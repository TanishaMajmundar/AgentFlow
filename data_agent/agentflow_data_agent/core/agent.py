import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import joblib
except ImportError:
    import pickle as joblib

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    LabelEncoder,
    OneHotEncoder,
    RobustScaler,
    StandardScaler,
)

from agentflow_data_agent.core.handoff_schemas import (
    ArtifactPaths,
    DataAgentReport,
    DataDriftMetrics,
    FeatureDriftReport,
    HyperparameterSearchHint,
    LeakagePreventionReport,
    PreprocessingSummary,
    StrategyHandoffPayload,
    TargetSelectionReport,
)
from agentflow_data_agent.pipelines.smote import NativeSMOTE
from agentflow_data_agent.pipelines.transformers import (
    AtlanticFeatureSelector,
    AutomatedFeatureEnricher,
    CollinearityPruner,
    DateTimeFeatureExtractor,
    FastSubsampledKNNImputer,
    NLPTextVectorizer,
    RareCategoryGrouper,
    ResilientTargetEncoder,
    SkewnessPowerTransformer,
    UniversalTypeCleaner,
)
from agentflow_data_agent.pipelines.wrapper import AgentFlowPipeline
from agentflow_data_agent.utils.io_handlers import load_dataset, optimize_memory
from agentflow_data_agent.utils.profilers import (
    discover_target,
    infer_semantic_type,
    profile_and_clean,
)


