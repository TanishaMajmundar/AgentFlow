"""Hybrid target detection: rules shortlist -> (optional) LLM choice -> Python validation."""
from backend.orchestrator import llm_handler
from backend.orchestrator.target_detector import detect_target, infer_problem_type, validate_target


def analyze_target(df, problem_statement="", use_llm=None):
    rules = detect_target(df, problem_statement)
    if use_llm is None:
        use_llm = llm_handler.llm_enabled()
    rules_rec = rules.get("recommended")
    if not use_llm or not rules_rec:
        return rules

    by_name = {c["name"]: c for c in rules["columns"]}
    shortlist = [by_name[n] for n in rules.get("shortlist", []) if n in by_name]
    info = {"provider": llm_handler.provider_name(), "model": llm_handler.model_name()}

    try:
        ans = llm_handler.ask_for_target(problem_statement, shortlist)
        info["latency_s"] = ans.get("latency_s")
        lookup = {c["name"].lower(): c["name"] for c in shortlist}
        pick = lookup.get(str(ans.get("recommended", "")).strip().lower())
        if pick is None:
            raise ValueError(f"model chose '{ans.get('recommended')}', which is not a candidate column")
        check = validate_target(df, pick)
        if not check["valid"]:
            raise ValueError("model's choice failed validation: " + " ".join(check["problems"]))
    except Exception as e:                       # LLM down, bad JSON, invalid pick...
        return {**rules, "llm": {**info, "error": str(e)[:200]}}

    try:
        llm_conf = min(1.0, max(0.0, float(ans.get("confidence"))))
    except (TypeError, ValueError):
        llm_conf = 0.5
    llm_reason = str(ans.get("reason", "")).strip()[:300]
    agrees = pick == rules_rec

    result = dict(rules)
    result["source"] = "hybrid"
    result["rules_pick"] = rules_rec
    result["llm"] = {**info, "recommended": pick, "reason": llm_reason,
                     "agrees_with_rules": agrees}

    if agrees:
        result["confidence"] = round(min(0.98, max(rules["confidence"], llm_conf) + 0.05), 2)
        result["ambiguous"] = False
        result["reason"] = (rules["reason"] + " The language model independently chose the same column"
                            + (f": {llm_reason}" if llm_reason else "."))
    else:
        alts = [a for a in rules.get("alternatives", []) if a["column"] != pick]
        alts.insert(0, {"column": rules_rec, "score": None,
                        "problem_type": rules.get("problem_type"),
                        "reason": "preferred by rule-based scoring"})
        result.update({
            "recommended": pick,
            "problem_type": check["problem_type"],
            "confidence": round(min(0.6, llm_conf), 2),
            "ambiguous": True,                  # disagreement: make the user look
            "alternatives": alts[:5],
            "validation": check,
            "reason": (f"The language model chose '{pick}'"
                       + (f": {llm_reason}" if llm_reason else ".")
                       + f" Rule-based scoring preferred '{rules_rec}'."),
        })
    return result