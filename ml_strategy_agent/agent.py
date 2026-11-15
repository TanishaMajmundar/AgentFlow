"""
agent.py
--------
ML Strategy Agent — central orchestrator (Member 4).

LLM Backend:  Google Gemini (gemini-2.0-flash → gemini-1.5-flash-8b fallback)
              Falls back to rule-based-only mode if no API key is available.

Model Scoring: 40% rule-based heuristics + 60% OpenML meta-learning
               (Falls back to 100% rule-based if OpenML is unavailable)

Pipeline (5 steps):
  1. Analyze problem type         (problem_analyzer.py)
  2. Analyze dataset              (dataset_analyzer.py)
  3. Select candidate models      (model_selector.py)
  4. Select evaluation metrics    (metric_selector.py)
  5. Build experiment plan        (experiment_planner.py)
  + Generate Gemini explanation   (llm.py + prompts.py)
"""

from __future__ import annotations
import sys

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from ml_strategy_agent.schemas import DataAgentOutput, MLStrategy, ProblemType
from ml_strategy_agent.problem_analyzer   import analyze_problem
from ml_strategy_agent.dataset_analyzer   import analyze_dataset
from ml_strategy_agent.model_selector     import select_models
from ml_strategy_agent.metric_selector    import select_metrics
from ml_strategy_agent.experiment_planner import create_plan
from ml_strategy_agent.llm                import GeminiLLM
from ml_strategy_agent.prompts            import problem_interpretation_prompt, explanation_prompt


