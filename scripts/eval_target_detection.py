import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.orchestrator import llm_handler
from backend.orchestrator.target_analysis import analyze_target
from backend.orchestrator.target_detector import load_dataset_frame

rng = np.random.RandomState(7)
N = 300


def col(kind, *a):
    if kind == "id":
        return [f"ID{i:04d}" for i in range(N)]
    if kind == "int":
        return rng.randint(a[0], a[1], N)
    if kind == "float":
        return rng.normal(a[0], a[1], N).round(2)
    return rng.choice(a[0], N)  # "cat"


def frame(spec):
    return pd.DataFrame({s[0]: col(s[1], *s[2:]) for s in spec})


YN = ["yes", "no"]
CASES = [
    ("hospital readmission", "Predict which patients will be readmitted to hospital within 30 days", "readmitted_30d",
     [("patient_id", "id"), ("age", "int", 18, 90), ("readmitted_30d", "cat", YN),
      ("bmi", "float", 27, 5), ("smoker", "cat", YN), ("blood_pressure", "float", 120, 15)]),
    ("house price", "Estimate how much a house will sell for", "sale_amt",
     [("sqft", "int", 500, 4000), ("bedrooms", "int", 1, 6), ("location", "cat", ["north", "south", "east", "west"]),
      ("year_built", "int", 1950, 2023), ("sale_amt", "float", 350000, 90000)]),
    ("loan approval", "Decide whether a loan application will be approved", "loan_status",
     [("applicant_id", "id"), ("income", "float", 55000, 15000), ("loan_amount", "float", 20000, 8000),
      ("credit_score", "int", 300, 850), ("employment", "cat", ["salaried", "self-employed", "unemployed"]),
      ("loan_status", "cat", ["approved", "rejected"])]),
    ("student result", "Predict whether a student will pass the course", "final_result",
     [("hours_studied", "float", 12, 4), ("attendance_pct", "float", 80, 12), ("prior_grade", "int", 40, 100),
      ("school", "cat", ["A", "B", "C"]), ("final_result", "cat", ["pass", "fail"])]),
    ("employee attrition (target mid-table)", "Which employees are likely to leave? Predict employee attrition", "left_company",
     [("emp_no", "id"), ("left_company", "cat", YN), ("dept", "cat", ["sales", "tech", "hr", "ops"]),
      ("tenure_years", "int", 0, 25), ("salary", "float", 60000, 15000), ("last_rating", "int", 1, 6)]),
    ("laptop price", "Predict the price of a laptop", "price",
     [("price", "float", 900, 300), ("brand", "cat", ["a", "b", "c", "d"]), ("ram_gb", "cat", [8, 16, 32]),
      ("storage_gb", "cat", [256, 512, 1024]), ("rating", "float", 4, 0.5)]),
    ("iris species", "Classify the species of an iris flower", "species",
     [("sepal_len", "float", 5.8, 0.8), ("sepal_wid", "float", 3, 0.4), ("petal_len", "float", 3.7, 1.7),
      ("petal_wid", "float", 1.2, 0.7), ("species", "cat", ["setosa", "versicolor", "virginica"])]),
    ("subscription cancel (target mid-table)", "Find out which customers will cancel their subscription", "cancelled",
     [("customer_id", "id"), ("plan", "cat", ["basic", "pro", "premium"]), ("cancelled", "int", 0, 2),
      ("monthly_fee", "float", 40, 12), ("support_calls", "int", 0, 9), ("region", "cat", ["N", "S", "E", "W"])]),
    ("bike rentals (target first)", "Forecast the number of daily bike rentals", "cnt",
     [("cnt", "int", 0, 900), ("temp", "float", 20, 8), ("humidity", "float", 60, 15),
      ("windspeed", "float", 12, 5), ("season", "cat", ["spring", "summer", "fall", "winter"]), ("holiday", "int", 0, 2)]),
    ("fraud flag (target mid-table)", "Classify each transaction as legitimate or fraudulent", "is_flagged",
     [("txn_id", "id"), ("is_flagged", "cat", ["legit", "fraud"]), ("amount", "float", 80, 60),
      ("merchant_type", "cat", ["food", "fuel", "travel", "retail"]), ("hour", "int", 0, 24)]),
]

ap = argparse.ArgumentParser()
ap.add_argument("--spec", help='JSON list of real datasets: [{"file":"x.csv","statement":"...","target":"col"}]')
args = ap.parse_args()

cases = [(n, s, t, frame(sp)) for n, s, t, sp in CASES]
if args.spec:
    for item in json.loads(Path(args.spec).read_text(encoding="utf-8")):
        cases.append((Path(item["file"]).name, item["statement"], item["target"],
                      load_dataset_frame(item["file"])))

llm_on = llm_enabled = llm_handler.llm_enabled()
print(f"\nprovider: {llm_handler.provider_name()}  model: {llm_handler.model_name() or '-'}\n")
print(f"{'case':42} {'truth':16} {'rules':22} {'hybrid':22}")
rows, r_ok, h_ok, llm_errors = [], 0, 0, 0
for name, stmt, truth, df in cases:
    r = analyze_target(df, stmt, use_llm=False)
    h = analyze_target(df, stmt, use_llm=True) if llm_on else None
    r_hit = r["recommended"] == truth
    r_ok += r_hit
    h_pick, h_hit = "-", None
    if h is not None:
        h_pick, h_hit = h["recommended"], h["recommended"] == truth
        h_ok += bool(h_hit)
        llm_errors += 1 if (h.get("llm") or {}).get("error") else 0
    print(f"{name[:41]:42} {truth:16} {str(r['recommended'])[:14] + (' OK' if r_hit else ' X'):22} "
          f"{(str(h_pick)[:14] + (' OK' if h_hit else ' X')) if h is not None else '-':22}")
    rows.append({"case": name, "truth": truth, "rules": r["recommended"], "rules_ok": r_hit,
                 "hybrid": h_pick if h is not None else None, "hybrid_ok": h_hit,
                 "llm_error": (h or {}).get("llm", {}).get("error") if h else None})

n = len(cases)
print(f"\nrules only : {r_ok}/{n} correct")
if llm_on:
    print(f"rules + LLM: {h_ok}/{n} correct   (LLM errors that fell back to rules: {llm_errors})")
else:
    print("rules + LLM: skipped (set $env:AGENTFLOW_LLM='ollama' to compare)")
out = ROOT / "artifacts" / "target_eval.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({"provider": llm_handler.provider_name(), "model": llm_handler.model_name(),
                           "rules_correct": r_ok, "hybrid_correct": h_ok if llm_on else None,
                           "total": n, "cases": rows}, indent=2, default=str))
print("saved:", out)