import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.orchestrator.target_detector import detect_target, load_dataset_frame

rng = np.random.RandomState(1)


def show(title, df, statement):
    r = detect_target(df, statement)
    print(f"\n=== {title} ===")
    print("statement  :", statement)
    print("recommended:", r["recommended"], "| confidence:", r["confidence"],
          "| ambiguous:", r["ambiguous"], "| type:", r["problem_type"])
    print("reason     :", r["reason"])
    print("alternates :", [(a["column"], a["score"]) for a in r["alternatives"]])
    if r["validation"]:
        print("warnings   :", r["validation"]["warnings"])


# Case 1: the one the Data Agent got wrong (picked device_type)
n = 900
seg = pd.DataFrame({
    "user_id": [f"U_{i}" for i in range(n)],
    "session_count": rng.poisson(12, n),
    "cart_value": rng.exponential(85, n),
    "device_type": rng.choice(["iOS", "Android", "Desktop", "Tablet"], n),
    "customer_segment": rng.choice(["Bronze", "Silver", "Gold", "Platinum"], n),
})
show("customer segments", seg, "Classify customers into bronze, silver, gold, and platinum tiers")

# Case 2: the example from the project concept
m = 700
churn = pd.DataFrame({
    "CustomerID": [f"C{i}" for i in range(m)],
    "Age": rng.randint(18, 80, m),
    "Gender": rng.choice(["M", "F"], m),
    "MonthlyCharges": rng.normal(70, 20, m).round(2),
    "Tenure": rng.randint(1, 72, m),
    "Contract": rng.choice(["Monthly", "Yearly", "TwoYear"], m),
    "PaymentMethod": rng.choice(["Card", "UPI", "Cash"], m),
    "Churn": rng.choice(["Yes", "No"], m, p=[0.27, 0.73]),
})
show("customer churn", churn,
     "Predict whether a customer will leave the company based on their account "
     "information and usage patterns.")

# Case 3 (optional): any real CSV
ap = argparse.ArgumentParser()
ap.add_argument("--file")
ap.add_argument("--problem", default="")
a = ap.parse_args()
if a.file:
    show(Path(a.file).name, load_dataset_frame(a.file), a.problem)