"""Real Data Agent wrapper: runs AutonomousDataAgent and returns a compact summary
that the orchestrator, the dashboard and the later agents can use."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "data_agent") not in sys.path:
    sys.path.insert(0, str(ROOT / "data_agent"))

from agentflow_data_agent.core.agent import AutonomousDataAgent  # noqa: E402

ARTIFACT_DIR = ROOT / "backend" / "storage" / "processed"


def _preprocessing_lines(report, missing_total):
    h = report.health_metrics
    p = report.preprocessing_summary
    lk = report.leakage_report
    lines = []
    if h.duplicate_rows_removed:
        lines.append(f"Removed {h.duplicate_rows_removed} duplicate rows")
    dropped = list(h.constant_cols_removed) + list(h.id_cols_removed)
    if dropped:
        lines.append("Dropped constant/ID columns: " + ", ".join(dropped))
    if lk.suspicious_leaky_features_flagged:
        lines.append("Removed leaky features: " + ", ".join(lk.suspicious_leaky_features_flagged))
    if missing_total:
        lines.append("Imputed missing values")
    if p.encoding_methods:
        lines.append("Encoded categorical features")
    lines.append(f"Scaled numeric features ({p.scaling_method})")
    if p.datetime_columns_expanded:
        lines.append("Expanded date columns into calendar features")
    if p.skewed_features_transformed:
        lines.append(f"Reduced skew in {len(p.skewed_features_transformed)} features")
    if p.feature_selection_applied:
        lines.append(f"Selected {p.features_count_final} of {p.features_count_after_expansion} features")
    if p.smote_applied:
        lines.append(f"Balanced training classes with SMOTE (+{p.smote_synthetic_samples_added} rows)")
    lines.append(f"Split train/test before fitting ({lk.train_rows}/{lk.test_rows} rows)")
    return lines


def real_data_agent(dataset_path, target_column, problem_statement=""):
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(dataset_path).stem)[:60] or "dataset"
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    agent = AutonomousDataAgent(output_dir=str(ARTIFACT_DIR))
    report = agent.run(
        file_path=dataset_path,
        project_id=stem,
        target_column=target_column,
        problem_statement=problem_statement,
    )

    t = report.target_report
    h = report.health_metrics
    leaky = set(report.leakage_report.suspicious_leaky_features_flagged)
    feats = [c for c in report.column_profiles
             if c.name != t.selected_target and c.name not in leaky
             and not c.action_taken.startswith("dropped")]
    numeric = sum(1 for c in feats
                  if c.inferred_semantic_type in ("continuous_numeric", "categorical_numeric"))
    missing_total = sum(c.missing_count for c in report.column_profiles)

    return {
        "is_mock": False,
        "dataset_path": str(dataset_path),
        "target_column": t.selected_target,
        "problem_type": "regression" if t.inferred_problem_type == "regression" else "classification",
        "problem_subtype": t.inferred_problem_type,
        "rows": h.total_rows_raw,
        "columns": h.total_cols_raw,
        "missing_values": missing_total,
        "duplicates": h.duplicate_rows_removed,
        "numerical_features": numeric,
        "categorical_features": len(feats) - numeric,
        "preprocessing": _preprocessing_lines(report, missing_total),
        "health_score": h.overall_health_score,
        "health_grade": h.health_grade,
        "train_rows": report.leakage_report.train_rows,
        "test_rows": report.leakage_report.test_rows,
        "final_feature_count": report.preprocessing_summary.features_count_final,
        # list form (not a dict) so class labels like "1.0" are never used as Mongo keys
        "class_distribution": [{"label": k, "count": v}
                               for k, v in (t.class_distribution or {}).items()],
        "artifacts": {
            "train": report.artifact_paths.processed_train_path,
            "test": report.artifact_paths.processed_test_path,
            "pipeline": report.artifact_paths.pipeline_pickle_path,
            "report": report.artifact_paths.report_json_path,
        },
    }