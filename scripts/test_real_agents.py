import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.agents.real_data_agent import real_data_agent
from backend.agents.real_strategy_agent import real_strategy_agent
from backend.agents.real_training_agent import real_training_agent
from backend.orchestrator.model_selection import select_best_model

ap = argparse.ArgumentParser()
ap.add_argument("--file", required=True)
ap.add_argument("--target", required=True)
ap.add_argument("--problem", default="")
a = ap.parse_args()

print("\n=== DATA AGENT ===")
d = real_data_agent(a.file, a.target, a.problem)
print(d["problem_type"], "|", d["rows"], "rows |", d["final_feature_count"], "features |",
      d["train_rows"], "train /", d["test_rows"], "test")

print("\n=== STRATEGY AGENT ===")
s = real_strategy_agent(a.problem, a.target, d)
print("\nmodels :", s["models"])
print("metric :", s["primary_metric"], f"({s['primary_metric_label']})")

print("\n=== TRAINING AGENT ===")
t = real_training_agent(d, s)
for r in t["results"]:
    print(f"  {r['model_name']:32} {r['status']:8}", r.get("metrics") or r.get("error"))

print("\n=== ORCHESTRATOR SELECTION ===")
best = select_best_model(t["results"], s["primary_metric"])
print("primary metric:", s["primary_metric"])
print("BEST MODEL    :", best["model_name"] if best else None, (best or {}).get("metrics"))