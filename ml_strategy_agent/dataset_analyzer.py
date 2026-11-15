"""
dataset_analyzer.py
-------------------
Converts raw DatasetMetadata from the Data Agent into a concise
DatasetSummary — the human-friendly characterization used by rules.py.
"""

from __future__ import annotations
from ml_strategy_agent.schemas import (
    DataAgentOutput, DatasetMetadata, DatasetSummary,
    DatasetSize, BalanceStatus, ProblemType,
)


# ── Thresholds ────────────────────────────────────────────────────────────────
_SMALL_THRESHOLD   = 1_000
_MEDIUM_THRESHOLD  = 50_000
_BALANCE_THRESHOLD = 0.30   # minority class ratio below this → imbalanced


def analyze_dataset(
    data_agent_output: DataAgentOutput,
    problem_type:      ProblemType,
) -> DatasetSummary:
    """
    Derive a DatasetSummary from raw DatasetMetadata.

    Args:
        data_agent_output: Output from the Data Agent (Member 3).
        problem_type:      Already-identified ML problem type.

    Returns:
        DatasetSummary with size category, feature breakdown, and balance status.
    """
    meta = data_agent_output.metadata

    size_category                            = _classify_size(meta.num_rows)
    has_numeric                              = meta.num_numeric_features > 0
    has_categorical                          = meta.num_categorical_features > 0
    has_text                                 = meta.num_text_features > 0
    has_missing                              = meta.num_missing_values > 0
    balance_status, minority_ratio, imb_ratio = _assess_balance(meta, problem_type)

    return DatasetSummary(
        size_category       = size_category,
        num_rows            = meta.num_rows,
        num_features        = meta.num_columns - 1,   # exclude target column
        has_numeric         = has_numeric,
        has_categorical     = has_categorical,
        has_text            = has_text,
        has_missing_values  = has_missing,
        balance_status      = balance_status,
        minority_class_ratio= minority_ratio,
        imbalance_ratio     = imb_ratio,
    )


# ── Private Helpers ───────────────────────────────────────────────────────────

def _classify_size(num_rows: int) -> DatasetSize:
    if num_rows < _SMALL_THRESHOLD:
        return DatasetSize.SMALL
    elif num_rows <= _MEDIUM_THRESHOLD:
        return DatasetSize.MEDIUM
    else:
        return DatasetSize.LARGE


def _assess_balance(
    meta:         DatasetMetadata,
    problem_type: ProblemType,
) -> tuple[BalanceStatus, float | None, float | None]:
    """
    Returns (BalanceStatus, minority_class_ratio, imbalance_ratio).
    imbalance_ratio = majority_count / minority_count  (higher = more imbalanced).
    """
    if problem_type == ProblemType.REGRESSION:
        return BalanceStatus.NOT_APPLICABLE, None, None

    class_counts = meta.target_distribution.class_counts
    if not class_counts or len(class_counts) < 2:
        return BalanceStatus.BALANCED, None, None

    counts          = list(class_counts.values())
    total           = sum(counts)
    minority        = min(counts)
    majority        = max(counts)
    minority_ratio  = minority / total
    imbalance_ratio = majority / minority if minority > 0 else float("inf")

    status = (
        BalanceStatus.IMBALANCED
        if minority_ratio < _BALANCE_THRESHOLD
        else BalanceStatus.BALANCED
    )
    return status, minority_ratio, imbalance_ratio
