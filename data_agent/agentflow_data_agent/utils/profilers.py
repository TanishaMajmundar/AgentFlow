import re
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from agentflow_data_agent.core.handoff_schemas import (
    ColumnProfile,
    CorrelationEntry,
    DatasetHealthMetrics,
    TargetCandidateScore,
    TargetSelectionReport,
    VisualAnalyticsPayload,
)

SEMANTIC_TARGET_KEYWORDS = {
    "high_priority": [
        "target", "label", "class", "outcome", "y", "churn", "fraud",
        "default", "survived", "diagnosis", "status", "is_fraud", "exited",
        "attrition", "stroke", "diabetes", "cancer", "readmitted", "claim",
        "approved", "loan_status", "credit_risk", "sentiment", "spam",
        "converted", "failure", "is_churn", "defaulter", "response"
    ],
    "medium_priority": [
        "price", "saleprice", "sales", "revenue", "income", "salary",
        "cost", "charges", "amount", "profit", "score", "rating",
        "demand", "cnt", "count", "total", "value", "median_house_value",
        "grade", "quality", "risk", "response", "subscribed", "deposit",
        "tenure", "duration", "trip_duration", "fare"
    ],
}

ID_PATTERNS = re.compile(
    r"^(id|.*_id|.*id|uuid|guid|index|row_id|record_id|customer_id|user_id|"
    r"patient_id|passengerid|transaction_id|order_id|ticket|name|full_name|"
    r"email|phone|ssn|account_number|vin|member_id)$",
    re.IGNORECASE,
)


def infer_semantic_type(s: pd.Series, col_name: str) -> str:
    n_total = len(s)
    non_null = s.dropna()
    if len(non_null) == 0:
        return "empty"

    n_unique = non_null.nunique()
    unique_ratio = n_unique / max(len(non_null), 1)

    if n_unique <= 1:
        return "constant"

    if ID_PATTERNS.match(col_name.strip()):
        if unique_ratio > 0.80:
            return "identifier"

    if pd.api.types.is_bool_dtype(s) or n_unique == 2:
        return "binary"

    if pd.api.types.is_numeric_dtype(s):
        if pd.api.types.is_integer_dtype(s) and unique_ratio >= 0.98 and n_total >= 50:
            diffs = non_null.sort_values().diff().dropna()
            if (diffs == 1).mean() > 0.95:
                return "identifier"
        if n_unique <= min(20, int(n_total * 0.05)):
            return "categorical_numeric"
        return "continuous_numeric"

    str_sample = non_null.astype(str).head(500)
    avg_words = str_sample.str.split().str.len().mean()
    avg_chars = str_sample.str.len().mean()

    if avg_words >= 6.0 or avg_chars >= 45.0:
        return "unstructured_text"

    if any(k in col_name.lower() for k in ["date", "time", "timestamp", "dt", "created", "updated"]):
        parsed_dt = pd.to_datetime(str_sample, errors="coerce")
        if parsed_dt.notna().mean() >= 0.75:
            return "datetime"
    elif 8 <= avg_chars <= 25 and n_unique > 15:
        parsed_dt = pd.to_datetime(str_sample, errors="coerce")
        if parsed_dt.notna().mean() >= 0.85:
            return "datetime"

    if unique_ratio >= 0.95 and n_total >= 50:
        return "identifier"

    if n_unique <= 15:
        return "low_cardinality_categorical"
    return "high_cardinality_categorical"


def infer_problem_type(y: pd.Series) -> str:
    non_null = y.dropna()
    n_unique = non_null.nunique()
    if n_unique <= 2:
        return "binary_classification"
    if not pd.api.types.is_numeric_dtype(non_null):
        return "multiclass_classification"
    if pd.api.types.is_integer_dtype(non_null) and n_unique <= min(20, max(3, int(len(non_null) * 0.05))):
        return "multiclass_classification"
    return "regression"


