import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data_agent"))
from agentflow_data_agent.core.agent import AutonomousDataAgent

rng = np.random.RandomState(0)
n = 600
df = pd.DataFrame({
    "customer_id": [f"C{i}" for i in range(n)],
    "age": rng.randint(18, 70, n),
    "income": rng.normal(50000, 15000, n).round(0),
    "city": rng.choice(["Ahmedabad", "Surat", "Pune", "Delhi"], n),
})
score = df["income"] / 1000 + rng.normal(0, 8, n)
df["risk_level"] = pd.cut(score, [-1e9, 40, 55, 1e9], labels=["Low", "Medium", "High"]).astype(str)
df["subscribed"] = np.where(score > 50, "yes", "no")

out = ROOT / "artifacts"
out.mkdir(exist_ok=True)
csv_path = out / "demo_text_target.csv"
df.to_csv(csv_path, index=False)

for target in ["risk_level", "subscribed"]:
    agent = AutonomousDataAgent(output_dir=str(out / "data_agent_test"))
    rep = agent.run(file_path=csv_path, project_id=f"t_{target}",
                    target_column=target, problem_statement="demo")
    t = rep.target_report
    print(target, "->", t.selected_target, "|", t.selection_mode,
          "|", t.inferred_problem_type, "|", t.class_distribution)