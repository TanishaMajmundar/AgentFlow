"""MOCK agents for integration testing only. Replace with real agents."""


def mock_data_agent(dataset_path, target_column, problem_statement=""):
    return {"is_mock": True, "dataset_path": dataset_path,
            "target_column": target_column, "problem_type": "classification",
            "note": "MOCK Data Agent output"}


def mock_ml_strategy_agent(problem_statement, target_column, data_output):
    return {"is_mock": True, "problem_type": data_output["problem_type"],
            "models": ["logistic_regression", "random_forest"],
            "primary_metric": "f1", "note": "MOCK ML Strategy output"}


def mock_training_agent(data_output, experiment_plan):
    return {"is_mock": True, "results": [
        {"model_name": "logistic_regression", "status": "success", "metrics": {"f1": 0.78}},
        {"model_name": "random_forest", "status": "success", "metrics": {"f1": 0.83}},
    ]}