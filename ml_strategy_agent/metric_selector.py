"""
metric_selector.py
------------------
Selects appropriate evaluation metrics and validation strategy
based on problem type and class balance status.
"""

from __future__ import annotations
from ml_strategy_agent.schemas import (
    ProblemType, DatasetSummary, BalanceStatus, MetricSet
)


# ── Metric Configurations ─────────────────────────────────────────────────────

_METRIC_CONFIGS: dict[str, dict] = {
    # Binary Classification
    "binary_balanced": {
        "primary":    "Accuracy",
        "secondary":  ["F1 Score", "ROC-AUC", "Precision", "Recall"],
        "validation": "5-Fold Stratified Cross-Validation",
        "folds":      5,
    },
    "binary_imbalanced": {
        "primary":    "F1 Score",
        "secondary":  ["Precision", "Recall", "ROC-AUC", "Matthews Correlation Coefficient (MCC)"],
        "validation": "5-Fold Stratified Cross-Validation",
        "folds":      5,
    },
    # Multiclass Classification
    "multiclass_balanced": {
        "primary":    "Accuracy",
        "secondary":  ["Macro F1 Score", "Weighted F1 Score", "ROC-AUC (OVR)"],
        "validation": "5-Fold Stratified Cross-Validation",
        "folds":      5,
    },
    "multiclass_imbalanced": {
        "primary":    "Macro F1 Score",
        "secondary":  ["Weighted F1 Score", "Precision (macro)", "Recall (macro)", "ROC-AUC (OVR)"],
        "validation": "5-Fold Stratified Cross-Validation",
        "folds":      5,
    },
    # Regression
    "regression": {
        "primary":    "R² Score",
        "secondary":  ["RMSE (Root Mean Squared Error)", "MAE (Mean Absolute Error)", "MAPE"],
        "validation": "5-Fold Cross-Validation",
        "folds":      5,
    },
}


def select_metrics(
    problem_type:    ProblemType,
    dataset_summary: DatasetSummary,
) -> MetricSet:
    """
    Return the appropriate primary and secondary metrics and validation strategy.

    Decision logic:
    - Binary balanced   → Accuracy + F1/AUC/P/R
    - Binary imbalanced → F1 primary + Precision/Recall/AUC/MCC
    - Multiclass balanced   → Accuracy + Macro F1
    - Multiclass imbalanced → Macro F1 primary
    - Regression        → R² + RMSE/MAE/MAPE
    """
    is_imbalanced = (dataset_summary.balance_status == BalanceStatus.IMBALANCED)

    key_map = {
        ProblemType.BINARY_CLASSIFICATION:     "binary_imbalanced"   if is_imbalanced else "binary_balanced",
        ProblemType.MULTICLASS_CLASSIFICATION:  "multiclass_imbalanced" if is_imbalanced else "multiclass_balanced",
        ProblemType.REGRESSION:                "regression",
        ProblemType.UNKNOWN:                   "binary_balanced",   # fallback
    }

    cfg = _METRIC_CONFIGS[key_map[problem_type]]
    return MetricSet(
        primary_metric      = cfg["primary"],
        secondary_metrics   = cfg["secondary"],
        validation_strategy = cfg["validation"],
        num_folds           = cfg.get("folds"),
    )
