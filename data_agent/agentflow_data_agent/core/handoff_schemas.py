from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MemoryMetrics(BaseModel):
    initial_memory_mb: float
    optimized_memory_mb: float
    memory_reduction_pct: float


class ColumnProfile(BaseModel):
    name: str
    raw_dtype: str
    inferred_semantic_type: str
    missing_count: int
    missing_pct: float
    unique_count: int
    unique_pct: float
    outlier_pct: Optional[float] = None
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    mean: Optional[float] = None
    std: Optional[float] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    sample_values: List[Any] = Field(default_factory=list)
    action_taken: str = "retained"


class TargetCandidateScore(BaseModel):
    column_name: str
    total_score: float
    semantic_name_score: float
    problem_statement_match_score: float
    positional_score: float
    entropy_dispersion_score: float
    statistical_centrality_score: float
    penalty_score: float
    inferred_task: str
    reasoning: str


class TargetSelectionReport(BaseModel):
    selected_target: str
    selection_mode: str  # "autonomous_ai_discovery" or "user_specified"
    confidence_score: float
    inferred_problem_type: str  # "binary_classification", "multiclass_classification", "regression"
    reasoning_summary: str
    target_missing_dropped: int
    class_distribution: Optional[Dict[str, int]] = None
    imbalance_ratio: Optional[float] = None
    is_imbalanced: bool = False
    target_skewness: Optional[float] = None
    top_candidates: List[TargetCandidateScore] = Field(default_factory=list)


class CorrelationEntry(BaseModel):
    feature_a: str
    feature_b: str
    correlation: float


class VisualAnalyticsPayload(BaseModel):
    """Rich visualization metadata precomputed for Dhyan's React Frontend."""
    top_correlations: List[CorrelationEntry] = Field(default_factory=list)
    missingness_summary: Dict[str, float] = Field(default_factory=dict)
    target_distribution_chart: Dict[str, int] = Field(default_factory=dict)
    outlier_summary: Dict[str, float] = Field(default_factory=dict)
    feature_type_counts: Dict[str, int] = Field(default_factory=dict)


class DatasetHealthMetrics(BaseModel):
    overall_health_score: float  # 0 to 100
    health_grade: str  # A+, A, B, C, D, F
    completeness_score: float
    uniqueness_score: float
    outlier_stability_score: float
    cardinality_health_score: float
    target_health_score: float
    total_rows_raw: int
    total_cols_raw: int
    duplicate_rows_removed: int
    constant_cols_removed: List[str]
    id_cols_removed: List[str]
    disguised_missing_values_normalized: int
    actionable_remediations: List[str] = Field(default_factory=list)


class LeakagePreventionReport(BaseModel):
    split_performed_before_fitting: bool = True
    stratified_split_used: bool
    train_rows: int
    test_rows: int
    suspicious_leaky_features_flagged: List[str] = Field(default_factory=list)
    high_collinearity_dropped: List[str] = Field(default_factory=list)
    smote_applied_strictly_on_train: bool = False


class PreprocessingSummary(BaseModel):
    numeric_imputation_method: str
    categorical_imputation_method: str
    scaling_method: str
    encoding_methods: Dict[str, str]
    nlp_text_columns_extracted: List[str]
    datetime_columns_expanded: List[str]
    engineered_interaction_features: List[str]
    engineered_group_features: List[str] = Field(default_factory=list)
    skewed_features_transformed: List[str]
    feature_selection_applied: bool
    features_count_before_preprocess: int
    features_count_after_expansion: int
    features_count_final: int
    smote_applied: bool
    smote_synthetic_samples_added: int
    pca_applied: bool
    pca_explained_variance_ratio: Optional[float] = None


class HyperparameterSearchHint(BaseModel):
    model_name: str
    suggested_params: Dict[str, List[Any]]


class StrategyHandoffPayload(BaseModel):
    """Direct intelligence handoff for Riaan's ML Strategy Agent & Tanisha's Orchestrator."""
    confirmed_problem_type: str
    target_column: str
    primary_evaluation_metric: str
    secondary_evaluation_metrics: List[str]
    recommended_candidate_models: List[str]
    recommended_cv_strategy: str
    recommended_cv_folds: int
    handle_class_weights: bool
    suggested_class_weight_ratio: Optional[float] = None
    dataset_scale_category: str  # "small", "medium", "large"
    strategy_notes: List[str]
    hyperparameter_hints: List[HyperparameterSearchHint] = Field(default_factory=list)


class FeatureDriftReport(BaseModel):
    feature_name: str
    drift_score_psi: float
    drift_detected: bool
    metric_used: str = "PSI"


class DataDriftMetrics(BaseModel):
    drift_detected: bool
    average_psi: float
    features_drifted_count: int
    feature_drift_reports: List[FeatureDriftReport] = Field(default_factory=list)


class ArtifactPaths(BaseModel):
    processed_train_path: str
    processed_test_path: str
    pipeline_pickle_path: str
    report_json_path: str


class DataAgentReport(BaseModel):
    project_id: str
    dataset_name: str
    execution_time_seconds: float
    status: str = "completed"
    memory_metrics: MemoryMetrics
    health_metrics: DatasetHealthMetrics
    target_report: TargetSelectionReport
    visual_analytics: VisualAnalyticsPayload
    leakage_report: LeakagePreventionReport
    preprocessing_summary: PreprocessingSummary
    strategy_handoff: StrategyHandoffPayload
    artifact_paths: ArtifactPaths
    column_profiles: List[ColumnProfile]
