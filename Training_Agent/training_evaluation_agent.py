"""Training and evaluation workflow used by the AgentFlow system."""

import time

from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
    mean_absolute_error, mean_squared_error, r2_score,
)
from sklearn.model_selection import (
    train_test_split, StratifiedKFold, KFold, cross_validate,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

try:  # Supports both package imports and running this file directly.
    from .model_registry import get_models, RANDOM_STATE
except ImportError:
    from model_registry import get_models, RANDOM_STATE


def _build_pipeline(model, problem_type, X):
    """Build preprocessing + estimator pipeline for the supplied data."""
    if problem_type == "classification":
        numeric_columns = X.select_dtypes(include=["number"]).columns.tolist()
        categorical_columns = X.select_dtypes(exclude=["number"]).columns.tolist()

        preprocessor = ColumnTransformer(
            transformers=[
                ("numeric", StandardScaler(), numeric_columns),
                (
                    "categorical",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                    categorical_columns,
                ),
            ],
            remainder="drop",
        )
        return Pipeline([
            ("preprocessor", preprocessor),
            ("model", clone(model)),
        ])

    return Pipeline([
        ("scaler", StandardScaler()),
        ("model", clone(model)),
    ])


def _validate_agent_input(agent_input):
    required_keys = {
        "problem_type", "recommended_models",
        "evaluation_metrics", "validation_strategy",
    }
    missing = required_keys - set(agent_input)
    if missing:
        raise ValueError(f"Missing agent_input keys: {sorted(missing)}")

    problem_type = agent_input["problem_type"]
    if problem_type not in {"classification", "regression"}:
        raise ValueError("problem_type must be 'classification' or 'regression'.")

    if not agent_input["recommended_models"]:
        raise ValueError("recommended_models cannot be empty.")

    validation = agent_input["validation_strategy"]
    if not isinstance(validation, dict):
        raise ValueError("validation_strategy must be a dictionary.")

    n_splits = int(validation.get("n_splits", 5))
    if n_splits < 2:
        raise ValueError("n_splits must be at least 2.")

    strategy_type = str(validation.get("type", "")).lower()
    if problem_type == "classification":
        if strategy_type not in {
            "stratified_k_fold", "stratifiedkfold", "stratified"
        }:
            raise ValueError(
                "Classification requires validation_strategy.type="
                "'stratified_k_fold'."
            )
        allowed_metrics = {"accuracy", "precision", "recall", "f1", "roc_auc"}
    else:
        if strategy_type not in {"k_fold", "kfold", "ordinary_k_fold"}:
            raise ValueError(
                "Regression requires validation_strategy.type='k_fold'."
            )
        allowed_metrics = {"mae", "rmse", "r2"}

    requested_metrics = agent_input["evaluation_metrics"]
    unknown_metrics = sorted(set(requested_metrics) - allowed_metrics)
    if unknown_metrics:
        raise ValueError(
            f"Unsupported metrics for {problem_type}: {unknown_metrics}. "
            f"Supported metrics: {sorted(allowed_metrics)}"
        )

    return n_splits, allowed_metrics


def run_training_evaluation_agent(X, y, agent_input):
    """
    Train and evaluate only the models requested by the ML Strategy Agent.

    Parameters
    ----------
    X : pandas.DataFrame
        Processed feature data received from the Data Agent.
    y : pandas.Series or array-like
        Target values corresponding to X.
    agent_input : dict
        Strategy output containing problem_type, recommended_models,
        evaluation_metrics, and validation_strategy.

    Returns
    -------
    dict
        Structured execution and evaluation results for the Orchestrator.
        This function does not rank models or select a final best model.
    """
    if not hasattr(X, "select_dtypes"):
        raise TypeError("X must be a pandas DataFrame with named columns.")
    if len(X) != len(y):
        raise ValueError("X and y must contain the same number of rows.")
    if len(X) == 0:
        raise ValueError("The input dataset is empty.")

    problem_type = agent_input["problem_type"]
    recommended_models = list(agent_input["recommended_models"])
    requested_metrics = list(agent_input["evaluation_metrics"])
    validation_strategy = dict(agent_input["validation_strategy"])
    n_splits, _ = _validate_agent_input(agent_input)

    selected_models, unsupported_models = get_models(
        problem_type, recommended_models
    )
    if not selected_models:
        raise ValueError(
            "None of the recommended model names were found in the model registry."
        )

    if problem_type == "classification":
        class_counts = y.value_counts() if hasattr(y, "value_counts") else None
        if class_counts is not None and class_counts.min() < n_splits:
            raise ValueError(
                "Each class must contain at least n_splits samples for "
                "Stratified K-Fold."
            )
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.20, random_state=RANDOM_STATE, stratify=y
        )
        cv = StratifiedKFold(
            n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE
        )
        scoring_map = {
            "accuracy": "accuracy",
            "precision": "precision",
            "recall": "recall",
            "f1": "f1",
            "roc_auc": "roc_auc",
        }
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.20, random_state=RANDOM_STATE
        )
        cv = KFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)
        scoring_map = {
            "mae": "neg_mean_absolute_error",
            "rmse": "neg_root_mean_squared_error",
            "r2": "r2",
        }

    test_results = {}
    cv_results = {}
    training_times = {}

    for model_name, estimator in selected_models.items():
        pipeline = _build_pipeline(estimator, problem_type, X)
        start_time = time.perf_counter()
        pipeline.fit(X_train, y_train)
        training_times[model_name] = time.perf_counter() - start_time

        predictions = pipeline.predict(X_test)
        metrics_result = {}

        if problem_type == "classification":
            if "accuracy" in requested_metrics:
                metrics_result["accuracy"] = float(
                    accuracy_score(y_test, predictions)
                )
            if "precision" in requested_metrics:
                metrics_result["precision"] = float(
                    precision_score(y_test, predictions, zero_division=0)
                )
            if "recall" in requested_metrics:
                metrics_result["recall"] = float(
                    recall_score(y_test, predictions, zero_division=0)
                )
            if "f1" in requested_metrics:
                metrics_result["f1"] = float(
                    f1_score(y_test, predictions, zero_division=0)
                )
            if "roc_auc" in requested_metrics:
                if not hasattr(pipeline, "predict_proba"):
                    raise ValueError(
                        f"{model_name} does not support predict_proba for ROC-AUC."
                    )
                probabilities = pipeline.predict_proba(X_test)[:, 1]
                metrics_result["roc_auc"] = float(
                    roc_auc_score(y_test, probabilities)
                )
        else:
            if "mae" in requested_metrics:
                metrics_result["mae"] = float(
                    mean_absolute_error(y_test, predictions)
                )
            if "rmse" in requested_metrics:
                metrics_result["rmse"] = float(
                    mean_squared_error(y_test, predictions) ** 0.5
                )
            if "r2" in requested_metrics:
                metrics_result["r2"] = float(r2_score(y_test, predictions))

        test_results[model_name] = metrics_result

        requested_scoring = {
            metric: scoring_map[metric] for metric in requested_metrics
        }
        cv_scores = cross_validate(
            _build_pipeline(estimator, problem_type, X),
            X_train,
            y_train,
            cv=cv,
            scoring=requested_scoring,
            return_train_score=False,
            n_jobs=1,
        )

        model_cv_results = {}
        for metric in requested_metrics:
            scores = cv_scores[f"test_{metric}"]
            if metric in {"mae", "rmse"}:
                scores = -scores
            model_cv_results[f"{metric}_mean"] = float(scores.mean())
            model_cv_results[f"{metric}_std"] = float(scores.std())
        cv_results[model_name] = model_cv_results

    # Return serializable results only. Trained estimators remain local to this run.
    return {
        "status": "success",
        "problem_type": problem_type,
        "dataset_rows": int(len(X)),
        "feature_count": int(X.shape[1]),
        "models_requested": recommended_models,
        "models_trained": list(selected_models.keys()),
        "unsupported_models": unsupported_models,
        "evaluation_metrics_requested": requested_metrics,
        "validation_strategy": validation_strategy,
        "training_times_seconds": {
            name: float(seconds) for name, seconds in training_times.items()
        },
        "model_results": {
            name: {
                "test_results": test_results[name],
                "cross_validation_results": cv_results[name],
            }
            for name in selected_models
        },
    }
