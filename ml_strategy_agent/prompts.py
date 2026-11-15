"""
prompts.py
----------
Gemini prompt templates for the ML Strategy Agent.

Prompts:
1. problem_interpretation_prompt  — resolves ambiguous problem types
2. explanation_prompt             — generates a human-readable strategy report
"""

from __future__ import annotations
from ml_strategy_agent.schemas import MLStrategy


def problem_interpretation_prompt(problem_statement: str, target_column: str) -> str:
    """
    Used when the rule-based analyzer cannot confidently determine
    the problem type. Asks Gemini to classify it.
    """
    return (
        f"You are an expert ML consultant classifying a machine learning problem.\n\n"
        f"Problem Statement:\n\"{problem_statement}\"\n\n"
        f"Target Column: \"{target_column}\"\n\n"
        f"Based on the problem statement and target column name, respond with EXACTLY ONE of:\n"
        f"- binary_classification\n"
        f"- multiclass_classification\n"
        f"- regression\n\n"
        f"Do not explain. Return only one of those three strings, nothing else."
    )


def explanation_prompt(strategy: MLStrategy, similar_datasets: list[str] | None = None) -> str:
    """
    Generates a professional, human-readable explanation of the ML strategy
    suitable for a capstone viva or project documentation.
    """
    candidate_lines = "\n".join(
        f"  {i+1}. {c.name} (Score: {c.suitability_score}/100 | Role: {c.role})\n"
        f"     Key reasons: {'; '.join(c.reasons[:2])}"
        for i, c in enumerate(strategy.candidate_models)
    )

    step_lines = "\n".join(
        f"  Step {s.step_number}: {s.description}"
        for s in strategy.experiment_plan.steps
    )

    if strategy.dataset_summary.minority_class_ratio is not None:
        ratio_pct    = strategy.dataset_summary.minority_class_ratio * 100
        balance_line = (
            f"Class balance: {ratio_pct:.1f}% minority class "
            f"({strategy.dataset_summary.balance_status.value})"
        )
    else:
        balance_line = "Target type: continuous numeric (regression problem)"

    openml_line = ""
    if similar_datasets:
        names = ", ".join(similar_datasets[:4])
        openml_line = (
            f"\nOpenML Context: Model scores were validated against {len(similar_datasets)} "
            f"similar historical benchmark datasets including: {names}. "
            f"The final suitability score blends 40% heuristic rules and 60% empirical OpenML evidence."
        )

    return (
        f"You are an expert ML consultant. Write a clear, professional explanation "
        f"of the following ML strategy for a student's capstone project viva presentation.\n\n"
        f"Requirements:\n"
        f"- 3 to 4 short paragraphs\n"
        f"- Plain English — explain the WHY behind each decision\n"
        f"- Explain WHY these specific models were chosen\n"
        f"- Explain WHY these specific evaluation metrics were selected\n"
        f"- Be encouraging and professional in tone\n"
        f"- Do NOT use bullet points — use proper flowing paragraphs\n\n"
        f"--- STRATEGY DETAILS ---\n"
        f"Problem: {strategy.problem_statement}\n"
        f"Target Column: {strategy.target_column}\n"
        f"Problem Type: {strategy.problem_type.value.replace('_', ' ').title()}\n\n"
        f"Dataset:\n"
        f"  - {strategy.dataset_summary.num_rows:,} rows, {strategy.dataset_summary.num_features} features\n"
        f"  - Size category: {strategy.dataset_summary.size_category.value}\n"
        f"  - {balance_line}\n"
        f"{openml_line}\n\n"
        f"Recommended Models:\n{candidate_lines}\n\n"
        f"Primary Metric: {strategy.metrics.primary_metric}\n"
        f"Secondary Metrics: {', '.join(strategy.metrics.secondary_metrics[:3])}\n"
        f"Validation: {strategy.metrics.validation_strategy}\n\n"
        f"Experiment Plan:\n{step_lines}\n"
        f"--- END ---\n\n"
        f"Write the explanation now:"
    )
