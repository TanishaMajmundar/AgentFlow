"""
model_selector.py
-----------------
Blended model recommender: 40% rule-based + 60% OpenML meta-learning.

Pipeline:
  1. Rule engine scores all candidate models (0-100) from dataset characteristics.
  2. OpenML meta-learning returns algorithm scores from similar historical datasets.
  3. Final blended score = 0.40 * rule_score + 0.60 * openml_score.
     (Falls back to 100% rule-based if OpenML is unavailable or timed out.)
  4. Top-N models are returned as CandidateModel objects with assigned roles.
"""

from __future__ import annotations
from ml_strategy_agent.schemas import ProblemType, DatasetSummary, CandidateModel
from ml_strategy_agent.rules import apply_suitability_rules
from ml_strategy_agent.openml_recommender import query_openml, OpenMLResult


# ── Constants ─────────────────────────────────────────────────────────────────

_ROLE_LABELS      = ["Baseline", "Primary Candidate", "Alternative Candidate"]
_WEIGHT_RULES     = 0.40
_WEIGHT_OPENML    = 0.60
_NEUTRAL_OPENML   = 50.0   # Score assigned when OpenML has no data for an algorithm


def select_models(
    problem_type:    ProblemType,
    dataset_summary: DatasetSummary,
    top_n:           int = 3,
    openml_timeout:  int = 35,
) -> tuple[list[CandidateModel], OpenMLResult]:
    """
    Score all candidate models and return the top-N with roles assigned.

    Returns:
        (candidates, openml_result) where openml_result carries context
        about similar datasets found and whether OpenML succeeded.
    """
    # Step 1: Rule-based scoring
    rule_scores = apply_suitability_rules(problem_type, dataset_summary)

    # Step 2: OpenML meta-learning
    is_regression  = (problem_type == ProblemType.REGRESSION)
    dataset_profile = _build_profile(dataset_summary, problem_type)
    problem_str     = "regression" if is_regression else "classification"

    openml_result = query_openml(
        profile        = dataset_profile,
        problem_type   = problem_str,
        top_k_datasets = 7,
        timeout_seconds= openml_timeout,
    )

    # Build OpenML score lookup
    openml_lookup: dict[str, float] = {}
    if openml_result.success:
        for rec in openml_result.recommendations:
            openml_lookup[rec.algorithm_name] = rec.openml_score

    # Step 3: Blend scores
    blended: list[tuple[str, float, list[str]]] = []

    for name, model_score in rule_scores.items():
        rule_s   = float(model_score.score)
        openml_s = openml_lookup.get(name)
        reasons  = list(model_score.reasons)

        if openml_result.success:
            if openml_s is not None:
                # Full blend
                final = _WEIGHT_RULES * rule_s + _WEIGHT_OPENML * openml_s
                oml_rec = next(
                    (r for r in openml_result.recommendations if r.algorithm_name == name),
                    None,
                )
                if oml_rec:
                    reasons.append(f"[OpenML] {oml_rec.reasoning}")
            else:
                # Algorithm not found in OpenML — use neutral score
                final = _WEIGHT_RULES * rule_s + _WEIGHT_OPENML * _NEUTRAL_OPENML
                reasons.append("[OpenML] No historical data on similar datasets — neutral score applied.")
        else:
            # OpenML unavailable — fall back to pure rule score
            final = rule_s

        blended.append((name, round(min(final, 100.0), 1), reasons))

    # Step 4: Sort and take top-N
    blended.sort(key=lambda x: x[1], reverse=True)

    candidates: list[CandidateModel] = []
    for i, (name, score, reasons) in enumerate(blended[:top_n]):
        role = _ROLE_LABELS[i] if i < len(_ROLE_LABELS) else f"Candidate {i + 1}"
        candidates.append(CandidateModel(
            name              = name,
            role              = role,
            suitability_score = int(round(score)),
            reasons           = reasons if reasons else ["General suitability for this problem type."],
        ))

    return candidates, openml_result


def _build_profile(ds: DatasetSummary, problem_type: ProblemType) -> dict:
    """Build the meta-feature profile dict passed to OpenML recommender."""
    is_regression = (problem_type == ProblemType.REGRESSION)
    return {
        "num_rows":        ds.num_rows,
        "num_features":    ds.num_features,
        "num_numeric":     ds.num_features if ds.has_numeric and not ds.has_categorical else 0,
        "num_categorical": 1 if ds.has_categorical else 0,
        "num_missing":     1 if ds.has_missing_values else 0,
        "num_classes":     0 if is_regression else (
            2 if problem_type == ProblemType.BINARY_CLASSIFICATION else 3
        ),
        "is_regression":   is_regression,
    }
