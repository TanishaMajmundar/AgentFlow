"""Real Training Agent wrapper: trains each model separately (one failure does not stop
the others), scores on the Data Agent's untouched test split, and saves each fitted
candidate to backend/storage/models/<run_id>/candidates/."""
import math
import re
import sys
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Training_Agent.training_evaluation_agent import run_training_evaluation_agent  # noqa: E402

MODELS_DIR = ROOT / "backend" / "storage" / "models"


def _load(path):
    p = Path(path)
    return pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_csv(p)


def _clean(o):
    """NaN/inf cannot be sent as JSON: turn them into None."""
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    return o


def real_training_agent(data_output, plan):
    art = data_output["artifacts"]
    target = data_output["target_column"]
    train_df, test_df = _load(art["train"]), _load(art["test"])
    X_train, y_train = train_df.drop(columns=[target]), train_df[target]
    X_test, y_test = test_df.drop(columns=[target]), test_df[target]

    validation = dict(plan["validation_strategy"])
    if plan["problem_type"] == "classification":
        smallest = int(y_train.value_counts().min())
        validation["n_splits"] = max(2, min(5, smallest))   # tiny classes need fewer folds

    run_dir = MODELS_DIR / str(data_output.get("run_id", "run")) / "candidates"
    run_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for name in plan["models"]:
        single = {
            "problem_type": plan["problem_type"],
            "recommended_models": [name],
            "evaluation_metrics": plan["evaluation_metrics"],
            "validation_strategy": validation,
        }
        try:
            out, fitted = run_training_evaluation_agent(
                X_train, y_train, single, X_test=X_test, y_test=y_test, return_models=True)
            res = out["model_results"][name]
            path = run_dir / (re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_") + ".pkl")
            joblib.dump(fitted[name], path)
            results.append({
                "model_name": name,
                "status": "success",
                "metrics": res["test_results"],
                "cv": res["cross_validation_results"],
                "train_seconds": round(out["training_times_seconds"][name], 3),
                "model_path": str(path),
            })
        except Exception as e:
            results.append({"model_name": name, "status": "failed",
                            "metrics": {}, "error": str(e)[:300]})

    if not any(r["status"] == "success" for r in results):
        raise RuntimeError("All models failed to train: " + "; ".join(
            f"{r['model_name']}: {r.get('error')}" for r in results))

    return _clean({
        "is_mock": False,
        "problem_type": plan["problem_type"],
        "primary_metric": plan["primary_metric"],
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "evaluated_on": "held-out test split (never seen during training)",
        "results": results,
    })