class MLStrategyAgent:
    """
    Member 4 — ML Strategy Agent.

    Architecture:
    ─────────────
    Rule Engine       (40% weight)
      ├─ problem_analyzer   → ProblemType
      ├─ dataset_analyzer   → DatasetSummary
      └─ rules.py           → rule-based suitability scores

    OpenML Meta-Learning  (60% weight)
      ├─ openml_recommender → similar dataset lookup
      └─ blended scoring    → final ranked models

    Gemini LLM  (google-genai)
      ├─ Resolves ambiguous problem types
      └─ Generates human-readable strategy explanation
    """

    def __init__(self):
        self._llm = GeminiLLM()
        if self._llm.ready:
            print(f"[MLStrategyAgent] LLM: Google Gemini ({self._llm.model_name})")
        else:
            print("[MLStrategyAgent] LLM disabled — running in rule-based-only mode.")
        print("[MLStrategyAgent] Scoring: 40% rule-based + 60% OpenML meta-learning\n")

    # ── Public Entry Point ────────────────────────────────────────────────────

    def run(
        self,
        problem_statement: str,
        target_column:     str,
        data_agent_output: DataAgentOutput,
        top_n_models:      int = 3,
    ) -> MLStrategy:
        """
        Run the full ML strategy pipeline and return a complete MLStrategy object.

        Args:
            problem_statement: Plain-English description of the ML task.
            target_column:     Name of the target variable in the dataset.
            data_agent_output: Output from the Data Agent (Member 3).
            top_n_models:      How many candidate models to recommend (default 3).

        Returns:
            MLStrategy — the complete strategy output for Member 5.
        """
        print("=" * 62)
        print("  ML STRATEGY AGENT  |  Member 4  |  Capstone Project")
        print("=" * 62)

        # ── Step 1: Identify Problem Type ─────────────────────────────────
        print("\n[1/5] Analyzing problem type...")
        problem_type, reasoning = analyze_problem(problem_statement, data_agent_output)
        print(f"      -> {problem_type.value.replace('_', ' ').title()}")
        print(f"      Reason: {reasoning}")

        if problem_type == ProblemType.UNKNOWN:
            if self._llm.ready:
                print("      -> Unclear -- consulting Gemini...")
                problem_type = self._resolve_problem_type(problem_statement, target_column)
                print(f"      -> Gemini resolved: {problem_type.value}")
            else:
                problem_type = ProblemType.BINARY_CLASSIFICATION
                print("      -> Fallback: assuming Binary Classification.")

        # ── Step 2: Analyze Dataset ───────────────────────────────────────
        print("\n[2/5] Analyzing dataset characteristics...")
        dataset_summary = analyze_dataset(data_agent_output, problem_type)
        print(f"      -> Size:    {dataset_summary.size_category.value.capitalize()} "
              f"({dataset_summary.num_rows:,} rows x {dataset_summary.num_features} features)")
        print(f"      -> Balance: {dataset_summary.balance_status.value}")
        if dataset_summary.minority_class_ratio is not None:
            print(f"      -> Minority class ratio: {dataset_summary.minority_class_ratio:.1%}")

        # ── Step 3: Select Candidate Models ──────────────────────────────
        print(f"\n[3/5] Selecting top-{top_n_models} candidate models...")
        print("      -> Querying OpenML for similar historical datasets...")
        candidates, openml_result = select_models(
            problem_type    = problem_type,
            dataset_summary = dataset_summary,
            top_n           = top_n_models,
        )

        if openml_result.success:
            print(f"      -> OpenML: {openml_result.num_similar_found} similar tasks found")
            if openml_result.similar_datasets:
                preview = ", ".join(openml_result.similar_datasets[:3])
                ellipsis = "..." if len(openml_result.similar_datasets) > 3 else ""
                print(f"         Matches: {preview}{ellipsis}")
            print("      -> Blending: 40% rule-based + 60% OpenML")
        else:
            print(f"      -> OpenML unavailable: {openml_result.message}")
            print("      -> Falling back to 100% rule-based scoring")

        for c in candidates:
            print(f"      -> [{c.role:22s}] {c.name:38s} Score: {c.suitability_score}/100")

        # ── Step 4: Select Metrics ────────────────────────────────────────
        print("\n[4/5] Selecting evaluation metrics...")
        metrics = select_metrics(problem_type, dataset_summary)
        print(f"      -> Primary:    {metrics.primary_metric}")
        print(f"      -> Secondary:  {', '.join(metrics.secondary_metrics[:3])}")
        print(f"      -> Validation: {metrics.validation_strategy}")

        # ── Step 5: Build Experiment Plan ─────────────────────────────────
        print("\n[5/5] Building experiment plan...")
        experiment_plan = create_plan(problem_type, candidates, metrics, target_column)
        print(f"      -> {len(experiment_plan.steps)} steps planned")

        # ── Assemble MLStrategy ───────────────────────────────────────────
        openml_dict = (
            {
                "success":           True,
                "message":           openml_result.message,
                "num_similar_found": openml_result.num_similar_found,
                "similar_datasets":  openml_result.similar_datasets,
            }
            if openml_result.success
            else {
                "success": False,
                "message": openml_result.message,
            }
        )

        strategy = MLStrategy(
            problem_statement  = problem_statement,
            target_column      = target_column,
            problem_type       = problem_type,
            dataset_summary    = dataset_summary,
            candidate_models   = candidates,
            metrics            = metrics,
            experiment_plan    = experiment_plan,
            gemini_explanation = None,
            openml_context     = openml_dict,
        )

        # ── Gemini Explanation ────────────────────────────────────────────
        if self._llm.ready:
            print(f"\n[+] Generating explanation via Gemini ({self._llm.model_name})...")
            try:
                similar = openml_result.similar_datasets if openml_result.success else None
                prompt  = explanation_prompt(strategy, similar_datasets=similar)
                strategy.gemini_explanation = self._llm.generate(prompt)
                print("      -> Explanation generated.")
            except Exception as e:
                print(f"      -> Explanation failed: {e}")

        print("\n" + "=" * 62)
        print("  STRATEGY COMPLETE")
        print("=" * 62 + "\n")

        return strategy

    # ── LLM Helpers ──────────────────────────────────────────────────────────

    def _resolve_problem_type(
        self,
        problem_statement: str,
        target_column:     str,
    ) -> ProblemType:
        """Ask Gemini to classify the problem type from the statement."""
        prompt = problem_interpretation_prompt(problem_statement, target_column)
        try:
            raw = self._llm.generate(prompt).lower()
            if "regression"    in raw:
                return ProblemType.REGRESSION
            if "multiclass"    in raw:
                return ProblemType.MULTICLASS_CLASSIFICATION
            if "binary"        in raw or "classification" in raw:
                return ProblemType.BINARY_CLASSIFICATION
        except Exception:
            pass
        return ProblemType.BINARY_CLASSIFICATION  # safe fallback

    # ── Serialization Helpers ─────────────────────────────────────────────────

    def to_json(self, strategy: MLStrategy, indent: int = 2) -> str:
        """Serialize an MLStrategy to a JSON string."""
        return strategy.model_dump_json(indent=indent)

    def from_json(self, json_str: str) -> MLStrategy:
        """Deserialize an MLStrategy from a JSON string."""
        return MLStrategy.model_validate_json(json_str)