def discover_target(
    df: pd.DataFrame,
    target_column: Optional[str] = None,
    problem_statement: Optional[str] = None,
) -> TargetSelectionReport:
    cols = list(df.columns)
    n_rows = len(df)

    if target_column and target_column in df.columns:
        selected = target_column
        mode = "user_specified"
        confidence = 1.0
        candidates_list = []
        reasoning = f"Target column '{selected}' was explicitly provided by user/orchestrator."
    else:
        mode = "autonomous_ai_discovery"
        candidates_list = []
        prob_tokens = set(re.findall(r"\w+", (problem_statement or "").lower()))

        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        mean_abs_corr: Dict[str, float] = {}
        if len(num_cols) >= 2:
            corr_mat = df[num_cols].corr().abs().fillna(0.0)
            for nc in num_cols:
                mean_abs_corr[nc] = float((corr_mat[nc].sum() - 1.0) / max(len(num_cols) - 1, 1))

        for idx, col in enumerate(cols):
            s = df[col]
            non_null = s.dropna()
            missing_pct = (n_rows - len(non_null)) / max(n_rows, 1)
            n_unique = non_null.nunique()
            unique_ratio = n_unique / max(len(non_null), 1)
            clean_name = col.strip().lower()
            sem_type = infer_semantic_type(s, col)

            sem_score = 0.0
            if clean_name in SEMANTIC_TARGET_KEYWORDS["high_priority"]:
                sem_score = 45.0
            elif any(k in clean_name for k in SEMANTIC_TARGET_KEYWORDS["high_priority"]):
                sem_score = 36.0
            elif clean_name in SEMANTIC_TARGET_KEYWORDS["medium_priority"]:
                sem_score = 30.0
            elif any(k in clean_name for k in SEMANTIC_TARGET_KEYWORDS["medium_priority"]):
                sem_score = 22.0

            prob_score = 0.0
            if prob_tokens:
                col_tokens = set(re.findall(r"\w+", clean_name))
                overlap = col_tokens & prob_tokens
                if clean_name in (problem_statement or "").lower():
                    prob_score = 25.0
                elif overlap:
                    prob_score = 18.0

            if idx == len(cols) - 1:
                pos_score = 15.0
            elif idx == len(cols) - 2:
                pos_score = 6.0
            elif idx == 0 and sem_score > 0:
                pos_score = 5.0
            else:
                pos_score = 0.0

            entropy_score = 0.0
            if 2 <= n_unique <= 20:
                probs = non_null.value_counts(normalize=True).values
                entropy = -float(np.sum(probs * np.log2(probs + 1e-12)))
                if 0.2 <= entropy <= 4.0:
                    entropy_score = 10.0
            elif pd.api.types.is_numeric_dtype(s) and n_unique > 20:
                entropy_score = 8.0

            stat_score = min(5.0, mean_abs_corr.get(col, 0.0) * 12.0)

            penalty = 0.0
            reasons = []
            if sem_type in {"identifier", "datetime", "unstructured_text", "constant", "empty"}:
                penalty += 80.0
                reasons.append(f"Penalized ({sem_type})")
            if missing_pct > 0.35:
                penalty += 50.0
                reasons.append(f"High missingness ({missing_pct:.1%})")
            if not pd.api.types.is_numeric_dtype(s) and unique_ratio > 0.50 and n_unique > 30:
                penalty += 60.0
                reasons.append("Excessive non-numeric cardinality")

            total = max(0.0, sem_score + prob_score + pos_score + entropy_score + stat_score - penalty)
            inferred_task = infer_problem_type(s)
            if not reasons:
                reasons.append(
                    f"sem={sem_score:.0f}, prob={prob_score:.0f}, pos={pos_score:.0f}, task={inferred_task}"
                )

            candidates_list.append(
                TargetCandidateScore(
                    column_name=col,
                    total_score=round(total, 2),
                    semantic_name_score=round(sem_score, 2),
                    problem_statement_match_score=round(prob_score, 2),
                    positional_score=round(pos_score, 2),
                    entropy_dispersion_score=round(entropy_score, 2),
                    statistical_centrality_score=round(stat_score, 2),
                    penalty_score=round(penalty, 2),
                    inferred_task=inferred_task,
                    reasoning="; ".join(reasons),
                )
            )

        candidates_list.sort(key=lambda x: x.total_score, reverse=True)
        best = candidates_list[0]
        selected = best.column_name
        second_score = candidates_list[1].total_score if len(candidates_list) > 1 else 0.0
        margin = best.total_score - second_score
        confidence = round(min(0.99, max(0.55, (best.total_score / 85.0) + (margin / 100.0))), 2)
        reasoning = (
            f"Autonomously selected '{selected}' (score={best.total_score}/100, "
            f"margin=+{margin:.1f} over runner-up) based on {best.reasoning}."
        )

    target_series = df[selected].dropna()
    problem_type = infer_problem_type(target_series)

    class_dist = None
    imbalance_ratio = None
    is_imbalanced = False
    target_skew = None

    if problem_type in {"binary_classification", "multiclass_classification"}:
        vc = target_series.astype(str).value_counts()
        class_dist = {str(k): int(v) for k, v in vc.head(25).items()}
        if len(vc) >= 2 and vc.min() > 0:
            imbalance_ratio = round(float(vc.max() / vc.min()), 2)
            is_imbalanced = imbalance_ratio >= 2.0
    else:
        target_skew = round(float(pd.to_numeric(target_series, errors="coerce").skew()), 3)

    return TargetSelectionReport(
        selected_target=selected,
        selection_mode=mode,
        confidence_score=confidence,
        inferred_problem_type=problem_type,
        reasoning_summary=reasoning,
        target_missing_dropped=int(df[selected].isna().sum()),
        class_distribution=class_dist,
        imbalance_ratio=imbalance_ratio,
        is_imbalanced=is_imbalanced,
        target_skewness=target_skew,
        top_candidates=candidates_list[:5],
    )


