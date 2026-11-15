"""
target_detector.py
------------------
Automatic target-column detection for AgentFlow. Runs BEFORE the Data Agent.

  1. profile every column (pandas)
  2. score candidates with rules (name, values, problem statement, position)
  3. (later) an LLM can re-rank the shortlist
  4. validate the choice with plain Python

No agent imports: pure pandas / numpy so it is easy to test.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

MIN_ROWS = 30
MAX_ROWS_PROFILED = 20000

STOPWORDS = {
    "a", "an", "the", "of", "to", "in", "on", "for", "and", "or", "is", "are", "will", "be",
    "whether", "if", "based", "using", "from", "with", "by", "that", "this", "it", "its",
    "their", "they", "them", "as", "at", "into", "can", "do", "does", "which", "what", "how",
    "predict", "prediction", "classify", "classification", "estimate", "forecast",
    "determine", "identify", "detect", "given", "model", "data", "dataset", "each", "per",
    "should", "would", "could", "use",
}


def _stem(w: str) -> str:
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def _tokens(text) -> list[str]:
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(text))   # split camelCase
    words = re.findall(r"[A-Za-z0-9]+", text.lower())
    return [_stem(w) for w in words if w not in STOPWORDS]


HIGH_PRIORITY = {_stem(w) for w in [
    "target", "label", "class", "outcome", "y", "churn", "fraud", "default", "survived",
    "diagnosis", "status", "exited", "attrition", "stroke", "diabetes", "cancer",
    "readmitted", "approved", "spam", "converted", "failure", "response", "subscribed",
]}
MEDIUM_PRIORITY = {_stem(w) for w in [
    "price", "sales", "revenue", "income", "salary", "cost", "charges", "amount", "profit",
    "score", "rating", "demand", "return", "grade", "quality", "risk", "value", "fare",
    "duration", "tenure", "count", "total",
]}
# words people write in a problem statement -> the column name they usually mean
SYNONYMS = {
    "leave": ["churn"], "left": ["churn"], "cancel": ["churn"], "quit": ["churn"],
    "survive": ["survived"], "subscribe": ["subscribed"], "fraudulent": ["fraud"],
    "approve": ["approved"], "diagnose": ["diagnosis"],
}

DATE_RE = re.compile(r"^\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})")
ID_NAME_RE = re.compile(r"(^|[_\s-])(id|uuid|guid|index|idx)([_\s-]|$)", re.I)
EXCLUDED_KINDS = {"empty", "constant", "identifier", "datetime", "text"}


# ----------------------------------------------------------------- loading
def load_dataset_frame(path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8", low_memory=False)
    df.columns = [str(c).strip() for c in df.columns]
    return df


# --------------------------------------------------------- column analysis
def _kind(s: pd.Series, name: str) -> str:
    nn = s.dropna()
    if len(nn) == 0:
        return "empty"
    nu = int(nn.nunique())
    if nu <= 1:
        return "constant"
    ratio = nu / len(nn)
    is_num = pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s)
    id_name = bool(ID_NAME_RE.search(name)) or bool(re.search(r"[a-z0-9]ID$", name))
    if id_name and ratio > 0.5:
        return "identifier"
    if is_num:
        if pd.api.types.is_integer_dtype(s) and ratio >= 0.98 and len(nn) >= 50:
            diffs = nn.sort_values().diff().dropna()
            if len(diffs) and float((diffs == 1).mean()) > 0.95:
                return "identifier"
        return "numeric"
    sample = nn.astype(str).head(200)
    if float(sample.str.match(DATE_RE).mean()) >= 0.8 or "date" in name.lower() \
            or "timestamp" in name.lower():
        return "datetime"
    avg_words = float(sample.str.split().str.len().mean())
    avg_chars = float(sample.str.len().mean())
    if avg_words >= 6 or avg_chars >= 45:
        return "text"
    if ratio > 0.9 and len(nn) >= 30:
        return "identifier"
    return "categorical"


def infer_problem_type(s: pd.Series) -> str:
    nn = s.dropna()
    nu = int(nn.nunique())
    if nu <= 2:
        return "binary_classification"
    if not pd.api.types.is_numeric_dtype(nn):
        return "multiclass_classification"
    is_int = pd.api.types.is_integer_dtype(nn) or bool((nn % 1 == 0).all())
    if is_int and nu <= min(20, max(3, int(len(nn) * 0.05))):
        return "multiclass_classification"
    return "regression"


def _leaky_columns(df: pd.DataFrame, column: str, threshold: float = 0.95) -> list[str]:
    y = df[column]
    if pd.api.types.is_numeric_dtype(y) and not pd.api.types.is_bool_dtype(y):
        y_num = y.astype(float)
    elif y.dropna().nunique() == 2:
        y_num = pd.Series(pd.factorize(y)[0], index=y.index).astype(float)
        y_num[y.isna()] = np.nan
    else:
        return []
    num = df.drop(columns=[column]).select_dtypes(include=[np.number])
    if num.shape[1] == 0 or y_num.nunique() < 2:
        return []
    with np.errstate(all="ignore"):
        corr = num.corrwith(y_num).abs()
    hits = corr[corr >= threshold].sort_values(ascending=False)
    return [str(c) for c in hits.index[:5]]


# -------------------------------------------------------------- validation
def validate_target(df: pd.DataFrame, column: str) -> dict:
    """Plain-Python safety checks. 'problems' block the run, 'warnings' don't."""
    if column not in df.columns:
        return {"valid": False, "problems": [f"Column '{column}' does not exist in the dataset."],
                "warnings": [], "problem_type": None}
    problems: list[str] = []
    warnings: list[str] = []
    s = df[column]
    n = len(df)
    nn = s.dropna()
    missing_pct = round(100.0 * (n - len(nn)) / max(n, 1), 2)
    kind = _kind(s, column)
    ptype = infer_problem_type(nn) if len(nn) else None

    if len(nn) < MIN_ROWS:
        problems.append(f"Only {len(nn)} rows have a value for '{column}' (need at least {MIN_ROWS}).")
    if missing_pct > 50:
        problems.append(f"'{column}' is missing in {missing_pct}% of rows.")
    elif missing_pct > 0:
        warnings.append(f"{missing_pct}% of rows have no value for '{column}'; they will be dropped.")
    reason_by_kind = {
        "constant": "has only one distinct value, so there is nothing to predict",
        "identifier": "looks like an identifier (unique per row)",
        "datetime": "looks like a date column",
        "text": "contains free text",
        "empty": "is empty",
    }
    if kind in reason_by_kind:
        problems.append(f"'{column}' {reason_by_kind[kind]}.")

    if ptype and "classification" in ptype and kind not in reason_by_kind:
        counts = nn.astype(str).value_counts()
        if kind != "numeric" and len(counts) > 30:
            problems.append(f"'{column}' has {len(counts)} distinct text values: too many to be classes.")
        elif int(counts.min()) < 2:
            rare = str(counts.idxmin())
            problems.append(f"Class '{rare}' has only 1 example; every class needs at least 2.")
        else:
            if int(counts.min()) < 10:
                warnings.append(f"Smallest class has only {int(counts.min())} examples; results may be unstable.")
            if len(counts) >= 2 and counts.max() / counts.min() >= 4:
                warnings.append("Classes are imbalanced; AgentFlow will account for this.")
    if n < 100:
        warnings.append("Very small dataset (under 100 rows); results will be rough.")

    leaks = _leaky_columns(df, column)
    if leaks:
        warnings.append("These columns are almost identical to the target and may leak the "
                        f"answer: {', '.join(leaks)}.")
    return {"valid": not problems, "problems": problems, "warnings": warnings,
            "problem_type": ptype, "missing_pct": missing_pct}