class AutonomousDataAgent:
    """
    Enterprise Autonomous Data Agent for AgentFlow AutoML.
    Orchestrates universal dataset ingestion, autonomous target discovery,
    comprehensive health profiling, leakage-free multi-modal feature engineering,
    and structured intelligence handoff.
    """

    def __init__(
        self,
        output_dir: str = "./artifacts/data_agent",
        test_size: float = 0.20,
        max_features_cap: int = 80,
        enable_smote: bool = True,
        enable_pca: bool = False,
        pca_variance_threshold: float = 0.96,
        random_state: int = 42,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.test_size = test_size
        self.max_features_cap = max_features_cap
        self.enable_smote = enable_smote
        self.enable_pca = enable_pca
        self.pca_variance_threshold = pca_variance_threshold
        self.random_state = random_state

        self.fitted_pipeline_: Optional[AgentFlowPipeline] = None
        self.target_encoder_label_: Optional[LabelEncoder] = None
        self.train_baseline_stats_: Dict[str, Any] = {}

    def _build_strategy_handoff(
        self,
        target_report: TargetSelectionReport,
        n_train_rows: int,
        n_final_features: int,
        smote_applied: bool,
    ) -> StrategyHandoffPayload:
        ptype = target_report.inferred_problem_type
        is_imb = target_report.is_imbalanced
        imb_ratio = target_report.imbalance_ratio or 1.0

        if n_train_rows < 2500:
            scale = "small"
            cv_folds = 5
        elif n_train_rows < 30000:
            scale = "medium"
            cv_folds = 5
        else:
            scale = "large"
            cv_folds = 3

        notes: List[str] = []
        hints: List[HyperparameterSearchHint] = []

        if ptype == "binary_classification":
            primary_metric = "roc_auc" if not is_imb else "f1_weighted"
            secondary_metrics = ["f1", "precision", "recall", "accuracy", "log_loss"]
            cv_strategy = "StratifiedKFold"
            models = ["LightGBMClassifier", "XGBoostClassifier", "CatBoostClassifier", "RandomForestClassifier", "LogisticRegression"]

            if is_imb:
                notes.append(
                    f"Class imbalance detected (ratio={imb_ratio:.1f}:1). "
                    f"{'SMOTE balanced training split; test scale_pos_weight.' if smote_applied else f'Set scale_pos_weight={imb_ratio:.1f} on tree boosters.'}"
                )
            hints.append(HyperparameterSearchHint(
                model_name="LightGBMClassifier",
                suggested_params={"n_estimators": [100, 300], "learning_rate": [0.03, 0.1], "num_leaves": [31, 63]}
            ))
            hints.append(HyperparameterSearchHint(
                model_name="XGBoostClassifier",
                suggested_params={"n_estimators": [100, 250], "learning_rate": [0.03, 0.1], "max_depth": [4, 6, 8]}
            ))

        elif ptype == "multiclass_classification":
            primary_metric = "f1_macro" if is_imb else "f1_weighted"
            secondary_metrics = ["accuracy", "log_loss", "roc_auc_ovr"]
            cv_strategy = "StratifiedKFold"
            models = ["LightGBMClassifier", "CatBoostClassifier", "XGBoostClassifier", "RandomForestClassifier"]
            hints.append(HyperparameterSearchHint(
                model_name="CatBoostClassifier",
                suggested_params={"iterations": [200, 400], "learning_rate": [0.03, 0.08], "depth": [4, 6]}
            ))
        else:
            primary_metric = "rmse"
            secondary_metrics = ["mae", "r2", "mape"]
            cv_strategy = "KFold"
            models = ["LightGBMRegressor", "XGBoostRegressor", "CatBoostRegressor", "RandomForestRegressor", "Ridge"]
            if target_report.target_skewness and abs(target_report.target_skewness) > 1.2:
                notes.append(
                    f"Target is skewed ({target_report.target_skewness}). Evaluate TransformedTargetRegressor(func=np.log1p) or Huber loss."
                )
            hints.append(HyperparameterSearchHint(
                model_name="LightGBMRegressor",
                suggested_params={"n_estimators": [150, 300], "learning_rate": [0.03, 0.08], "subsample": [0.8, 1.0]}
            ))

        if n_final_features > 40:
            notes.append(f"High-dimensional feature space ({n_final_features} features); recommend colsample_bytree=0.7 and L2 regularization.")

        return StrategyHandoffPayload(
            confirmed_problem_type=ptype,
            target_column=target_report.selected_target,
            primary_evaluation_metric=primary_metric,
            secondary_evaluation_metrics=secondary_metrics,
            recommended_candidate_models=models,
            recommended_cv_strategy=cv_strategy,
            recommended_cv_folds=cv_folds,
            handle_class_weights=bool(is_imb and not smote_applied),
            suggested_class_weight_ratio=round(float(imb_ratio), 2) if is_imb else None,
            dataset_scale_category=scale,
            strategy_notes=notes,
            hyperparameter_hints=hints,
        )

    def run(
        self,
        file_path: Union[str, Path],
        project_id: str = "agentflow_run_001",
        target_column: Optional[str] = None,
        problem_statement: Optional[str] = None,
    ) -> DataAgentReport:
        t0 = time.time()
        dataset_name = Path(file_path).stem

        raw_df = load_dataset(file_path, output_dir=self.output_dir)
        df_opt, mem_metrics = optimize_memory(raw_df)

        type_cleaner = UniversalTypeCleaner(treat_unknown_as_missing=True)
        df_cleaned_types = type_cleaner.fit_transform(df_opt)
        disguised_cnt = type_cleaner.disguised_count_

        target_report = discover_target(
            df_cleaned_types, target_column=target_column, problem_statement=problem_statement
        )
        target_col = target_report.selected_target
        problem_type = target_report.inferred_problem_type

        df_clean, col_profiles, health_metrics, visual_payload = profile_and_clean(
            df_cleaned_types, target_col=target_col, disguised_count=disguised_cnt
        )

        X = df_clean.drop(columns=[target_col])
        y_raw = df_clean[target_col]
        features_before = X.shape[1]

        if problem_type in {"binary_classification", "multiclass_classification"}:
            self.target_encoder_label_ = LabelEncoder()
            y = pd.Series(self.target_encoder_label_.fit_transform(y_raw.astype(str)), name=target_col)
            min_class_count = y.value_counts().min()
            stratify_vec = y if min_class_count >= 2 else None
        else:
            self.target_encoder_label_ = None
            y = pd.to_numeric(y_raw, errors="coerce")
            valid_y = y.notna()
            X = X.loc[valid_y].reset_index(drop=True)
            y = y.loc[valid_y].reset_index(drop=True)
            stratify_vec = None

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=self.test_size,
            random_state=self.random_state,
            stratify=stratify_vec,
        )
        X_train = X_train.reset_index(drop=True)
        X_test = X_test.reset_index(drop=True)
        y_train = y_train.reset_index(drop=True)
        y_test = y_test.reset_index(drop=True)

        leaky_features: List[str] = []
        for col in X_train.select_dtypes(include=[np.number]).columns:
            corr_with_y = abs(X_train[col].corr(pd.Series(y_train)))
            if pd.notna(corr_with_y) and corr_with_y >= 0.992:
                leaky_features.append(col)
        if leaky_features:
            X_train = X_train.drop(columns=leaky_features)
            X_test = X_test.drop(columns=leaky_features)

        dt_cols = [c for c in X_train.columns if infer_semantic_type(X_train[c], c) == "datetime"]
        text_cols = [c for c in X_train.columns if infer_semantic_type(X_train[c], c) == "unstructured_text"]

        dt_extractor = DateTimeFeatureExtractor(datetime_cols=dt_cols)
        X_train = dt_extractor.fit_transform(X_train)
        X_test = dt_extractor.transform(X_test)

        nlp_extractor = NLPTextVectorizer(text_cols=text_cols, n_components=5)
        X_train = nlp_extractor.fit_transform(X_train)
        X_test = nlp_extractor.transform(X_test)

        enricher = AutomatedFeatureEnricher(max_interactions=5, clip_outliers=True)
        X_train = enricher.fit_transform(X_train)
        X_test = enricher.transform(X_test)

        skew_transformer = SkewnessPowerTransformer(skew_threshold=1.0)
        X_train = skew_transformer.fit_transform(X_train)
        X_test = skew_transformer.transform(X_test)

        collinearity_pruner = CollinearityPruner(threshold=0.98)
        X_train = collinearity_pruner.fit_transform(X_train)
        X_test = collinearity_pruner.transform(X_test)

        num_cols = X_train.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = [c for c in X_train.columns if c not in num_cols]
        low_card_cols = [c for c in cat_cols if X_train[c].nunique(dropna=True) <= 12]
        high_card_cols = [c for c in cat_cols if c not in low_card_cols]

        has_outliers = any((p.outlier_pct or 0.0) > 2.5 for p in col_profiles)
        scaler_name = "RobustScaler" if has_outliers else "StandardScaler"
        scaler_cls = RobustScaler if has_outliers else StandardScaler

        transformers = []
        encoding_summary: Dict[str, str] = {}

        if num_cols:
            num_pipe = Pipeline([
                ("imputer", FastSubsampledKNNImputer(n_neighbors=5, max_fit_samples=2500, add_indicators=True)),
                ("scaler", scaler_cls()),
            ])
            transformers.append(("num", num_pipe, num_cols))

        if low_card_cols:
            for c in low_card_cols:
                encoding_summary[c] = "RareGrouper + OneHotEncoder"
            low_cat_pipe = Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("rare_grouper", RareCategoryGrouper(min_freq=0.015)),
                ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False, drop="if_binary")),
            ])
            transformers.append(("low_cat", low_cat_pipe, low_card_cols))

        if high_card_cols:
            for c in high_card_cols:
                encoding_summary[c] = "ResilientTargetEncoder (Bayesian m-estimate)"
            high_cat_pipe = Pipeline([
                ("imputer", SimpleImputer(strategy="constant", fill_value="missing_category")),
                ("target_enc", ResilientTargetEncoder(m=10.0, task_type=problem_type, random_state=self.random_state)),
                ("scaler", StandardScaler()),
            ])
            transformers.append(("high_cat", high_cat_pipe, high_card_cols))

        col_transformer = ColumnTransformer(transformers=transformers, remainder="drop")
        X_train_mat = col_transformer.fit_transform(X_train, y_train.values)
        X_test_mat = col_transformer.transform(X_test)

        expected_cols_ct = num_cols + low_card_cols + high_card_cols

        expanded_feature_names: List[str] = []
        if num_cols:
            expanded_feature_names.extend(num_cols)
            imputer_step = col_transformer.named_transformers_["num"].named_steps["imputer"]
            if imputer_step.add_indicators and imputer_step.cols_with_missing_in_fit_:
                for idx in imputer_step.cols_with_missing_in_fit_:
                    if idx < len(num_cols):
                        expanded_feature_names.append(f"{num_cols[idx]}_is_missing")

        if low_card_cols:
            ohe_step = col_transformer.named_transformers_["low_cat"].named_steps["ohe"]
            expanded_feature_names.extend(ohe_step.get_feature_names_out(low_card_cols).tolist())

        if high_card_cols:
            te_step = col_transformer.named_transformers_["high_cat"].named_steps["target_enc"]
            expanded_feature_names.extend(te_step.get_feature_names_out(high_card_cols).tolist())

        if len(expanded_feature_names) != X_train_mat.shape[1]:
            expanded_feature_names = [f"f_{i}" for i in range(X_train_mat.shape[1])]

        features_after_expansion = X_train_mat.shape[1]

        selector = AtlanticFeatureSelector(
            problem_type=problem_type,
            max_features=self.max_features_cap,
            min_features_to_trigger=35,
        )
        X_train_sel = selector.fit_transform(X_train_mat, y_train.values)
        X_test_sel = selector.transform(X_test_mat)
        final_feature_names = selector.get_feature_names(expanded_feature_names)

        pca_applied = False
        pca_var_ratio = None
        pca_model = None
        if self.enable_pca and X_train_sel.shape[1] > 20:
            pca_model = PCA(n_components=self.pca_variance_threshold, svd_solver="full", random_state=self.random_state)
            X_train_sel = pca_model.fit_transform(X_train_sel)
            X_test_sel = pca_model.transform(X_test_sel)
            pca_applied = True
            pca_var_ratio = round(float(np.sum(pca_model.explained_variance_ratio_)), 4)
            final_feature_names = [f"pca_comp_{i}" for i in range(X_train_sel.shape[1])]

        smote_applied = False
        smote_added = 0
        y_train_final = y_train.values.copy()
        if (
            self.enable_smote
            and problem_type in {"binary_classification", "multiclass_classification"}
            and target_report.is_imbalanced
        ):
            smote = NativeSMOTE(random_state=self.random_state)
            X_train_sel, y_train_final = smote.fit_resample(X_train_sel, y_train_final)
            if smote.synthetic_added_ > 0:
                smote_applied = True
                smote_added = smote.synthetic_added_

        train_df_out = pd.DataFrame(X_train_sel, columns=final_feature_names)
        train_df_out[target_col] = y_train_final

        test_df_out = pd.DataFrame(X_test_sel, columns=final_feature_names)
        test_df_out[target_col] = y_test.values

        train_path = self.output_dir / f"{project_id}_train_processed.parquet"
        test_path = self.output_dir / f"{project_id}_test_processed.parquet"
        pipeline_path = self.output_dir / f"{project_id}_preprocessing_pipeline.pkl"
        report_path = self.output_dir / f"{project_id}_data_agent_report.json"

        try:
            train_df_out.to_parquet(train_path, index=False)
            test_df_out.to_parquet(test_path, index=False)
        except Exception:
            train_path = self.output_dir / f"{project_id}_train_processed.csv"
            test_path = self.output_dir / f"{project_id}_test_processed.csv"
            train_df_out.to_csv(train_path, index=False)
            test_df_out.to_csv(test_path, index=False)

        self.train_baseline_stats_ = {
            col: {
                "mean": float(train_df_out[col].mean()),
                "std": float(train_df_out[col].std()) if train_df_out[col].std() > 0 else 1.0,
                "quantiles": [float(q) for q in np.percentile(train_df_out[col], [10, 25, 50, 75, 90])]
            }
            for col in final_feature_names
        }

        pipeline_config = {
            "type_cleaner": type_cleaner,
            "dropped_cols": health_metrics.constant_cols_removed + health_metrics.id_cols_removed + leaky_features,
            "dt_extractor": dt_extractor,
            "nlp_extractor": nlp_extractor,
            "enricher": enricher,
            "skew_transformer": skew_transformer,
            "collinearity_pruner": collinearity_pruner,
            "expected_col_transformer_columns": expected_cols_ct,
            "col_transformer": col_transformer,
            "selector": selector,
            "pca_model": pca_model,
            "final_feature_names": final_feature_names,
            "target_col": target_col,
            "target_label_encoder": self.target_encoder_label_,
            "train_baseline_stats": self.train_baseline_stats_,
        }
        self.fitted_pipeline_ = AgentFlowPipeline(pipeline_config)
        joblib.dump(self.fitted_pipeline_, pipeline_path)

        leakage_report = LeakagePreventionReport(
            split_performed_before_fitting=True,
            stratified_split_used=stratify_vec is not None,
            train_rows=len(train_df_out),
            test_rows=len(test_df_out),
            suspicious_leaky_features_flagged=leaky_features,
            high_collinearity_dropped=collinearity_pruner.to_drop_,
            smote_applied_strictly_on_train=smote_applied,
        )

        prep_summary = PreprocessingSummary(
            numeric_imputation_method="FastSubsampledKNNImputer (k=5, distance-weighted, missingness indicators)",
            categorical_imputation_method="SimpleImputer (most_frequent / missing_category)",
            scaling_method=scaler_name,
            encoding_methods=encoding_summary,
            nlp_text_columns_extracted=text_cols,
            datetime_columns_expanded=dt_cols,
            engineered_interaction_features=enricher.generated_features_,
            engineered_group_features=[c for c in enricher.generated_features_ if "mean_by" in c],
            skewed_features_transformed=list(skew_transformer.transformers_.keys()),
            feature_selection_applied=selector.active_,
            features_count_before_preprocess=features_before,
            features_count_after_expansion=features_after_expansion,
            features_count_final=len(final_feature_names),
            smote_applied=smote_applied,
            smote_synthetic_samples_added=smote_added,
            pca_applied=pca_applied,
            pca_explained_variance_ratio=pca_var_ratio,
        )

        strategy_handoff = self._build_strategy_handoff(
            target_report=target_report,
            n_train_rows=len(train_df_out),
            n_final_features=len(final_feature_names),
            smote_applied=smote_applied,
        )

        artifacts = ArtifactPaths(
            processed_train_path=str(train_path.resolve()),
            processed_test_path=str(test_path.resolve()),
            pipeline_pickle_path=str(pipeline_path.resolve()),
            report_json_path=str(report_path.resolve()),
        )

        elapsed = round(time.time() - t0, 3)
        report = DataAgentReport(
            project_id=project_id,
            dataset_name=dataset_name,
            execution_time_seconds=elapsed,
            status="completed",
            memory_metrics=mem_metrics,
            health_metrics=health_metrics,
            target_report=target_report,
            visual_analytics=visual_payload,
            leakage_report=leakage_report,
            preprocessing_summary=prep_summary,
            strategy_handoff=strategy_handoff,
            artifact_paths=artifacts,
            column_profiles=col_profiles,
        )

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))

        return report

    def transform_unseen_data(
        self,
        df_new: pd.DataFrame,
        compute_drift: bool = False
    ) -> Union[pd.DataFrame, Tuple[pd.DataFrame, DataDriftMetrics]]:
        if self.fitted_pipeline_ is None:
            raise RuntimeError("Pipeline has not been fitted yet. Call `run()` or load a saved pipeline first.")

        transformed_df = self.fitted_pipeline_.transform(df_new)

        if not compute_drift or not self.train_baseline_stats_:
            return transformed_df

        drift_reports: List[FeatureDriftReport] = []
        psi_values: List[float] = []

        for col in transformed_df.columns:
            if col in self.train_baseline_stats_:
                base = self.train_baseline_stats_[col]
                quantiles = base["quantiles"]
                new_vals = transformed_df[col].values
                bins = [-np.inf] + quantiles + [np.inf]
                counts, _ = np.histogram(new_vals, bins=bins)
                actual_pct = (counts / max(len(new_vals), 1)) + 1e-5
                expected_pct = np.array([0.10, 0.15, 0.25, 0.25, 0.15, 0.10]) + 1e-5

                psi = float(np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct)))
                psi_values.append(psi)
                drift_detected = psi >= 0.25
                drift_reports.append(
                    FeatureDriftReport(
                        feature_name=col,
                        drift_score_psi=round(psi, 4),
                        drift_detected=drift_detected,
                    )
                )

        avg_psi = float(np.mean(psi_values)) if psi_values else 0.0
        drift_count = sum(1 for r in drift_reports if r.drift_detected)
        drift_metrics = DataDriftMetrics(
            drift_detected=drift_count > 0,
            average_psi=round(avg_psi, 4),
            features_drifted_count=drift_count,
            feature_drift_reports=drift_reports,
        )

        return transformed_df, drift_metrics
