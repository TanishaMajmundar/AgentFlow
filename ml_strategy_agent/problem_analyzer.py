"""
problem_analyzer.py
-------------------
Determines the ML problem type (classification vs regression,
binary vs multiclass) from the problem statement and target distribution.
"""

from __future__ import annotations
from ml_strategy_agent.schemas import ProblemType, DataAgentOutput


# ── Keyword Heuristics ───────────────────────────────────────────────────────

_CLASSIFICATION_KEYWORDS = [
    "classify", "classification", "predict whether", "predict if",
    "churn", "fraud", "spam", "detect", "is it", "will the customer",
    "yes or no", "true or false", "belong", "category", "class",
    "disease", "approve", "reject", "sentiment", "label", "survived",
    "default", "dropout", "click", "conversion", "intent",
]

_REGRESSION_KEYWORDS = [
    "predict the price", "predict the value", "predict the amount",
    "forecast", "estimate", "how much", "how many", "sales",
    "revenue", "temperature", "score", "rating", "price", "cost",
    "demand", "age", "salary", "wage", "duration", "time", "mpg",
    "mileage", "count", "total", "volume", "distance", "area",
]


def analyze_problem(
    problem_statement: str,
    data_agent_output: DataAgentOutput,
) -> tuple[ProblemType, str]:
    """
    Identify the ML problem type from the problem statement and target data.

    Decision cascade (strongest signal first):
    1. Target class_counts  → 2 classes = binary, >2 = multiclass
    2. Continuous target statistics → regression
    3. Keyword matching on problem statement
    4. Fallback: UNKNOWN → Gemini will decide

    Returns:
        (ProblemType, reasoning_string)
    """
    target_dist = data_agent_output.metadata.target_distribution
    stmt_lower  = problem_statement.lower()

    # 1. Class counts -- strongest structural signal
    if target_dist.class_counts:
        n = len(target_dist.class_counts)
        if n == 2:
            return (
                ProblemType.BINARY_CLASSIFICATION,
                f"Target has exactly 2 classes {list(target_dist.class_counts.keys())} -> Binary Classification.",
            )
        elif n > 2:
            return (
                ProblemType.MULTICLASS_CLASSIFICATION,
                f"Target has {n} distinct classes -> Multiclass Classification.",
            )

    # 2. Continuous target stats -> regression
    if (target_dist.min_value is not None
            and target_dist.max_value is not None
            and target_dist.mean_value is not None):
        return (
            ProblemType.REGRESSION,
            f"Target contains continuous numeric values "
            f"(min={target_dist.min_value}, max={target_dist.max_value}, "
            f"mean={target_dist.mean_value:.2f}) -> Regression.",
        )

    # 3. Keyword scoring
    reg_score   = sum(1 for kw in _REGRESSION_KEYWORDS       if kw in stmt_lower)
    cls_score   = sum(1 for kw in _CLASSIFICATION_KEYWORDS   if kw in stmt_lower)

    if reg_score > cls_score:
        return (
            ProblemType.REGRESSION,
            f"Keyword analysis: regression ({reg_score}) > classification ({cls_score}) -> Regression.",
        )
    if cls_score > 0:
        return (
            ProblemType.BINARY_CLASSIFICATION,
            f"Keyword analysis: classification signals ({cls_score}) found -> Binary Classification (assumed).",
        )

    # 4. Fallback — needs LLM
    return (
        ProblemType.UNKNOWN,
        "Could not determine problem type from data or keywords. Gemini will resolve.",
    )
