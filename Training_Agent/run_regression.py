
import json
import pandas as pd
from pathlib import Path
from sklearn.datasets import fetch_california_housing

from training_evaluation_agent import run_training_evaluation_agent


# --------------------------------------------------
# 1. Load California Housing Dataset
# --------------------------------------------------

print("Loading California Housing dataset...")

housing = fetch_california_housing(as_frame=True)

X = housing.data
y = housing.target

print("\nDataset loaded successfully!")
print("Dataset shape:", X.shape)
print("Target shape:", y.shape)
print("Features:", list(X.columns))


# --------------------------------------------------
# 2. Simulate ML Strategy Agent Output
# --------------------------------------------------

agent_input = {
    "problem_type": "regression",

    "recommended_models": [
        "Linear Regression",
        "Random Forest Regressor",
        "SVR"
    ],

    "evaluation_metrics": [
        "mae",
        "rmse",
        "r2"
    ],

    "validation_strategy": {
        "type": "k_fold",
        "n_splits": 5
    }
}


# --------------------------------------------------
# 3. Execute Training & Evaluation Agent
# --------------------------------------------------

print("\nStarting Regression Training & Evaluation Agent...")
print("Models requested:", agent_input["recommended_models"])

agent_output = run_training_evaluation_agent(
    X,
    y,
    agent_input
)


# --------------------------------------------------
# 4. Display Results
# --------------------------------------------------

print("\n========== REGRESSION AGENT EXECUTION COMPLETED ==========")

print(json.dumps(agent_output, indent=4))


# --------------------------------------------------
# 5. Save Results
# --------------------------------------------------

output_path = Path("outputs/regression_results.json")

output_path.parent.mkdir(parents=True, exist_ok=True)

with open(output_path, "w", encoding="utf-8") as file:
    json.dump(agent_output, file, indent=4)

print("\nRegression results saved successfully!")
print("Output file:", output_path.resolve())
