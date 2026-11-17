"""Converts the orchestrator's workflow document into the shape the React frontend expects."""

AGENT_MAP = [("data", "data_agent"), ("strategy", "ml_strategy_agent"), ("training", "training_agent")]
STATUS_MAP = {"pending": "waiting", "running": "running", "completed": "done", "failed": "error"}
RUNNING_MSG = {
    "data": "Analyzing dataset…",
    "strategy": "Identifying problem type…",
    "training": "Training candidate models…",
}


def _score(result, metric):
    if not result or not metric:
        return None
    return (result.get("metrics") or {}).get(metric)


def _agent_output(key, out, metric):
    if not out:
        return None
    if key == "data":
        return {
            "rows": out.get("rows"),
            "columns": out.get("columns"),
            "missing_values": out.get("missing_values"),
            "duplicates": out.get("duplicates"),
            "preprocessing": out.get("preprocessing", []),
        }
    if key == "strategy":
        return {
            "problem_type": out.get("problem_type"),
            "models": out.get("models", []),
            "primary_metric": out.get("primary_metric_label") or out.get("primary_metric"),
        }
    if key == "training":
        return {"results": [
            {"name": r.get("model_name"), "score": _score(r, metric)}
            for r in out.get("results", []) if r.get("status") == "success"
        ]}
    return None


def build_status(wf):
    results = wf.get("results") or {}
    metric = (results.get("ml_strategy_agent") or {}).get("primary_metric")
    agents = []
    for fkey, bkey in AGENT_MAP:
        st = STATUS_MAP.get((wf.get("agents") or {}).get(bkey, "pending"), "waiting")
        message = ""
        if st == "running":
            message = RUNNING_MSG[fkey]
        elif st == "error":
            message = wf.get("error") or "This agent failed."
        agents.append({
            "key": fkey,
            "status": st,
            "message": message,
            "output": _agent_output(fkey, results.get(bkey), metric) if st == "done" else None,
        })
    return {
        "project_id": wf.get("project_id", wf["workflow_id"]),
        "project_name": wf.get("project_name"),
        "dataset_name": wf.get("dataset_name"),
        "target_column": wf.get("target_column"),
        "state": "queued" if wf["status"] == "created" else wf["status"],
        "agents": agents,
        "error": wf.get("error"),
    }


def build_results(wf):
    res = wf.get("results") or {}
    data = res.get("data_agent") or {}
    strat = res.get("ml_strategy_agent") or {}
    train = res.get("training_agent") or {}
    metric = strat.get("primary_metric")
    label = strat.get("primary_metric_label") or metric

    models = []
    for r in train.get("results", []):
        score = _score(r, metric)
        if r.get("status") == "success" and score is not None:
            models.append({"name": r.get("model_name"), "score": score})

    best = wf.get("final_model")
    final = None
    if best:
        final = {"name": best.get("model_name"), "score": _score(best, metric), "metric": label}

    return {
        "project_id": wf.get("project_id", wf["workflow_id"]),
        "project_name": wf.get("project_name"),
        "problem_statement": wf.get("problem_statement"),
        "target_column": wf.get("target_column"),
        "dataset": {
            "filename": wf.get("dataset_name"),
            "rows": data.get("rows"),
            "columns": data.get("columns"),
            "missing_values": data.get("missing_values"),
            "duplicates": data.get("duplicates"),
            "numerical_features": data.get("numerical_features"),
            "categorical_features": data.get("categorical_features"),
            "preprocessing": data.get("preprocessing", []),
        },
        "strategy": {
            "problem_type": strat.get("problem_type"),
            "primary_metric": label,
            "models": strat.get("models", []),
        },
        "models": models,
        "final_model": final,
    }