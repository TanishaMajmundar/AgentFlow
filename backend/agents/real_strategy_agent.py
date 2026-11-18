"""Real ML Strategy Agent wrapper.

Strategy modes (env AGENTFLOW_STRATEGY_MODE, or the mode= argument):
  rules   rule-based suitability only (default: offline, takes seconds)
  openml  rules blended with OpenML meta-learning (needs internet, about a minute)
  both    run both and train the UNION of their candidates; measured scores decide
If STRATEGY_MODE is unset, AGENTFLOW_USE_OPENML=1 still selects 'openml'.
AGENTFLOW_USE_LLM=1 lets the Strategy Agent also call Gemini (off by default).
"""
import os
import sys
import threading
from itertools import zip_longest
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

_REAL_QUERY = _model_selector.query_openml           # keep the real function before patching
_OPENML_TIMEOUT = int(os.getenv("AGENTFLOW_OPENML_TIMEOUT", "90"))
_LOCK = threading.Lock()                              # the patch below is process-wide

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


def _query_real(*a, **k):
    return _REAL_QUERY(*a, **{**k, "timeout_seconds": _OPENML_TIMEOUT})


def _query_off(*a, **k):
    return OpenMLResult(success=False, message="OpenML disabled for this run.")


def _resolve_mode(mode):
    mode = (mode or os.getenv("AGENTFLOW_STRATEGY_MODE") or "").strip().lower()
    if mode in ("rules", "openml", "both"):
        return mode
    return "openml" if os.getenv("AGENTFLOW_USE_OPENML") == "1" else "rules"


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


def _run_strategy(problem_statement, target_column, data_output, use_openml):
    with _LOCK:
        _model_selector.query_openml = _query_real if use_openml else _query_off
        return MLStrategyAgent().run(
            problem_statement=problem_statement,
            target_column=target_column,
            data_agent_output=_to_strategy_input(data_output),
            top_n_models=6,                  # ask for extras; some names get filtered out
        )


def _candidates(strategy, kind, source):
    out = {}
    for c in strategy.candidate_models:
        n = NAME_FIX.get(c.name, c.name)
        if n in MODEL_REGISTRY[kind] and n not in out:
            out[n] = {"name": n, "strategy_name": c.name, "suitability": {source: c.suitability_score},
                      "reasons": c.reasons[:3], "proposed_by": [source]}
    return out


def real_strategy_agent(problem_statement, target_column, data_output, mode=None):
    kind = data_output["problem_type"]            # "classification" | "regression"
    mode = _resolve_mode(mode)
    big = int(data_output["rows"]) > 20000        # big data: fewer models to keep it fast

    runs = {}
    if mode in ("rules", "both"):
        runs["rules"] = _run_strategy(problem_statement, target_column, data_output, False)
    if mode in ("openml", "both"):
        runs["openml"] = _run_strategy(problem_statement, target_column, data_output, True)

    per_mode = (2 if big else 3) if mode == "both" else (3 if big else 5)
    info, lists = {}, []
    for src, strat in runs.items():
        cand = _candidates(strat, kind, src)
        names = list(cand)[:per_mode]
        lists.append(names)
        for n in names:
            if n in info:
                info[n]["proposed_by"].append(src)
                info[n]["suitability"].update(cand[n]["suitability"])
            else:
                info[n] = cand[n]

    names = []                                    # interleave so each strategy's #1 pick is included
    for group in zip_longest(*lists):
        for n in group:
            if n and n not in names:
                names.append(n)
    for n in FALLBACK[kind]:                      # always train at least 3 models
        if len(names) >= 3:
            break
        if n not in names:
            names.append(n)
            info[n] = {"name": n, "strategy_name": n, "suitability": {}, "proposed_by": ["fallback"],
                       "reasons": ["Standard model added by AgentFlow"]}

    base = next(iter(runs.values()))              # metrics do not depend on OpenML
    openml_ctx = runs["openml"].openml_context if "openml" in runs else None
    validation = ({"type": "stratified_k_fold", "n_splits": 5} if kind == "classification"
                  else {"type": "k_fold", "n_splits": 5})

    return {
        "is_mock": False,
        "strategy_mode": mode,
        "problem_type": kind,
        "problem_subtype": base.problem_type.value,
        "models": names,
        "candidates": [info[n] for n in names],
        "primary_metric": _primary_key(base.metrics.primary_metric, kind),
        "primary_metric_label": base.metrics.primary_metric,
        "secondary_metrics": base.metrics.secondary_metrics,
        "evaluation_metrics": ALLOWED_METRICS[kind],
        "validation_strategy": validation,
        "dataset_size": base.dataset_summary.size_category.value,
        "balance": base.dataset_summary.balance_status.value,
        "openml_used": bool(openml_ctx and openml_ctx.get("success")),
        "openml": openml_ctx,
        "experiment_steps": [s.description for s in base.experiment_plan.steps],
        "explanation": base.gemini_explanation,
    }