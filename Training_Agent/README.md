# Training Agent

## 1. About the Project

The Training Agent is a component of the AgentFlow multi-agent project. Its purpose is to train and evaluate machine learning models based on the instructions received from the ML Strategy Agent.

It receives the processed dataset (`X` and `y`) from the Data Agent and the model recommendations, evaluation metrics, and validation strategy from the ML Strategy Agent.

Based on these inputs, the Training Agent trains the requested models, evaluates their performance, performs cross-validation, and sends the results to the Orchestrator.

### Responsibilities

- Receive processed data and strategy instructions.
- Train the models specified by the ML Strategy Agent.
- Evaluate models using the provided metrics.
- Perform the specified cross-validation.
- Return structured evaluation results to the Orchestrator.

**Scope:** The Training Agent only handles model training and evaluation. It does not recommend models, rank them, or select a final best model.

## 2. Project Structure

```text
Training-Agent/
│
├── training_evaluation_agent.py
├── model_registry.py
├── run_classification.py
├── run_regression.py
├── requirements.txt
├── README.md
│
├── data/
│   └── bank-full.csv
│
├── notebooks/
│   └── Training_Agent_Experiments.ipynb
│
└── outputs/
    └── .gitkeep
```

### Description of Files

| File | Purpose |
|---|---|
| `training_evaluation_agent.py` | Main file containing the Training Agent's execution logic. |
| `model_registry.py` | Contains the available classification and regression models. |
| `run_classification.py` | Runs a sample classification experiment independently. |
| `run_regression.py` | Runs a sample regression experiment independently. |
| `requirements.txt` | Lists the required Python libraries. |
| `README.md` | Project documentation and setup instructions. |
| `data/` | Contains the dataset used for the classification experiment. |
| `notebooks/` | Contains the Jupyter notebook used for experiments and testing. |
| `outputs/` | Stores generated experiment results. |

## 3. Implementation

The Training Agent was implemented using Python, Pandas, and Scikit-learn.

### Step 1: Model Registry

A shared model registry was created in `model_registry.py`.

It contains:
- 10 classification models.
- 10 regression models.

The Training Agent uses this registry to access the estimators requested by the ML Strategy Agent.

### Step 2: Training Agent Development

The main implementation was created in `training_evaluation_agent.py`.

A single main function, `run_training_evaluation_agent()`, handles both classification and regression workflows.

It performs the following operations:

1. Receives the dataset and strategy instructions.
2. Identifies the problem type.
3. Retrieves the requested models from the registry.
4. Prepares the required preprocessing pipeline.
5. Trains each requested model.
6. Calculates the specified test metrics.
7. Performs cross-validation using the provided validation strategy.
8. Returns the results in a structured Python dictionary.

### Step 3: Classification Experiment

A classification experiment was performed using the Bank Marketing dataset.

The experiment used:
- Logistic Regression
- Random Forest
- Support Vector Machine (SVM)

The evaluation metrics included accuracy, precision, recall, F1-score, and ROC-AUC.

A Stratified K-Fold cross-validation strategy with 5 splits was used.

The experiment was executed through `run_classification.py`, and the results were saved in `outputs/classification_results.json`.

### Step 4: Regression Experiment

A regression experiment was performed using the California Housing dataset.

The experiment used:
- Linear Regression
- Random Forest Regressor
- Support Vector Regressor (SVR)

The evaluation metrics included MAE, RMSE, and R².

A K-Fold cross-validation strategy with 5 splits was used.

The experiment was executed through `run_regression.py`, and the results were saved in `outputs/regression_results.json`.

### Step 5: Jupyter Notebook Experiments

The notebook `Training_Agent_Experiments.ipynb` contains the experimental work and example workflows used during development.

It demonstrates the model training and evaluation process separately from the main agent implementation.

The notebook uses sample strategy inputs for experimentation. During final integration, actual outputs from the ML Strategy Agent will be used.

## 4. Running the Project

### Requirements

- Python 3.10 or later
- Pandas
- NumPy
- Scikit-learn

### Setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

### Run the experiments

For classification:

```bash
python run_classification.py
```

For regression:

```bash
python run_regression.py
```

These runner files are intended for independent testing and demonstration. They are not the entry points used by the Orchestrator.

## 5. Orchestrator Integration

The Orchestrator will connect the Training Agent with the other AgentFlow components.

It will import and call `run_training_evaluation_agent()` from `training_evaluation_agent.py`, passing the processed dataset and the ML Strategy Agent's output.

The Training Agent will return structured training and evaluation results to the Orchestrator for the next stage of the workflow.

The `model_registry.py` file is used internally by the main agent implementation. The two runner files are only for independent testing and demonstration.

**Note:** The classification and regression workflows have been tested independently. Integration with the Orchestrator will be completed as part of the overall AgentFlow workflow.

## 6. Output

The Training Agent returns a structured Python dictionary containing:

- Execution status
- Requested and trained model names
- Training time
- Test evaluation metrics
- Cross-validation results

This output is designed to be passed back to the Orchestrator for the next stage of the AgentFlow workflow.

## 7. Technologies Used

- Python
- Pandas
- NumPy
- Scikit-learn
- Jupyter Notebook