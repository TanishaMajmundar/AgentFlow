"""Shared registry of supported classification and regression estimators."""

from sklearn.base import clone
from sklearn.linear_model import (
    LogisticRegression, LinearRegression, Ridge, Lasso, ElasticNet
)
from sklearn.ensemble import (
    RandomForestClassifier, RandomForestRegressor,
    GradientBoostingClassifier, GradientBoostingRegressor,
    AdaBoostClassifier, ExtraTreesClassifier, ExtraTreesRegressor,
    HistGradientBoostingClassifier,
)
from sklearn.svm import SVC, SVR
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.naive_bayes import GaussianNB

RANDOM_STATE = 42

MODEL_REGISTRY = {
    "classification": {
        "Logistic Regression": LogisticRegression(
            max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE
        ),
        "K-Nearest Neighbors (KNN)": KNeighborsClassifier(n_neighbors=5),
        "Decision Tree": DecisionTreeClassifier(
            class_weight="balanced", random_state=RANDOM_STATE
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=100, class_weight="balanced",
            random_state=RANDOM_STATE, n_jobs=1
        ),
        "Support Vector Machine (SVM)": SVC(
            probability=True, class_weight="balanced", random_state=RANDOM_STATE
        ),
        "Gaussian Naive Bayes": GaussianNB(),
        "Gradient Boosting": GradientBoostingClassifier(random_state=RANDOM_STATE),
        "AdaBoost": AdaBoostClassifier(random_state=RANDOM_STATE),
        "Extra Trees": ExtraTreesClassifier(
            n_estimators=100, class_weight="balanced",
            random_state=RANDOM_STATE, n_jobs=1
        ),
        "HistGradientBoosting": HistGradientBoostingClassifier(
            random_state=RANDOM_STATE
        ),
    },
    "regression": {
        "Linear Regression": LinearRegression(),
        "Ridge Regression": Ridge(),
        "Lasso Regression": Lasso(max_iter=5000),
        "ElasticNet": ElasticNet(max_iter=5000),
        "KNN Regressor": KNeighborsRegressor(n_neighbors=5),
        "Decision Tree Regressor": DecisionTreeRegressor(random_state=RANDOM_STATE),
        "Random Forest Regressor": RandomForestRegressor(
            n_estimators=100, random_state=RANDOM_STATE, n_jobs=1
        ),
        "SVR": SVR(),
        "Gradient Boosting Regressor": GradientBoostingRegressor(
            random_state=RANDOM_STATE
        ),
        "Extra Trees Regressor": ExtraTreesRegressor(
            n_estimators=100, random_state=RANDOM_STATE, n_jobs=1
        ),
    },
}


def get_models(problem_type, model_names):
    """Clone and return only the requested models; also report unknown names."""
    if problem_type not in MODEL_REGISTRY:
        raise ValueError(
            f"Unsupported problem type: {problem_type}. "
            f"Choose from {list(MODEL_REGISTRY)}."
        )

    available_models = MODEL_REGISTRY[problem_type]
    selected_models = {}
    unsupported_models = []

    for model_name in model_names:
        if model_name in available_models:
            selected_models[model_name] = clone(available_models[model_name])
        else:
            unsupported_models.append(model_name)

    return selected_models, unsupported_models
