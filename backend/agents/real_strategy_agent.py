"""Real ML Strategy Agent wrapper.
Rules-only by default (offline, fast, no API keys). Set AGENTFLOW_USE_LLM=1 or
AGENTFLOW_USE_OPENML=1 to switch the online features back on."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if os.getenv("AGENTFLOW_USE_LLM") != "1":
    os.environ["GOOGLE_API_KEY"] = ""   # must be set BEFORE ml_strategy_agent is imported

from ml_strategy_agent import (  # noqa: E402
    MLStrategyAgent, DataAgentOutput, DatasetMetadata,
    TargetDistribution, PreprocessingSummary,
)
import ml_strategy_agent.model_selector as _model_selector  # noqa: E402
from ml_strategy_agent.openml_recommender import OpenMLResult  # noqa: E402
from Training_Agent.model_registry import MODEL_REGISTRY  # noqa: E402

if os.getenv("AGENTFLOW_USE_OPENML") != "1":
    _model_selector.query_openml = lambda *a, **k: OpenMLResult(
        success=False, message="OpenML disabled (offline mode).")

# Strategy names -> names the Training Agent's registry understands
NAME_FIX = {
    "Support Vector Regressor (SVR)": "SVR",
    "Naive Bayes": "Gaussian Naive Bayes",
    "XGBoost": "HistGradientBoosting",
}
FALLBACK = {
    "classification": ["Logistic Regression", "Random Forest", "Gradient Boosting"],
    "regression": ["Linear Regression", "Random Forest Regressor", "Gradient Boosting Regressor"],
}
ALLOWED_METRICS = {
    "classification": ["accuracy", "precision", "recall", "f1", "roc_auc"],
    "regression": ["mae", "rmse", "r2"],
}


def _to_strategy_input(d):
    if d["problem_type"] == "classification":
        dist = TargetDistribution(class_counts={
            str(c["label"]): int(c["count"]) for c in d.get("class_distribution", [])})
    else:
        s = d.get("target_stats") or {}
        dist = TargetDistribution(min_value=s.get("min"), max_value=s.get("max"),
                                  mean_value=s.get("mean"))
    n_feat = int(d["final_feature_count"])
    meta = DatasetMetadata(
        num_rows=int(d["rows"]),
        num_columns=n_feat + 1,              # +1 for the target
        num_numeric_features=n_feat,         # the processed data is all numeric
        num_categorical_features=0,
        num_text_features=0,
        num_missing_values=0,                # already imputed by the Data Agent
        target_column=d["target_column"],
        target_distribution=dist,
        preprocessing=PreprocessingSummary(),
    )
    return DataAgentOutput(dataset_name=Path(d["dataset_path"]).stem, metadata=meta)


def _primary_key(label, kind):
    low = (label or "").lower()
    if "f1" in low:
        key = "f1"
    elif "accuracy" in low:
        key = "accuracy"
    elif "roc" in low:
        key = "roc_auc"
    elif "r²" in low or "r2" in low:
        key = "r2"
    elif "rmse" in low:
        key = "rmse"
    elif "mae" in low:
        key = "mae"
    else:
        key = None
    if key in ALLOWED_METRICS[kind]:
        return key
    return "f1" if kind == "classification" else "r2"


def real_strategy_agent(problem_statement, target_column, data_output):
    kind = data_output["problem_type"]            # "classification" | "regression"
    strategy = MLStrategyAgent().run(
        problem_statement=problem_statement,
        target_column=target_column,
        data_agent_output=_to_strategy_input(data_output),
        top_n_models=6,                           # ask for extras, some names get filtered
    )

    names = []
    for c in strategy.candidate_models:
        n = NAME_FIX.get(c.name, c.name)
        if n in MODEL_REGISTRY[kind] and n not in names:
            names.append(n)
    for n in FALLBACK[kind]:
        if len(names) >= 3:
            break
        if n not in names:
            names.append(n)
    names = names[:3]

    if kind == "classification":
        validation = {"type": "stratified_k_fold", "n_splits": 5}
    else:
        validation = {"type": "k_fold", "n_splits": 5}

    return {
        "is_mock": False,
        "problem_type": kind,
        "problem_subtype": strategy.problem_type.value,
        "models": names,
        "primary_metric": _primary_key(strategy.metrics.primary_metric, kind),
        "primary_metric_label": strategy.metrics.primary_metric,
        "secondary_metrics": strategy.metrics.secondary_metrics,
        "evaluation_metrics": ALLOWED_METRICS[kind],
        "validation_strategy": validation,
        "dataset_size": strategy.dataset_summary.size_category.value,
        "balance": strategy.dataset_summary.balance_status.value,
        "candidates": [{"name": c.name, "role": c.role, "score": c.suitability_score,
                        "reasons": c.reasons[:3]} for c in strategy.candidate_models],
        "experiment_steps": [s.description for s in strategy.experiment_plan.steps],
        "explanation": strategy.gemini_explanation,
    }