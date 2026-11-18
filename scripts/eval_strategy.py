"""Does OpenML meta-learning pick better candidate models than rules alone?

For each dataset: the Data Agent runs once; the Strategy Agent runs in both modes and
its top-k candidates are trained and scored (cross-validation on the training data,
and the untouched test split).

Caveats printed with the results:
- Test splits are small, so differences under ~0.02 are noise.
- The Data Agent applies SMOTE before saving the training data on imbalanced targets,
  which inflates the CV numbers. Trust the TEST column more.
"""
import argparse
import contextlib
import io
import json
import os
import sys
import time
from pathlib import Path

os.environ["AGENTFLOW_USE_OPENML"] = "1"   # keep the real OpenML function inside the wrapper
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

import ml_strategy_agent.model_selector as ms
from ml_strategy_agent.openml_recommender import OpenMLResult
from backend.agents import real_strategy_agent as rsa
from backend.agents.real_data_agent import real_data_agent
from Training_Agent.training_evaluation_agent import run_training_evaluation_agent

REAL_OPENML = ms.query_openml
MARGIN = 0.02
LOWER_IS_BETTER = {"mae", "rmse"}


def _no_openml(*args, **kwargs):
    return OpenMLResult(success=False, message="disabled for this run")


MODES = {"rules": _no_openml, "openml": REAL_OPENML}


def load_frame(path):
    p = Path(path)
    return pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_csv(p)


def score(name, kind, primary, validation, Xtr, ytr, Xte, yte):
    plan = {"problem_type": kind, "recommended_models": [name],
            "evaluation_metrics": [primary], "validation_strategy": validation}
    try:
        out = run_training_evaluation_agent(Xtr, ytr, plan, X_test=Xte, y_test=yte)
        res = out["model_results"][name]
        return {"cv": res["cross_validation_results"][f"{primary}_mean"],
                "test": res["test_results"][primary]}
    except Exception as e:
        return {"error": str(e)[:150]}


def fmt(x):
    return "  n/a " if x is None else f"{x:6.3f}"


def run_case(case, top):
    print("\n" + "=" * 78)
    print(f"{case['name']}   ({Path(case['file']).name})")
    d = real_data_agent(case["file"], case["target"], case["problem"])
    kind, target = d["problem_type"], d["target_column"]
    tr, te = load_frame(d["artifacts"]["train"]), load_frame(d["artifacts"]["test"])
    Xtr, ytr = tr.drop(columns=[target]), tr[target]
    Xte, yte = te.drop(columns=[target]), te[target]
    if kind == "classification":
        folds = max(2, min(5, int(ytr.value_counts().min())))
        validation = {"type": "stratified_k_fold", "n_splits": folds}
    else:
        validation = {"type": "k_fold", "n_splits": 5}
    print(f"{kind} | {d['rows']} rows | train {len(tr)} / test {len(te)} | "
          f"{d['final_feature_count']} features")

    cache, report, primary, label = {}, {}, None, None
    for mode, fn in MODES.items():
        ms.query_openml = fn
        buf = io.StringIO()
        t0 = time.time()
        with contextlib.redirect_stdout(buf):
            s = rsa.real_strategy_agent(case["problem"], target, d)
        secs = time.time() - t0
        primary = s["primary_metric"]
        label = s.get("primary_metric_label", primary)
        names = s["models"][:top]
        for n in names:
            if n not in cache:
                cache[n] = score(n, kind, primary, validation, Xtr, ytr, Xte, yte)
        report[mode] = {"seconds": round(secs, 1), "models": names,
                        "openml_used": mode == "openml" and "similar tasks found" in buf.getvalue()}

    pick = min if primary in LOWER_IS_BETTER else max

    def best(names, key):
        ok = [n for n in names if key in cache[n]]
        return pick(ok, key=lambda n: cache[n][key]) if ok else None

    print(f"metric: {label} (key '{primary}')\n")
    summary = {}
    for mode, r in report.items():
        tag = ""
        if mode == "openml":
            tag = "  [OpenML ran]" if r["openml_used"] else "  [OpenML FAILED -> fell back to rules: comparison not valid]"
        print(f"{mode.upper():7} strategy took {r['seconds']:5.1f}s{tag}")
        for n in r["models"]:
            c = cache[n]
            line = c["error"] if "error" in c else f"test {fmt(c['test'])}   cv {fmt(c['cv'])}"
            print(f"   {n:34} {line}")
        bt, bc = best(r["models"], "test"), best(r["models"], "cv")
        summary[mode] = {"best_test": bt, "best_test_score": cache[bt]["test"] if bt else None,
                         "best_cv": bc, "best_cv_score": cache[bc]["cv"] if bc else None,
                         **r}
        print(f"   -> best on test: {bt}   best on cv: {bc}\n")

    verdict = "n/a"
    r_s, o_s = summary["rules"]["best_test_score"], summary["openml"]["best_test_score"]
    if r_s is not None and o_s is not None:
        delta = (o_s - r_s) * (-1 if primary in LOWER_IS_BETTER else 1)
        if not report["openml"]["openml_used"]:
            verdict = "invalid (OpenML did not run)"
        elif delta > MARGIN:
            verdict = f"OpenML better by {delta:.3f}"
        elif delta < -MARGIN:
            verdict = f"rules better by {-delta:.3f}"
        else:
            verdict = f"tie (difference {delta:+.3f} is within noise)"
    print(f"VERDICT (test score, margin {MARGIN}): {verdict}")
    return {"case": case["name"], "kind": kind, "metric": primary, "verdict": verdict,
            "modes": summary, "scores": cache}


ap = argparse.ArgumentParser()
ap.add_argument("--spec", default="scripts/strategy_cases.json")
ap.add_argument("--top", type=int, default=3, help="candidates each strategy gets to train")
args = ap.parse_args()

cases = json.loads(Path(args.spec).read_text(encoding="utf-8"))
results = [run_case(c, args.top) for c in cases]

print("\n" + "=" * 78 + "\nSUMMARY")
for r in results:
    print(f"  {r['case']:10} {r['kind']:15} {r['verdict']}")
out = ROOT / "artifacts" / "strategy_eval.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
print("\nsaved:", out)