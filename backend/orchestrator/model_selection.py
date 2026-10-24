import math

LOWER_IS_BETTER = {"rmse", "mae", "mse", "log_loss"}


def metric_direction(metric: str) -> str:
    return "min" if metric.lower() in LOWER_IS_BETTER else "max"


def _valid(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) \
        and not math.isnan(value) and not math.isinf(value)


def select_best_model(results: list[dict], primary_metric: str, direction: str | None = None):
    """
    results: [{"model_name": str, "status": "success"|"failed", "metrics": {...}}, ...]
    Returns the best result dict, or None if no model has a valid metric.
    """
    direction = direction or metric_direction(primary_metric)
    eligible = [
        r for r in results
        if r.get("status") == "success"
        and _valid((r.get("metrics") or {}).get(primary_metric))
    ]
    if not eligible:
        return None
    pick = min if direction == "min" else max
    return pick(eligible, key=lambda r: r["metrics"][primary_metric])