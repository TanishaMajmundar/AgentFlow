"""
openml_recommender.py
---------------------
Meta-learning recommendation engine using the OpenML public benchmark platform.

Strategy:
1. Fetch all tasks of the target type from OpenML (includes meta-features per task).
2. Build a 7-dimensional meta-feature vector for the user's dataset.
3. Cosine similarity against all tasks → pick top-K most similar.
4. For each top task, fetch algorithm evaluation scores.
5. Aggregate raw scores, normalise 0-100, return ranked recommendations.

Runs in a daemon thread with a configurable timeout so it never blocks the main pipeline.
"""

from __future__ import annotations
import warnings
import threading
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

warnings.filterwarnings("ignore")


# ── Algorithm Name Mapping ───────────────────────────────────────────────────
# Maps OpenML flow name tokens → internal candidate names used in rules.py

_FLOW_TOKENS: list[tuple[str, str]] = [
    # Tree ensembles & Boosting
    ("randomforestclassifier",     "Random Forest"),
    ("randomforest",               "Random Forest"),
    ("gradientboostingclassifier", "Gradient Boosting"),
    ("gradientboosting",           "Gradient Boosting"),
    ("xgbclassifier",              "XGBoost"),
    ("xgboost",                    "XGBoost"),
    ("lightgbm",                   "LightGBM"),
    ("lgbm",                       "LightGBM"),
    ("catboost",                   "CatBoost"),
    # Linear / Logistic
    ("logisticregression",         "Logistic Regression"),
    ("logistic",                   "Logistic Regression"),
    ("sgdclassifier",              "Logistic Regression"),
    # SVM
    ("svc",                        "Support Vector Machine (SVM)"),
    ("svm",                        "Support Vector Machine (SVM)"),
    ("smo",                        "Support Vector Machine (SVM)"),
    # KNN & Trees
    ("kneighborsclassifier",       "K-Nearest Neighbors (KNN)"),
    ("kneighbors",                 "K-Nearest Neighbors (KNN)"),
    ("ibk",                        "K-Nearest Neighbors (KNN)"),
    ("decisiontreeclassifier",     "Decision Tree"),
    ("decisiontree",               "Decision Tree"),
    ("j48",                        "Decision Tree"),
    ("reptree",                    "Decision Tree"),
    # Naive Bayes
    ("gaussiannb",                 "Naive Bayes"),
    ("naivebayes",                 "Naive Bayes"),
    # Regression
    ("randomforestregressor",      "Random Forest Regressor"),
    ("gradientboostingregressor",  "Gradient Boosting Regressor"),
    ("xgbregressor",               "XGBoost Regressor"),
    ("linearregression",           "Linear Regression"),
    ("svr",                        "Support Vector Regressor (SVR)"),
    ("decisiontreeregressor",      "Decision Tree Regressor"),
    ("ridge",                      "Ridge Regression"),
    ("lasso",                      "Lasso Regression"),
]


def _map_flow(raw: str) -> Optional[str]:
    """Map a raw OpenML flow name to an internal algorithm name."""
    key = raw.lower().replace(" ", "").replace("-", "").replace("_", "").replace(".", "")
    for token, internal in _FLOW_TOKENS:
        if token in key:
            return internal
    return None


# ── Data Containers ──────────────────────────────────────────────────────────

@dataclass
class OpenMLRecommendation:
    algorithm_name:         str
    openml_score:           float
    similar_datasets_found: int
    reasoning:              str


@dataclass
class OpenMLResult:
    recommendations:   list[OpenMLRecommendation] = field(default_factory=list)
    similar_datasets:  list[str]                  = field(default_factory=list)
    num_similar_found: int                        = 0
    success:           bool                       = False
    message:           str                        = ""


# ── Meta-Feature Vectorization ───────────────────────────────────────────────

def _build_vector(
    nrows:   float,
    nfeat:   float,
    nnumer:  float,
    ncat:    float,
    nmiss:   float,
    nclass:  float,
    is_reg:  bool,
) -> np.ndarray:
    nfeat = max(nfeat, 1)
    return np.array([
        np.log1p(nrows),
        np.log1p(nfeat),
        nnumer / nfeat,
        ncat   / nfeat,
        nmiss  / max(nrows * nfeat, 1),
        float(min(nclass, 20)),
        float(is_reg),
    ], dtype=float)


