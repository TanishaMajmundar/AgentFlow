"""Builds best_model.pkl for the model the orchestrator selected."""
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy
import pandas
import sklearn

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "data_agent") not in sys.path:
    sys.path.insert(0, str(ROOT / "data_agent"))

from agentflow_data_agent.model_bundle import AgentFlowModel  # noqa: E402

MODELS_DIR = ROOT / "backend" / "storage" / "models"


def package_best_model(project_id, data_out, plan, best):
    """Returns the path of backend/storage/models/<project_id>/best_model.pkl."""
    preprocessor = joblib.load(data_out["artifacts"]["pipeline"])
    estimator = joblib.load(best["model_path"])

    out_dir = MODELS_DIR / str(project_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "project_id": project_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_name": best["model_name"],
        "problem_type": data_out["problem_type"],
        "target_column": data_out["target_column"],
        "primary_metric": plan.get("primary_metric_label") or plan.get("primary_metric"),
        "test_metrics": best.get("metrics"),
        "cross_validation": best.get("cv"),
        "train_rows": data_out.get("train_rows"),
        "test_rows": data_out.get("test_rows"),
        "required_input_columns": data_out.get("raw_feature_columns", []),
        "library_versions": {
            "python": platform.python_version(),
            "scikit-learn": sklearn.__version__,
            "pandas": pandas.__version__,
            "numpy": numpy.__version__,
        },
    }
    bundle = AgentFlowModel(preprocessor, estimator, meta)
    bundle.meta["class_labels"] = bundle.class_labels

    path = out_dir / "best_model.pkl"
    joblib.dump(bundle, path)
    (out_dir / "model_info.json").write_text(
        json.dumps(bundle.meta, indent=2, default=str), encoding="utf-8")
    return str(path)