# --------------------------------------------------------------- detection
def _confidence(top: float, margin: float) -> float:
    c = 0.25 + 0.5 * min(top, 70.0) / 70.0 + 0.25 * min(max(margin, 0.0), 30.0) / 30.0
    return round(min(0.97, max(0.2, c)), 2)


def detect_target(df: pd.DataFrame, problem_statement: str = "") -> dict:
    if len(df) > MAX_ROWS_PROFILED:
        df = df.sample(MAX_ROWS_PROFILED, random_state=0).reset_index(drop=True)

    stmt = (problem_statement or "").strip()
    stmt_lower = stmt.lower()
    stmt_tokens = set(_tokens(stmt))
    for t in list(stmt_tokens):
        stmt_tokens.update(_stem(x) for x in SYNONYMS.get(t, []))

    n, ncols = len(df), len(df.columns)
    profile: list[dict] = []
    scored: list[tuple] = []          # (score, idx, column, reasons)

    for idx, col in enumerate(df.columns):
        s = df[col]
        nn = s.dropna()
        nu = int(nn.nunique()) if len(nn) else 0
        missing_pct = round(100.0 * (n - len(nn)) / max(n, 1), 2)
        kind = _kind(s, str(col))

        note = ""
        if kind in EXCLUDED_KINDS:
            note = f"not usable as a target ({kind})"
        elif missing_pct > 50:
            note = "too many missing values"
        elif kind != "numeric" and nu > 30:
            note = "too many distinct text values"

        profile.append({
            "name": str(col), "dtype": str(s.dtype), "kind": kind, "unique": nu,
            "missing_pct": missing_pct, "usable": not note, "note": note,
            "samples": [str(v)[:30] for v in nn.astype(str).unique()[:3]],
        })
        if note:
            continue

        score, reasons = 0.0, []

        # 1) the column name appears in the problem statement
        ctoks = set(_tokens(col))
        overlap = ctoks & stmt_tokens
        if ctoks and overlap:
            score += 30.0 * len(overlap) / len(ctoks)
            reasons.append(f"its name matches the problem statement ({', '.join(sorted(overlap))})")

        # 2) the column's VALUES appear in the problem statement
        if kind == "categorical" and nu <= 30 and stmt_lower:
            vals = [str(v) for v in nn.astype(str).unique() if len(str(v)) >= 3]
            hit = [v for v in vals if re.search(rf"\b{re.escape(v.lower())}\b", stmt_lower)]
            if len(hit) >= 2:
                score += 40.0 * len(hit) / nu
                reasons.append(f"its values ({', '.join(hit[:4])}) are mentioned in the problem statement")
            elif len(hit) == 1:
                score += 10.0
                reasons.append(f"its value '{hit[0]}' is mentioned in the problem statement")

        # 3) the name looks like a typical outcome
        if ctoks & HIGH_PRIORITY:
            score += 25.0
            reasons.append("its name looks like a typical outcome column")
        elif ctoks & MEDIUM_PRIORITY:
            score += 12.0
            reasons.append("its name looks like a measurable quantity worth predicting")

        # 4) position and shape
        if idx == ncols - 1:
            score += 10.0
            reasons.append("it is the last column (targets usually are)")
        elif idx == ncols - 2:
            score += 3.0
        if 2 <= nu <= 20:
            score += 8.0
        elif kind == "numeric" and nu > 20:
            score += 5.0

        scored.append((round(score, 1), idx, str(col), reasons))

    scored.sort(key=lambda r: (-r[0], -r[1]))     # ties: later column wins

    base = {"source": "rules", "columns": profile}
    if not scored:
        return {**base, "recommended": None, "confidence": 0.0, "ambiguous": True,
                "reason": "No column in this file looks usable as a prediction target.",
                "problem_type": None, "alternatives": [], "validation": None}

    top_score, _, top_col, top_reasons = scored[0]
    margin = top_score - (scored[1][0] if len(scored) > 1 else 0.0)
    conf = _confidence(top_score, margin)
    ptype = infer_problem_type(df[top_col])
    reason = (f"'{top_col}' was recommended because " + "; ".join(top_reasons[:3]) + "."
              if top_reasons else f"'{top_col}' was the most suitable remaining column.")

    alts = [{"column": c, "score": sc, "problem_type": infer_problem_type(df[c]),
             "reason": "; ".join(r[:2]) or "possible candidate"}
            for sc, _, c, r in scored[1:5] if sc > 0]

    return {**base, "recommended": top_col, "confidence": conf,
            "ambiguous": bool(margin < 8 or conf < 0.55), "reason": reason,
            "problem_type": ptype, "alternatives": alts,
            "validation": validate_target(df, top_col)}