def _build_query_vec(profile: dict, is_reg: bool) -> np.ndarray:
    return _build_vector(
        profile.get("num_rows", 1),
        profile.get("num_features", 1),
        profile.get("num_numeric", 0),
        profile.get("num_categorical", 0),
        profile.get("num_missing", 0),
        profile.get("num_classes", 0),
        is_reg,
    )


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(np.dot(a, b) / (na * nb)) if na > 0 and nb > 0 else 0.0


# ── Public Entry Point ───────────────────────────────────────────────────────

def query_openml(
    profile:         dict,
    problem_type:    str,        # "classification" or "regression"
    top_k_datasets:  int  = 7,
    timeout_seconds: int  = 35,
) -> OpenMLResult:
    """
    Query OpenML for algorithm performance on similar historical datasets.

    Runs in a thread; returns a failed result if timeout is exceeded.
    """
    result_holder: list[Optional[OpenMLResult]] = [None]
    exc_holder:    list[Optional[Exception]]    = [None]

    def _worker():
        try:
            result_holder[0] = _fetch_and_score(profile, problem_type, top_k_datasets)
        except Exception as e:
            exc_holder[0] = e

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds)

    if thread.is_alive():
        return OpenMLResult(
            success=False,
            message=f"OpenML timed out after {timeout_seconds}s — using rule-based scores only.",
        )
    if exc_holder[0]:
        return OpenMLResult(success=False, message=f"OpenML error: {exc_holder[0]}")

    return result_holder[0] or OpenMLResult(success=False, message="No result returned.")


# ── Curated OpenML Benchmark Suites ───────────────────────────────────────────
# Curated suites (OpenML-CC18 suite 99 for classification, classic regression suite)
# have guaranteed, high-quality benchmark run evaluations on OpenML.
_CURATED_CLASSIFICATION_TASKS: list[int] = [
    3, 6, 11, 12, 14, 15, 16, 18, 22, 23, 28, 29, 31, 32, 37, 44, 46, 54,
    181, 182, 188, 300, 307, 458, 469, 554, 1049, 1050, 1053, 1063, 1067, 1068,
    1461, 1468, 1475, 1480, 1485, 1486, 1487, 1489, 1494, 1497, 1501, 1510, 1590,
    4134, 4534, 4538, 41142, 41143, 41146, 41150, 41156, 41157, 41159, 41161, 41162,
    41163, 41164, 41165, 41166, 41167, 41168, 41169, 7592, 14952, 14965, 146195,
    146825, 167119, 167120, 167121, 167124,
]

_CURATED_REGRESSION_TASKS: list[int] = [
    2280, 2281, 2282, 2283, 2284, 2285, 2286, 2287, 2288, 2289, 2290, 2291,
    2292, 2293, 2294, 2295, 2296, 2297, 2298, 2299, 2300, 4833, 4834, 4835,
    4836, 4837, 4838, 4839, 4840, 4841, 4842, 4843, 4844, 4845, 4846, 4847,
    4848, 4849, 4850,
]


