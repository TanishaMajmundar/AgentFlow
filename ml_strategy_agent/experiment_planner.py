"""
experiment_planner.py
---------------------
Generates a structured, step-by-step experiment plan
for the Training Agent (Member 5) to execute.
"""

from __future__ import annotations
from ml_strategy_agent.schemas import (
    ProblemType, CandidateModel, MetricSet, ExperimentPlan, ExperimentStep
)


def create_plan(
    problem_type:  ProblemType,
    candidates:    list[CandidateModel],
    metrics:       MetricSet,
    target_column: str,
) -> ExperimentPlan:
    """
    Build a concrete, numbered experiment plan for the Training Agent.

    Args:
        problem_type:   Identified ML problem type.
        candidates:     Recommended candidate models (ordered by score).
        metrics:        Selected evaluation metrics and validation strategy.
        target_column:  Name of the target variable column.

    Returns:
        ExperimentPlan with ordered steps, baseline, and comparison models.
    """
    baseline          = candidates[0].name if candidates else "Baseline Model"
    comparison_models = [c.name for c in candidates[1:]]
    all_models        = [baseline] + comparison_models
    secondary_preview = ", ".join(metrics.secondary_metrics[:3])

    steps: list[ExperimentStep] = []
    n = 0  # step counter

    def step(description: str) -> None:
        nonlocal n
        n += 1
        steps.append(ExperimentStep(step_number=n, description=description))

    # ── 1. Split ───────────────────────────────────────────────────────────
    step(
        f"Split dataset into training set (80%) and hold-out test set (20%), "
        f"stratifying on column '{target_column}'."
    )

    # ── 2. Establish Baseline ──────────────────────────────────────────────
    step(
        f"Train baseline model — {baseline} — using default hyperparameters "
        f"with {metrics.validation_strategy}."
    )

    # ── 3+. Train Comparison Models ────────────────────────────────────────
    for model_name in comparison_models:
        step(
            f"Train comparison model — {model_name} — using default hyperparameters "
            f"with {metrics.validation_strategy}."
        )

    # ── Next: Cross-Validation Evaluation ─────────────────────────────────
    step(
        f"Evaluate all models ({', '.join(all_models)}) using "
        f"{metrics.validation_strategy} on the training set and record CV scores."
    )

    # ── Next: Metric Comparison ────────────────────────────────────────────
    step(
        f"Compare all models by primary metric ({metrics.primary_metric}) "
        f"and secondary metrics ({secondary_preview}). Tabulate results."
    )

    # ── Next: Select Best ──────────────────────────────────────────────────
    step(
        f"Select the best-performing model based on {metrics.primary_metric} "
        f"cross-validation score."
    )

    # ── Next: Hyperparameter Tuning ────────────────────────────────────────
    step(
        "Perform hyperparameter tuning on the selected best model using "
        "GridSearchCV or RandomizedSearchCV with 5-fold CV."
    )

    # ── Next: Final Evaluation ─────────────────────────────────────────────
    step(
        f"Evaluate the tuned final model on the hold-out test set "
        f"and report {metrics.primary_metric} as the official performance score."
    )

    # ── Problem-Specific Extras ────────────────────────────────────────────
    if problem_type in (
        ProblemType.BINARY_CLASSIFICATION,
        ProblemType.MULTICLASS_CLASSIFICATION,
    ):
        step(
            "Generate a confusion matrix and full classification report "
            "(precision, recall, F1 per class) on the test set."
        )

    if problem_type == ProblemType.REGRESSION:
        step(
            "Plot residual distribution and predicted-vs-actual scatter chart "
            "for visual error analysis of the final model."
        )

    # ── Final: Feature Importance ──────────────────────────────────────────
    step(
        "Extract and visualise feature importances (or coefficients) from the "
        "final model to support interpretability."
    )

    return ExperimentPlan(
        steps             = steps,
        baseline_model    = baseline,
        comparison_models = comparison_models,
    )