def profile_and_clean(
    df: pd.DataFrame, target_col: str, disguised_count: int
) -> Tuple[pd.DataFrame, List[ColumnProfile], DatasetHealthMetrics, VisualAnalyticsPayload]:
    raw_rows, raw_cols = df.shape
    df_clean = df.copy()

    df_clean = df_clean[df_clean[target_col].notna()].reset_index(drop=True)

    dup_count = int(df_clean.duplicated().sum())
    if dup_count > 0:
        df_clean = df_clean.drop_duplicates().reset_index(drop=True)

    profiles: List[ColumnProfile] = []
    constant_cols: List[str] = []
    id_cols: List[str] = []
    outlier_ratios: List[float] = []
    missingness_summary: Dict[str, float] = {}
    outlier_summary: Dict[str, float] = {}
    feature_type_counts: Dict[str, int] = {}
    high_card_penalties: int = 0

    for col in df_clean.columns:
        s = df_clean[col]
        n_total = len(s)
        miss_cnt = int(s.isna().sum())
        miss_pct = round(miss_cnt / max(n_total, 1) * 100.0, 2)
        missingness_summary[col] = miss_pct
        uniq_cnt = int(s.dropna().nunique())
        uniq_pct = round(uniq_cnt / max(n_total - miss_cnt, 1) * 100.0, 2)
        sem_type = "target" if col == target_col else infer_semantic_type(s, col)
        feature_type_counts[sem_type] = feature_type_counts.get(sem_type, 0) + 1

        outlier_pct = None
        skew_val = None
        kurt_val = None
        mean_val = None
        std_val = None
        min_val = None
        max_val = None

        if pd.api.types.is_numeric_dtype(s) and uniq_cnt > 2:
            valid_num = s.dropna().astype(float)
            if len(valid_num) > 0:
                mean_val = round(float(valid_num.mean()), 4)
                std_val = round(float(valid_num.std()), 4)
                min_val = round(float(valid_num.min()), 4)
                max_val = round(float(valid_num.max()), 4)
                skew_val = round(float(valid_num.skew()), 3)
                kurt_val = round(float(valid_num.kurtosis()), 3)
                q1, q3 = np.percentile(valid_num, [25, 75])
                iqr = q3 - q1
                if iqr > 0:
                    out_cnt = int(((valid_num < (q1 - 1.5 * iqr)) | (valid_num > (q3 + 1.5 * iqr))).sum())
                    outlier_pct = round(out_cnt / len(valid_num) * 100.0, 2)
                    outlier_ratios.append(outlier_pct)
                    outlier_summary[col] = outlier_pct

        action = "retained"
        if col != target_col:
            if sem_type in {"constant", "empty"} or miss_pct >= 95.0:
                constant_cols.append(col)
                action = "dropped_constant_or_empty"
            elif sem_type == "identifier":
                id_cols.append(col)
                action = "dropped_identifier"
            elif sem_type == "high_cardinality_categorical":
                high_card_penalties += 1
                action = "target_encoded"
            elif sem_type == "unstructured_text":
                action = "tfidf_svd_vectorized"
            elif sem_type == "datetime":
                action = "cyclical_datetime_expanded"

        samples = [str(v) for v in s.dropna().unique()[:4]]
        profiles.append(
            ColumnProfile(
                name=col,
                raw_dtype=str(s.dtype),
                inferred_semantic_type=sem_type,
                missing_count=miss_cnt,
                missing_pct=miss_pct,
                unique_count=uniq_cnt,
                unique_pct=uniq_pct,
                outlier_pct=outlier_pct,
                skewness=skew_val,
                kurtosis=kurt_val,
                mean=mean_val,
                std=std_val,
                min_val=min_val,
                max_val=max_val,
                sample_values=samples,
                action_taken=action,
            )
        )

    drop_cols = constant_cols + id_cols
    if drop_cols:
        df_clean = df_clean.drop(columns=drop_cols, errors="ignore")

    total_cells = max(raw_rows * raw_cols, 1)
    total_missing = int(df.isna().sum().sum())
    completeness = max(0.0, 100.0 - (total_missing / total_cells * 100.0 * 1.5))
    uniqueness = max(0.0, 100.0 - (dup_count / max(raw_rows, 1) * 100.0 * 1.5))
    avg_outlier = float(np.mean(outlier_ratios)) if outlier_ratios else 0.0
    outlier_stability = max(0.0, 100.0 - min(40.0, avg_outlier * 2.0))
    cardinality_health = max(
        0.0,
        100.0 - ((len(id_cols) + len(constant_cols) + high_card_penalties * 0.5) / max(raw_cols, 1) * 100.0),
    )
    target_health = 100.0 - (int(df[target_col].isna().sum()) / max(raw_rows, 1) * 100.0 * 2.0)
    target_health = max(0.0, min(100.0, target_health))

    overall = (
        0.30 * completeness
        + 0.20 * uniqueness
        + 0.20 * outlier_stability
        + 0.15 * cardinality_health
        + 0.15 * target_health
    )

    if overall >= 90:
        grade = "A+"
    elif overall >= 80:
        grade = "A"
    elif overall >= 70:
        grade = "B"
    elif overall >= 55:
        grade = "C"
    elif overall >= 40:
        grade = "D"
    else:
        grade = "F"

    remediations: List[str] = []
    if disguised_count > 0:
        remediations.append(f"Normalized {disguised_count} disguised missing tokens into standard NaNs.")
    if dup_count > 0:
        remediations.append(f"Purged {dup_count} exact duplicate rows to prevent statistical bias.")
    if constant_cols:
        remediations.append(f"Dropped zero-variance constant columns: {', '.join(constant_cols)}.")
    if id_cols:
        remediations.append(f"Filtered non-informative unique identifier columns: {', '.join(id_cols)}.")
    if avg_outlier > 3.0:
        remediations.append(f"Detected {avg_outlier:.1f}% average outlier density; configured learned Winsorization.")

    health = DatasetHealthMetrics(
        overall_health_score=round(overall, 2),
        health_grade=grade,
        completeness_score=round(completeness, 2),
        uniqueness_score=round(uniqueness, 2),
        outlier_stability_score=round(outlier_stability, 2),
        cardinality_health_score=round(cardinality_health, 2),
        target_health_score=round(target_health, 2),
        total_rows_raw=raw_rows,
        total_cols_raw=raw_cols,
        duplicate_rows_removed=dup_count,
        constant_cols_removed=constant_cols,
        id_cols_removed=id_cols,
        disguised_missing_values_normalized=disguised_count,
        actionable_remediations=remediations,
    )

    top_corrs: List[CorrelationEntry] = []
    num_clean = df_clean.select_dtypes(include=[np.number])
    if num_clean.shape[1] >= 2:
        corr_mat = num_clean.corr().abs().fillna(0.0)
        seen_pairs = set()
        for c1 in corr_mat.columns:
            for c2 in corr_mat.columns:
                if c1 != c2 and (c2, c1) not in seen_pairs:
                    seen_pairs.add((c1, c2))
                    val = float(corr_mat.loc[c1, c2])
                    if val > 0.10:
                        top_corrs.append(CorrelationEntry(feature_a=c1, feature_b=c2, correlation=round(val, 3)))
        top_corrs.sort(key=lambda x: x.correlation, reverse=True)

    target_dist_chart = {}
    if target_col in df_clean.columns:
        vc = df_clean[target_col].astype(str).value_counts().head(20).to_dict()
        target_dist_chart = {str(k): int(v) for k, v in vc.items()}

    visual_payload = VisualAnalyticsPayload(
        top_correlations=top_corrs[:15],
        missingness_summary=missingness_summary,
        target_distribution_chart=target_dist_chart,
        outlier_summary=outlier_summary,
        feature_type_counts=feature_type_counts,
    )

    return df_clean, profiles, health, visual_payload