def _fetch_and_score(
    profile:      dict,
    problem_type: str,
    top_k:        int,
) -> OpenMLResult:
    import openml

    openml.config.apikey    = ""
    openml.config.verbosity = 0

    is_reg    = (problem_type == "regression")
    query_vec = _build_query_vec(profile, is_reg)

    curated_ids = _CURATED_REGRESSION_TASKS if is_reg else _CURATED_CLASSIFICATION_TASKS
    print("      [OpenML] Querying curated benchmark task repository...", flush=True)
    try:
        tasks_df = openml.tasks.list_tasks(
            task_id=curated_ids,
            output_format="dataframe",
        )
    except Exception:
        task_type_id = 2 if is_reg else 1
        try:
            tasks_df = openml.tasks.list_tasks(type=task_type_id, output_format="dataframe")
        except Exception:
            tasks_df = None

    if tasks_df is None or tasks_df.empty:
        return OpenMLResult(
            success=False,
            message="OpenML returned no tasks for this problem type.",
        )

    # ── Similarity computation ────────────────────────────────────────────
    META_COLUMNS = {
        "NumberOfInstances":        "nrows",
        "NumberOfFeatures":         "nfeat",
        "NumberOfNumericFeatures":  "nnumer",
        "NumberOfSymbolicFeatures": "ncat",
        "NumberOfMissingValues":    "nmiss",
        "NumberOfClasses":          "nclass",
    }
    available_cols = {v: k for k, v in META_COLUMNS.items() if k in tasks_df.columns}

    if not available_cols:
        return OpenMLResult(
            success=False,
            message="OpenML task meta-features not available in API response.",
        )

    tasks_df = tasks_df.fillna(0)
    similarities: list[tuple[float, int, str]] = []

    for tid, row in tasks_df.iterrows():
        try:
            tvec = _build_vector(
                float(row.get("NumberOfInstances",       0)),
                float(row.get("NumberOfFeatures",        1)),
                float(row.get("NumberOfNumericFeatures", 0)),
                float(row.get("NumberOfSymbolicFeatures",0)),
                float(row.get("NumberOfMissingValues",   0)),
                float(row.get("NumberOfClasses",         0)),
                is_reg,
            )
            sim  = _cosine_similarity(query_vec, tvec)
            name = str(row.get("name", f"task_{tid}"))
            similarities.append((sim, int(tid), name))
        except Exception:
            continue

    if not similarities:
        return OpenMLResult(success=False, message="Could not compute task similarities.")

    similarities.sort(reverse=True)
    candidate_pool = similarities[:40]

    # ── Fetch evaluations from candidate pool ─────────────────────────────
    metric = "predictive_accuracy" if not is_reg else "root_mean_squared_error"
    aggregated: dict[str, list[float]] = {}
    working_datasets: list[str] = []
    working_tids: list[int] = []

    for sim, tid, name in candidate_pool:
        if len(working_tids) >= top_k:
            break
        try:
            evals_df = openml.evaluations.list_evaluations(
                function=metric,
                tasks=[tid],
                output_format="dataframe",
                size=50,
            )
            if evals_df is None or evals_df.empty:
                continue

            flow_col  = "flow_name" if "flow_name" in evals_df.columns else None
            score_col = "value"     if "value"     in evals_df.columns else None
            if not flow_col or not score_col:
                continue

            task_mapped = False
            for _, row in evals_df.iterrows():
                raw_flow = str(row.get(flow_col, ""))
                score    = float(row.get(score_col, 0) or 0)
                if score <= 0 or np.isnan(score):
                    continue
                internal = _map_flow(raw_flow)
                if not internal:
                    continue
                # For RMSE: invert so lower RMSE -> higher score
                if is_reg:
                    score = 1.0 / (1.0 + score)
                aggregated.setdefault(internal, []).append(score)
                task_mapped = True

            if task_mapped:
                working_tids.append(tid)
                working_datasets.append(name)

        except Exception:
            continue

    if not aggregated:
        top_names = [t[2] for t in similarities[:top_k]]
        return OpenMLResult(
            success=False,
            message="No usable algorithm evaluation data found in similar tasks.",
            similar_datasets=top_names,
            num_similar_found=0,
        )

    # ── Normalise to 0-100 ────────────────────────────────────────────────
    mean_scores = {alg: float(np.mean(vals)) for alg, vals in aggregated.items()}
    max_s, min_s = max(mean_scores.values()), min(mean_scores.values())
    span         = (max_s - min_s) or 1.0

    recommendations = []
    for alg, raw_score in sorted(mean_scores.items(), key=lambda x: x[1], reverse=True):
        norm = ((raw_score - min_s) / span) * 100.0
        n    = len(aggregated[alg])
        recommendations.append(OpenMLRecommendation(
            algorithm_name         = alg,
            openml_score           = round(norm, 1),
            similar_datasets_found = len(working_tids),
            reasoning              = (
                f"Evaluated in {n} run(s) across {len(working_tids)} similar OpenML tasks "
                f"(mean performance: {raw_score:.4f})"
            ),
        ))

    return OpenMLResult(
        recommendations   = recommendations,
        similar_datasets  = working_datasets,
        num_similar_found = len(working_tids),
        success           = True,
        message           = f"OpenML: {len(working_tids)} similar tasks with verified evaluations found, {len(recommendations)} algorithms ranked.",
    )
