"""
rules.py
--------
Rule-based suitability scoring engine for ML model recommendation.

Each rule examines dataset characteristics and adjusts candidate model scores.
Scores represent RECOMMENDATION SUITABILITY (0-100), NOT predicted accuracy.
All rules are additive/subtractive deltas from a starting base of 50.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from ml_strategy_agent.schemas import (
    ProblemType, DatasetSummary, BalanceStatus, DatasetSize
)


# ── Candidate Pools ──────────────────────────────────────────────────────────

CLASSIFICATION_CANDIDATES: list[str] = [
    "Logistic Regression",
    "Decision Tree",
    "Random Forest",
    "Support Vector Machine (SVM)",
    "K-Nearest Neighbors (KNN)",
    "Naive Bayes",
    "Gradient Boosting",
    "XGBoost",
]

REGRESSION_CANDIDATES: list[str] = [
    "Linear Regression",
    "Decision Tree Regressor",
    "Random Forest Regressor",
    "Support Vector Regressor (SVR)",
    "Gradient Boosting Regressor",
    "XGBoost Regressor",
    "Ridge Regression",
    "Lasso Regression",
]


# ── Score Record ─────────────────────────────────────────────────────────────

@dataclass
class ModelScore:
    name:    str
    score:   int          = 50   # Base score
    reasons: list[str]    = field(default_factory=list)

    def adjust(self, delta: int, reason: str) -> None:
        self.score = max(0, min(100, self.score + delta))
        self.reasons.append(reason)


# ── Rule Engine ───────────────────────────────────────────────────────────────

def apply_suitability_rules(
    problem_type:    ProblemType,
    dataset_summary: DatasetSummary,
) -> dict[str, ModelScore]:
    """
    Apply all suitability rules to score candidate models.

    Returns:
        dict of {model_name: ModelScore}, sorted by score descending.
    """
    pool = (
        CLASSIFICATION_CANDIDATES
        if problem_type in (ProblemType.BINARY_CLASSIFICATION, ProblemType.MULTICLASS_CLASSIFICATION)
        else REGRESSION_CANDIDATES
    )
    scores: dict[str, ModelScore] = {name: ModelScore(name=name) for name in pool}

    # ── Rule 1: Dataset Size ───────────────────────────────────────────────
    _apply_size_rules(scores, dataset_summary.size_category)

    # ── Rule 2: Feature Type Mix ───────────────────────────────────────────
    _apply_feature_type_rules(scores, dataset_summary)

    # ── Rule 3: Numerical Scaling ─────────────────────────────────────────
    if dataset_summary.has_numeric:
        _adj(scores, "Support Vector Machine (SVM)",   +10, "Benefits from scaled numerical features")
        _adj(scores, "Support Vector Regressor (SVR)", +10, "Benefits from scaled numerical features")
        _adj(scores, "K-Nearest Neighbors (KNN)",      +10, "Distance metric benefits from scaling")
        _adj(scores, "Logistic Regression",            +5,  "Converges faster with scaled features")
        _adj(scores, "Linear Regression",              +5,  "More numerically stable with scaling")
        _adj(scores, "Ridge Regression",               +8,  "L2 penalty benefits from scaled features")
        _adj(scores, "Lasso Regression",               +8,  "L1 penalty benefits from scaled features")

    # ── Rule 4: Class Imbalance ───────────────────────────────────────────
    if dataset_summary.balance_status == BalanceStatus.IMBALANCED:
        _adj(scores, "Random Forest",                  +12, "class_weight='balanced' handles imbalance")
        _adj(scores, "XGBoost",                        +12, "scale_pos_weight parameter for imbalance")
        _adj(scores, "Gradient Boosting",              +8,  "Robust to moderate class imbalance")
        _adj(scores, "Logistic Regression",            +6,  "class_weight='balanced' available")
        _adj(scores, "Support Vector Machine (SVM)",   +5,  "class_weight='balanced' available")
        _adj(scores, "Naive Bayes",                    -12, "Sensitive to class imbalance")
        _adj(scores, "K-Nearest Neighbors (KNN)",      -12, "Biased toward majority class")
        _adj(scores, "Decision Tree",                  -5,  "Overfits majority class without weighting")

    # ── Rule 5: Text Features ─────────────────────────────────────────────
    if dataset_summary.has_text:
        _adj(scores, "Naive Bayes",                    +18, "Excellent for text/NLP bag-of-words features")
        _adj(scores, "Logistic Regression",            +12, "Strong with TF-IDF text features")
        _adj(scores, "Linear Regression",              +10, "Works well with text feature vectors")
        _adj(scores, "Support Vector Machine (SVM)",   +12, "Effective in high-dimensional text spaces")
        _adj(scores, "K-Nearest Neighbors (KNN)",      -15, "Poor in high-dimensional sparse text spaces")
        _adj(scores, "Random Forest",                  -5,  "Less effective on sparse high-dim text")

    # ── Rule 6: Missing Values ────────────────────────────────────────────
    if dataset_summary.has_missing_values:
        _adj(scores, "XGBoost",                        +12, "Built-in missing value handling")
        _adj(scores, "XGBoost Regressor",              +12, "Built-in missing value handling")
        _adj(scores, "Random Forest",                  +6,  "Robust to missing values via ensemble")
        _adj(scores, "Random Forest Regressor",        +6,  "Robust to missing values via ensemble")
        _adj(scores, "Gradient Boosting",              +5,  "Tolerates missing values well")
        _adj(scores, "Gradient Boosting Regressor",    +5,  "Tolerates missing values well")
        _adj(scores, "K-Nearest Neighbors (KNN)",      -12, "Cannot handle missing values directly")
        _adj(scores, "Support Vector Machine (SVM)",   -6,  "Requires complete feature vectors")
        _adj(scores, "Support Vector Regressor (SVR)", -6,  "Requires complete feature vectors")

    # ── Rule 7: Multiclass Classification ────────────────────────────────
    if problem_type == ProblemType.MULTICLASS_CLASSIFICATION:
        _adj(scores, "Random Forest",                  +10, "Natively supports multiclass out-of-box")
        _adj(scores, "XGBoost",                        +10, "Efficient multiclass via softmax objective")
        _adj(scores, "Gradient Boosting",              +10, "Supports multiclass classification")
        _adj(scores, "Logistic Regression",            +5,  "OVR/multinomial multiclass support")
        _adj(scores, "Naive Bayes",                    +5,  "Naturally probabilistic multiclass model")
        _adj(scores, "Support Vector Machine (SVM)",   -8,  "OVR strategy adds O(n²) complexity at scale")
        _adj(scores, "K-Nearest Neighbors (KNN)",      -5,  "Slows down significantly with more classes")

    # ── Rule 8: Regression-specific ──────────────────────────────────────
    if problem_type == ProblemType.REGRESSION:
        _adj(scores, "Linear Regression",              +10, "Interpretable regression baseline")
        _adj(scores, "Ridge Regression",               +8,  "Prevents overfitting via L2 regularization")
        _adj(scores, "Lasso Regression",               +6,  "Automatic feature selection via L1")

    return dict(sorted(scores.items(), key=lambda x: x[1].score, reverse=True))


# ── Private Helpers ───────────────────────────────────────────────────────────

def _apply_size_rules(scores: dict[str, ModelScore], size: DatasetSize) -> None:
    if size == DatasetSize.SMALL:
        _adj(scores, "Support Vector Machine (SVM)",   +18, "Excellent on small datasets")
        _adj(scores, "Support Vector Regressor (SVR)", +18, "Excellent on small datasets")
        _adj(scores, "K-Nearest Neighbors (KNN)",      +15, "Effective on small, clean datasets")
        _adj(scores, "Logistic Regression",            +10, "Fast and reliable on small data")
        _adj(scores, "Naive Bayes",                    +10, "Efficient with limited data")
        _adj(scores, "Ridge Regression",               +10, "Stable on small data with regularization")
        _adj(scores, "Lasso Regression",               +8,  "Handles sparse small datasets well")
        _adj(scores, "XGBoost",                        -12, "Prone to overfitting on very small datasets")
        _adj(scores, "XGBoost Regressor",              -12, "Prone to overfitting on very small datasets")
        _adj(scores, "Random Forest",                  -6,  "Needs moderate data for stable trees")
        _adj(scores, "Random Forest Regressor",        -6,  "Needs moderate data for stable trees")

    elif size == DatasetSize.MEDIUM:
        _adj(scores, "Random Forest",                  +15, "Excellent on medium tabular data")
        _adj(scores, "Random Forest Regressor",        +15, "Excellent on medium tabular data")
        _adj(scores, "Gradient Boosting",              +12, "Strong performer on structured medium data")
        _adj(scores, "Gradient Boosting Regressor",    +12, "Strong performer on structured medium data")
        _adj(scores, "XGBoost",                        +12, "Highly competitive on medium tabular data")
        _adj(scores, "XGBoost Regressor",              +12, "Highly competitive on medium tabular data")
        _adj(scores, "Logistic Regression",            +5,  "Reliable, interpretable baseline")
        _adj(scores, "Linear Regression",              +5,  "Reliable, interpretable regression baseline")

    elif size == DatasetSize.LARGE:
        _adj(scores, "XGBoost",                        +20, "Scales excellently to large datasets")
        _adj(scores, "XGBoost Regressor",              +20, "Scales excellently to large datasets")
        _adj(scores, "Gradient Boosting",              +15, "Strong on large structured data")
        _adj(scores, "Gradient Boosting Regressor",    +15, "Strong on large structured data")
        _adj(scores, "Random Forest",                  +10, "Parallelizable; good at large scale")
        _adj(scores, "Random Forest Regressor",        +10, "Parallelizable; good at large scale")
        _adj(scores, "K-Nearest Neighbors (KNN)",      -22, "O(n) prediction cost — very slow at scale")
        _adj(scores, "Support Vector Machine (SVM)",   -18, "Quadratic training cost on large datasets")
        _adj(scores, "Support Vector Regressor (SVR)", -18, "Quadratic training cost on large datasets")
        _adj(scores, "Naive Bayes",                    -5,  "May underfit complex large feature spaces")


def _apply_feature_type_rules(
    scores: dict[str, ModelScore],
    ds:     DatasetSummary,
) -> None:
    # Pure categorical features
    if ds.has_categorical and not ds.has_numeric:
        _adj(scores, "Naive Bayes",                    +10, "Native categorical distribution modelling")
        _adj(scores, "Decision Tree",                  +10, "Handles categorical splits natively")
        _adj(scores, "Decision Tree Regressor",        +10, "Handles categorical splits natively")

    # Mixed feature types
    if ds.has_numeric and ds.has_categorical:
        _adj(scores, "Random Forest",                  +10, "Handles mixed numeric + categorical well")
        _adj(scores, "Random Forest Regressor",        +10, "Handles mixed numeric + categorical well")
        _adj(scores, "XGBoost",                        +10, "Robust to mixed feature types")
        _adj(scores, "XGBoost Regressor",              +10, "Robust to mixed feature types")
        _adj(scores, "Gradient Boosting",              +6,  "Handles mixed feature types")
        _adj(scores, "Gradient Boosting Regressor",    +6,  "Handles mixed feature types")


def _adj(
    scores: dict[str, ModelScore],
    name:   str,
    delta:  int,
    reason: str,
) -> None:
    """Adjust score only if the model is in the active candidate pool."""
    if name in scores:
        scores[name].adjust(delta, reason)
