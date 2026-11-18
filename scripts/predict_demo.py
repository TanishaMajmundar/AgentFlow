"""Load a downloaded best_model.pkl and predict on raw rows.

  python scripts/predict_demo.py --model <best_model.pkl> --csv <rows.csv> [--n 8] [--out predictions.csv]

SECURITY: pickle files can execute code when loaded. Only load models you created or trust.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data_agent"))   # lets joblib find AgentFlow's preprocessing classes

import joblib
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--csv", required=True)
ap.add_argument("--n", type=int, default=8, help="how many rows to predict")
ap.add_argument("--out", help="optional CSV to save predictions to")
a = ap.parse_args()

model = joblib.load(a.model)
m = model.meta
print("\n=== AgentFlow model ===")
print("model        :", m.get("model_name"))
print("problem type :", m.get("problem_type"))
print("target       :", m.get("target_column"))
print("primary metric:", m.get("primary_metric"))
print("test metrics :", {k: round(v, 3) for k, v in (m.get("test_metrics") or {}).items()})
print("trained with :", m.get("library_versions"))

raw = pd.read_csv(a.csv, sep=None, engine="python").head(a.n)
target = m.get("target_column")
actual = raw[target].tolist() if target in raw.columns else None
rows = raw.drop(columns=[target], errors="ignore")

missing = [c for c in m.get("required_input_columns", []) if c not in rows.columns]
if missing:
    print("\nWARNING: these expected columns are missing and will be filled with 0:", missing)

pred = model.predict(rows)
out = rows.copy()
out["PREDICTED_" + str(target)] = pred
if hasattr(model.estimator, "predict_proba") and model.class_labels is not None:
    proba = model.predict_proba(rows)
    out["confidence"] = proba.max(axis=1).round(3)
if actual is not None:
    out["ACTUAL_" + str(target)] = actual

print("\n=== Predictions ===")
show = [c for c in out.columns if c.startswith(("PREDICTED_", "ACTUAL_", "confidence"))]
print(out[show].to_string(index=False))
if a.out:
    out.to_csv(a.out, index=False)
    print("\nsaved:", a.out)