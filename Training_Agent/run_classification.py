
import pandas as pd
import json
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from training_evaluation_agent import run_training_evaluation_agent


# --------------------------------------------------
# 1. Load Bank Marketing Dataset
# --------------------------------------------------

data_path = Path("data/bank-full.csv")

df = pd.read_csv(data_path, sep=";")

print("Dataset loaded successfully!")
print("Original dataset shape:", df.shape)


# --------------------------------------------------
# 2. Separate Features and Target
# --------------------------------------------------

X = df.drop(columns=["y"])

# Encode target labels: yes = 1, no = 0
label_encoder = LabelEncoder()
y = label_encoder.fit_transform(df["y"])

print("Features shape:", X.shape)
print("Target classes:", label_encoder.classes_)


# --------------------------------------------------
# 3. Take a Stratified Sample of 5000 Rows
# --------------------------------------------------

X, _, y, _ = train_test_split(
    X,
    y,
    train_size=5000,
    random_state=42,
    stratify=y
)

print("\nSample selected successfully!")
print("Sample size:", len(X))


# --------------------------------------------------
# 4. Simulate ML Strategy Agent Output
# --------------------------------------------------

agent_input = {
    "problem_type": "classification",

    "recommended_models": [
        "Logistic Regression",
        "Random Forest",
        "Support Vector Machine (SVM)"
    ],

    "evaluation_metrics": [
        "accuracy",
        "precision",
        "recall",
        "f1",
        "roc_auc"
    ],

    "validation_strategy": {
        "type": "stratified_k_fold",
        "n_splits": 5
    }
}


# --------------------------------------------------
# 5. Execute Training & Evaluation Agent
# --------------------------------------------------

print("\nStarting Training & Evaluation Agent...")
print("Models requested:", agent_input["recommended_models"])

agent_output = run_training_evaluation_agent(
    X,
    y,
    agent_input
)


# --------------------------------------------------
# 6. Display Results
# --------------------------------------------------

print("\n========== AGENT EXECUTION COMPLETED ==========")

print(json.dumps(agent_output, indent=4))


# --------------------------------------------------
# 7. Save Results for Orchestrator / Inspection
# --------------------------------------------------

output_path = Path("outputs/classification_results.json")

output_path.parent.mkdir(parents=True, exist_ok=True)

with open(output_path, "w", encoding="utf-8") as file:
    json.dump(agent_output, file, indent=4)

print("\nResults saved successfully!")
print("Output file:", output_path.resolve())
