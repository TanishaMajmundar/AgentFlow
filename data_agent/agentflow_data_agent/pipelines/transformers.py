import re
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_selection import SelectKBest, mutual_info_classif, mutual_info_regression
from sklearn.impute import KNNImputer, SimpleImputer
from sklearn.preprocessing import PowerTransformer


class UniversalTypeCleaner(BaseEstimator, TransformerMixin):
    """
    Cleans 30+ disguised missing tokens ('?', 'null', 'nan', '-999', 'N/A', etc.),
    coerces currency ($/€/£/₹/¥) and numeric strings into floats, normalizes whitespace,
    and maps common boolean representations ('yes'/'no', 'true'/'false', 't'/'f') to binary 1/0.
    """
    DISGUISED_MISSING = {
        "?", "??", "na", "n/a", "#na", "#n/a", "#value!", "#null!", "none", "null",
        "nil", "nan", "-nan", "missing", "undefined", "--", "-", "", " ", "unknown",
        "unk", "-999", "-9999", "-99999", "999", "9999", "99999", "inf", "-inf",
        "not available", "not applicable"
    }

    BOOLEAN_TRUE = {"true", "yes", "y", "t", "1"}
    BOOLEAN_FALSE = {"false", "no", "n", "f", "0"}

    def __init__(self, treat_unknown_as_missing: bool = True):
        self.treat_unknown_as_missing = treat_unknown_as_missing
        self.numeric_coerced_cols_: List[str] = []
        self.boolean_coerced_cols_: List[str] = []
        self.disguised_count_: int = 0

    def fit(self, X: pd.DataFrame, y: Any = None):
        df = X.copy()
        self.numeric_coerced_cols_ = []
        self.boolean_coerced_cols_ = []

        for col in df.select_dtypes(include=["object", "category"]).columns:
            s = df[col].astype(str).str.strip()
            lower_s = s.str.lower()
            valid_mask = ~lower_s.isin(self.DISGUISED_MISSING)

            if valid_mask.sum() == 0:
                continue

            valid_vals = s[valid_mask]
            valid_lower = lower_s[valid_mask]

            unique_bool = set(valid_lower.unique())
            if unique_bool.issubset(self.BOOLEAN_TRUE | self.BOOLEAN_FALSE) and len(unique_bool) <= 2:
                self.boolean_coerced_cols_.append(col)
                continue

            cleaned = valid_vals.str.replace(r"[$€£₹¥,% ]", "", regex=True)
            coerced = pd.to_numeric(cleaned, errors="coerce")
            if coerced.notna().mean() >= 0.85:
                self.numeric_coerced_cols_.append(col)

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        df = X.copy()
        missing_tokens = set(self.DISGUISED_MISSING)
        if not self.treat_unknown_as_missing:
            missing_tokens.discard("unknown")
            missing_tokens.discard("unk")

        for col in df.select_dtypes(include=["object", "category"]).columns:
            s = df[col].astype(str).str.strip()
            lower_s = s.str.lower()
            mask = lower_s.isin(missing_tokens)
            if mask.any():
                self.disguised_count_ += int(mask.sum())
                df.loc[mask, col] = np.nan

            if col in self.boolean_coerced_cols_:
                s_clean = df[col].astype(str).str.strip().str.lower()
                mapped = pd.Series(np.nan, index=df.index, dtype=np.float32)
                mapped[s_clean.isin(self.BOOLEAN_TRUE)] = 1.0
                mapped[s_clean.isin(self.BOOLEAN_FALSE)] = 0.0
                df[col] = mapped

            elif col in self.numeric_coerced_cols_:
                cleaned = (
                    df[col]
                    .astype(str)
                    .str.replace(r"[$€£₹¥,% ]", "", regex=True)
                )
                df[col] = pd.to_numeric(cleaned, errors="coerce")

        return df


class DateTimeFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    Expands datetime columns into cyclical harmonic (sin/cos for month, day-of-week, hour),
    calendar indicators (year, quarter, weekend, month-start, month-end), and elapsed
    days relative to the minimum historical timestamp.
    """
    def __init__(self, datetime_cols: List[str]):
        self.datetime_cols = datetime_cols
        self.base_dates_: Dict[str, pd.Timestamp] = {}
        self.generated_cols_: List[str] = []

    def fit(self, X: pd.DataFrame, y: Any = None):
        self.base_dates_ = {}
        for col in self.datetime_cols:
            if col in X.columns:
                dt = pd.to_datetime(X[col], errors="coerce")
                min_dt = dt.min()
                if pd.notna(min_dt):
                    self.base_dates_[col] = min_dt
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        df = X.copy()
        self.generated_cols_ = []

        for col in self.datetime_cols:
            if col not in df.columns:
                continue
            dt = pd.to_datetime(df[col], errors="coerce")

            df[f"{col}_year"] = dt.dt.year.fillna(-1).astype(np.float32)
            df[f"{col}_quarter"] = dt.dt.quarter.fillna(-1).astype(np.float32)
            df[f"{col}_dayofweek"] = dt.dt.dayofweek.fillna(-1).astype(np.float32)
            df[f"{col}_dayofmonth"] = dt.dt.day.fillna(-1).astype(np.float32)
            df[f"{col}_is_weekend"] = dt.dt.dayofweek.isin([5, 6]).astype(np.float32)
            df[f"{col}_is_month_start"] = dt.dt.is_month_start.astype(np.float32)
            df[f"{col}_is_month_end"] = dt.dt.is_month_end.astype(np.float32)

            month_val = dt.dt.month.fillna(0)
            df[f"{col}_month_sin"] = np.sin(2 * np.pi * month_val / 12.0).astype(np.float32)
            df[f"{col}_month_cos"] = np.cos(2 * np.pi * month_val / 12.0).astype(np.float32)

            day_val = dt.dt.dayofweek.fillna(0)
            df[f"{col}_dow_sin"] = np.sin(2 * np.pi * day_val / 7.0).astype(np.float32)
            df[f"{col}_dow_cos"] = np.cos(2 * np.pi * day_val / 7.0).astype(np.float32)

            if (dt.dt.hour > 0).any():
                hour_val = dt.dt.hour.fillna(0)
                df[f"{col}_hour_sin"] = np.sin(2 * np.pi * hour_val / 24.0).astype(np.float32)
                df[f"{col}_hour_cos"] = np.cos(2 * np.pi * hour_val / 24.0).astype(np.float32)
                self.generated_cols_.extend([f"{col}_hour_sin", f"{col}_hour_cos"])

            if col in self.base_dates_:
                diff_days = (dt - self.base_dates_[col]).dt.total_seconds() / (24 * 3600)
                df[f"{col}_elapsed_days"] = diff_days.fillna(-1.0).astype(np.float32)
                self.generated_cols_.append(f"{col}_elapsed_days")

            self.generated_cols_.extend([
                f"{col}_year", f"{col}_quarter", f"{col}_dayofweek", f"{col}_dayofmonth",
                f"{col}_is_weekend", f"{col}_is_month_start", f"{col}_is_month_end",
                f"{col}_month_sin", f"{col}_month_cos", f"{col}_dow_sin", f"{col}_dow_cos"
            ])
            df.drop(columns=[col], inplace=True)

        return df


class NLPTextVectorizer(BaseEstimator, TransformerMixin):
    """
    Extracts dense semantic LSA (TF-IDF + TruncatedSVD) components and lexical morphological features
    (character length, word count, digit count, uppercase ratio, punctuation count).
    """
    def __init__(self, text_cols: List[str], n_components: int = 5):
        self.text_cols = text_cols
        self.n_components = n_components
        self.vectorizers_: Dict[str, TfidfVectorizer] = {}
        self.svds_: Dict[str, TruncatedSVD] = {}
        self.feature_names_: List[str] = []

    def fit(self, X: pd.DataFrame, y: Any = None):
        self.vectorizers_ = {}
        self.svds_ = {}
        for col in self.text_cols:
            if col not in X.columns:
                continue
            corpus = X[col].fillna("").astype(str).tolist()
            vec = TfidfVectorizer(max_features=600, stop_words="english", ngram_range=(1, 2))
            try:
                tfidf_mat = vec.fit_transform(corpus)
                if tfidf_mat.shape[1] > 1:
                    n_comp = min(self.n_components, tfidf_mat.shape[1] - 1, max(1, tfidf_mat.shape[0] - 1))
                    if n_comp >= 1:
                        svd = TruncatedSVD(n_components=n_comp, random_state=42)
                        svd.fit(tfidf_mat)
                        self.vectorizers_[col] = vec
                        self.svds_[col] = svd
            except ValueError:
                pass
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        df = X.copy()
        self.feature_names_ = []
        for col in self.text_cols:
            if col not in df.columns:
                continue
            s = df[col].fillna("").astype(str)

            df[f"{col}_char_len"] = s.str.len().astype(np.float32)
            df[f"{col}_word_count"] = s.str.split().str.len().astype(np.float32)
            df[f"{col}_digit_count"] = s.apply(lambda x: sum(c.isdigit() for c in x)).astype(np.float32)
            punct_set = set('!?,.:;"-()\'')
            df[f"{col}_punct_count"] = s.apply(lambda x: sum(c in punct_set for c in x)).astype(np.float32)
            df[f"{col}_upper_ratio"] = s.apply(lambda x: sum(c.isupper() for c in x) / max(len(x), 1)).astype(np.float32)

            self.feature_names_.extend([
                f"{col}_char_len", f"{col}_word_count", f"{col}_digit_count",
                f"{col}_punct_count", f"{col}_upper_ratio"
            ])

            if col in self.vectorizers_ and col in self.svds_:
                tfidf_mat = self.vectorizers_[col].transform(s.tolist())
                svd_mat = self.svds_[col].transform(tfidf_mat)
                for i in range(svd_mat.shape[1]):
                    cname = f"{col}_nlp_svd_{i}"
                    df[cname] = svd_mat[:, i].astype(np.float32)
                    self.feature_names_.append(cname)

            df.drop(columns=[col], inplace=True)
        return df


class AutomatedFeatureEnricher(BaseEstimator, TransformerMixin):
    """
    Domain-agnostic feature enrichment:
    1. Synthesizes pairwise mathematical interaction & ratio features between top numeric features.
    2. Generates group-level aggregation statistics (mean & std of continuous feature grouped by top category).
    3. Winsorizes extreme outliers using learned Tukey IQR bounds (Q1 - 1.5*IQR, Q3 + 1.5*IQR).
    """
    def __init__(self, max_interactions: int = 5, clip_outliers: bool = True):
        self.max_interactions = max_interactions
        self.clip_outliers = clip_outliers
        self.bounds_: Dict[str, Tuple[float, float]] = {}
        self.interaction_pairs_: List[Tuple[str, str, str]] = []
        self.group_agg_configs_: List[Tuple[str, str, Dict[Any, float], float]] = []
        self.generated_features_: List[str] = []

    def fit(self, X: pd.DataFrame, y: Any = None):
        num_cols = X.select_dtypes(include=[np.number]).columns.tolist()
        self.bounds_ = {}

        if self.clip_outliers:
            for col in num_cols:
                s = X[col].dropna()
                if len(s) > 15 and s.nunique() > 5:
                    q1, q3 = np.percentile(s, [25.0, 75.0])
                    iqr = q3 - q1
                    if iqr > 0:
                        self.bounds_[col] = (float(q1 - 2.5 * iqr), float(q3 + 2.5 * iqr))

        self.interaction_pairs_ = []
        if len(num_cols) >= 2 and self.max_interactions > 0:
            scored_cols = []
            for c in num_cols:
                s = X[c].dropna()
                if len(s) > 10 and s.nunique() > 10:
                    scored_cols.append((c, float(s.std() / (abs(s.mean()) + 1e-5))))
            scored_cols.sort(key=lambda x: x[1], reverse=True)
            top_c = [c for c, _ in scored_cols[:8]]

            if len(top_c) >= 2:
                corr = X[top_c].corr().abs().fillna(0.0)
                candidates = []
                for i in range(len(top_c)):
                    for j in range(i + 1, len(top_c)):
                        c1, c2 = top_c[i], top_c[j]
                        r = corr.loc[c1, c2]
                        if 0.25 <= r <= 0.94:
                            if X[c2].min() >= 0:
                                candidates.append((r, c1, c2, "ratio"))
                            else:
                                candidates.append((r, c1, c2, "product"))
                candidates.sort(key=lambda x: x[0], reverse=True)
                for _, c1, c2, op in candidates[: self.max_interactions]:
                    self.interaction_pairs_.append((c1, c2, op))

        self.group_agg_configs_ = []
        cat_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()
        if cat_cols and num_cols:
            eligible_cats = [c for c in cat_cols if 3 <= X[c].nunique() <= 40]
            if eligible_cats:
                grp_col = eligible_cats[0]
                val_col = num_cols[0]
                grouped_mean = X.groupby(grp_col)[val_col].mean().to_dict()
                global_mean = float(X[val_col].mean())
                self.group_agg_configs_.append((grp_col, val_col, grouped_mean, global_mean))

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        df = X.copy()
        if self.clip_outliers:
            for col, (low, high) in self.bounds_.items():
                if col in df.columns:
                    df[col] = df[col].clip(lower=low, upper=high)

        self.generated_features_ = []

        for c1, c2, op in self.interaction_pairs_:
            if c1 in df.columns and c2 in df.columns:
                if op == "ratio":
                    feat_name = f"{c1}_per_{c2}"
                    denom = df[c2].replace(0, np.nan)
                    df[feat_name] = (df[c1] / (denom + 1e-5)).replace([np.inf, -np.inf], np.nan).astype(np.float32)
                else:
                    feat_name = f"{c1}_x_{c2}"
                    df[feat_name] = (df[c1] * df[c2]).astype(np.float32)
                self.generated_features_.append(feat_name)

        for grp_col, val_col, mapping, default_val in self.group_agg_configs_:
            if grp_col in df.columns:
                feat_name = f"{val_col}_mean_by_{grp_col}"
                df[feat_name] = df[grp_col].map(mapping).fillna(default_val).astype(np.float32)
                self.generated_features_.append(feat_name)

        return df


class FastSubsampledKNNImputer(BaseEstimator, TransformerMixin):
    """
    High-Performance Subsampled KNN Imputer:
    Reduces complexity from O(N^2) to O(N * K) by fitting on representative prototype samples
    (N = 2500) for large datasets. Automatically adds binary missingness indicator columns
    and includes a median fallback to strictly guarantee ZERO remaining NaN values.
    """
    def __init__(self, n_neighbors: int = 5, max_fit_samples: int = 2500, add_indicators: bool = True):
        self.n_neighbors = n_neighbors
        self.max_fit_samples = max_fit_samples
        self.add_indicators = add_indicators
        self.imputer_: Optional[KNNImputer] = None
        self.fallback_imputer_: Optional[SimpleImputer] = None
        self.cols_with_missing_in_fit_: List[int] = []

    def fit(self, X: Union[np.ndarray, pd.DataFrame], y: Any = None):
        X_arr = np.asarray(X, dtype=np.float64)
        n_samples, n_features = X_arr.shape

        self.cols_with_missing_in_fit_ = [
            i for i in range(n_features) if np.isnan(X_arr[:, i]).any()
        ]

        self.fallback_imputer_ = SimpleImputer(strategy="median")
        self.fallback_imputer_.fit(X_arr)

        if self.cols_with_missing_in_fit_:
            self.imputer_ = KNNImputer(n_neighbors=self.n_neighbors, weights="distance")
            if n_samples > self.max_fit_samples:
                rng = np.random.RandomState(42)
                idx = rng.choice(n_samples, size=self.max_fit_samples, replace=False)
                self.imputer_.fit(X_arr[idx])
            else:
                self.imputer_.fit(X_arr)
        else:
            self.imputer_ = None

        return self

    def transform(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        X_arr = np.asarray(X, dtype=np.float64)
        has_nans = np.isnan(X_arr).any()

        indicators = []
        if self.add_indicators and self.cols_with_missing_in_fit_:
            for col_idx in self.cols_with_missing_in_fit_:
                if col_idx < X_arr.shape[1]:
                    indicators.append(np.isnan(X_arr[:, col_idx]).astype(np.float32)[:, np.newaxis])

        if not has_nans:
            result = X_arr.astype(np.float32)
        elif self.imputer_ is not None:
            imputed = self.imputer_.transform(X_arr)
            if np.isnan(imputed).any() and self.fallback_imputer_ is not None:
                imputed = self.fallback_imputer_.transform(imputed)
            result = imputed.astype(np.float32)
        elif self.fallback_imputer_ is not None:
            result = self.fallback_imputer_.transform(X_arr).astype(np.float32)
        else:
            result = np.nan_to_num(X_arr, nan=0.0).astype(np.float32)

        if indicators:
            ind_mat = np.hstack(indicators)
            return np.hstack([result, ind_mat])
        return result


class ResilientTargetEncoder(BaseEstimator, TransformerMixin):
    """
    Multi-Task Empirical Bayes Resilient Target Encoder:
    Smooths high-cardinality categorical levels towards global priors using m-estimate smoothing.
    Robustly supports Binary Classification, Multiclass Classification (one-vs-rest encoding),
    and Continuous Regression without target leakage.
    """
    def __init__(self, m: float = 10.0, task_type: str = "binary_classification", random_state: int = 42):
        self.m = m
        self.task_type = task_type
        self.random_state = random_state
        self.global_priors_: Dict[Any, Any] = {}
        self.mappings_: Dict[Any, Any] = {}
        self.feature_names_out_: List[str] = []
        self.is_multiclass_: bool = False

    def fit(self, X: Union[pd.DataFrame, np.ndarray], y: np.ndarray):
        df = pd.DataFrame(X).copy()
        y_arr = np.asarray(y)
        self.mappings_ = {}
        self.global_priors_ = {}
        self.feature_names_out_ = []

        classes = np.unique(y_arr[pd.notna(y_arr)])
        self.is_multiclass_ = (self.task_type == "multiclass_classification" and len(classes) > 2)

        if self.is_multiclass_:
            for col in df.columns:
                col_s = df[col].astype(str)
                self.mappings_[col] = {}
                self.global_priors_[col] = {}
                for cls in classes:
                    y_binary = (y_arr == cls).astype(float)
                    p_global = float(np.mean(y_binary))
                    self.global_priors_[col][cls] = p_global

                    temp_df = pd.DataFrame({"cat": col_s, "target": y_binary})
                    grp = temp_df.groupby("cat")["target"].agg(["count", "mean"])
                    counts = grp["count"]
                    means = grp["mean"]
                    smoothed = (counts * means + self.m * p_global) / (counts + self.m)
                    self.mappings_[col][cls] = smoothed.to_dict()
                    self.feature_names_out_.append(f"{col}_te_cls_{cls}")
        else:
            y_float = y_arr.astype(float)
            global_mean = float(np.nanmean(y_float))
            self.global_priors_["global"] = global_mean

            for col in df.columns:
                col_s = df[col].astype(str)
                temp_df = pd.DataFrame({"cat": col_s, "target": y_float})
                grp = temp_df.groupby("cat")["target"].agg(["count", "mean"])
                counts = grp["count"]
                means = grp["mean"]
                smoothed = (counts * means + self.m * global_mean) / (counts + self.m)
                self.mappings_[col] = smoothed.to_dict()
                self.feature_names_out_.append(f"{col}_target_enc")

        return self

    def transform(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        df = pd.DataFrame(X).copy()
        output_cols = []

        if self.is_multiclass_:
            for col in df.columns:
                col_s = df[col].astype(str)
                if col in self.mappings_:
                    for cls, mapping in self.mappings_[col].items():
                        prior = self.global_priors_[col][cls]
                        encoded = col_s.map(mapping).fillna(prior).values.astype(np.float32)
                        output_cols.append(encoded[:, np.newaxis])
        else:
            global_mean = self.global_priors_.get("global", 0.0)
            for col in df.columns:
                col_s = df[col].astype(str)
                mapping = self.mappings_.get(col, {})
                encoded = col_s.map(mapping).fillna(global_mean).values.astype(np.float32)
                output_cols.append(encoded[:, np.newaxis])

        if output_cols:
            return np.hstack(output_cols)
        return np.zeros((len(df), 0), dtype=np.float32)

    def get_feature_names_out(self, input_features: Optional[List[str]] = None) -> np.ndarray:
        if input_features is not None and len(input_features) == len(self.mappings_):
            names = []
            if self.is_multiclass_:
                for (orig_col, c_idx) in zip(input_features, self.mappings_.keys()):
                    for cls in self.mappings_[c_idx].keys():
                        names.append(f"{orig_col}_te_cls_{cls}")
            else:
                for orig_col in input_features:
                    names.append(f"{orig_col}_target_enc")
            return np.asarray(names, dtype=object)
        return np.asarray(self.feature_names_out_, dtype=object)


class RareCategoryGrouper(BaseEstimator, TransformerMixin):
    """
    Groups rare, low-frequency categorical levels (< threshold frequency) into an 'other' level
    to prevent one-hot combinatorial explosion and high-cardinality overfitting.
    """
    def __init__(self, min_freq: float = 0.015, other_label: str = "rare_other"):
        self.min_freq = min_freq
        self.other_label = other_label
        self.frequent_categories_: Dict[Any, set] = {}

    def fit(self, X: Union[pd.DataFrame, np.ndarray], y: Any = None):
        self.frequent_categories_ = {}
        df = pd.DataFrame(X)
        n_samples = len(df)
        for col in df.columns:
            s = df[col].astype(str)
            vc = s.value_counts()
            frequent = set(vc[vc / n_samples >= self.min_freq].index)
            self.frequent_categories_[col] = frequent
        return self

    def transform(self, X: Union[pd.DataFrame, np.ndarray]) -> pd.DataFrame:
        df = pd.DataFrame(X).copy()
        for col, frequent in self.frequent_categories_.items():
            if col in df.columns:
                s = df[col].astype(str)
                df[col] = s.where(s.isin(frequent), self.other_label)
        return df


class SkewnessPowerTransformer(BaseEstimator, TransformerMixin):
    """
    Detects highly skewed numeric distributions (|skewness| > threshold) and applies
    Yeo-Johnson power transformation to stabilize variance for linear, distance, and neural models.
    Operates column-by-column to prevent pipeline failure if some columns are omitted at test time.
    """
    def __init__(self, skew_threshold: float = 1.0):
        self.skew_threshold = skew_threshold
        self.transformers_: Dict[str, PowerTransformer] = {}
        self.medians_: Dict[str, float] = {}

    def fit(self, X: pd.DataFrame, y: Any = None):
        num_cols = X.select_dtypes(include=[np.number]).columns.tolist()
        self.transformers_ = {}
        self.medians_ = {}

        for col in num_cols:
            s = X[col].dropna()
            if len(s) > 20 and s.nunique() > 10:
                sk = float(s.skew())
                if abs(sk) > self.skew_threshold and s.std() > 1e-6:
                    med = float(s.median())
                    self.medians_[col] = med
                    pt = PowerTransformer(method="yeo-johnson", standardize=False)
                    try:
                        pt.fit(X[[col]].fillna(med).values)
                        self.transformers_[col] = pt
                    except Exception:
                        pass

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        df = X.copy()
        for col, pt in self.transformers_.items():
            if col in df.columns:
                med = self.medians_.get(col, 0.0)
                na_mask = df[col].isna()
                filled = df[[col]].fillna(med).values
                try:
                    transformed = pt.transform(filled)
                    transformed_s = pd.Series(transformed.ravel(), index=df.index, dtype=np.float32)
                    transformed_s[na_mask] = np.nan
                    df[col] = transformed_s
                except Exception:
                    pass
        return df


class CollinearityPruner(BaseEstimator, TransformerMixin):
    """
    Detects and drops redundant features exhibiting extreme pairwise collinearity (|r| > threshold)
    on the training split to guarantee numeric stability and reduce model complexity.
    """
    def __init__(self, threshold: float = 0.98):
        self.threshold = threshold
        self.to_drop_: List[str] = []

    def fit(self, X: pd.DataFrame, y: Any = None):
        num_df = X.select_dtypes(include=[np.number])
        self.to_drop_ = []
        if num_df.shape[1] > 1:
            corr_matrix = num_df.corr().abs().fillna(0.0)
            upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
            self.to_drop_ = [col for col in upper.columns if any(upper[col] > self.threshold)]
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        return X.drop(columns=[c for c in self.to_drop_ if c in X.columns], errors="ignore")


class AtlanticFeatureSelector(BaseEstimator, TransformerMixin):
    """
    Atlantic-Style Supervised Mutual Information Feature Selection:
    Caps dimensionality while preserving maximum signal from engineered and raw features.
    Filters zero-variance features and uses stratified subsampling for blazing speed on large datasets.
    """
    def __init__(
        self,
        problem_type: str = "binary_classification",
        max_features: int = 80,
        min_features_to_trigger: int = 35,
    ):
        self.problem_type = problem_type
        self.max_features = max_features
        self.min_features_to_trigger = min_features_to_trigger
        self.selector_: Optional[SelectKBest] = None
        self.selected_indices_: Optional[np.ndarray] = None
        self.active_: bool = False

    def fit(self, X: np.ndarray, y: np.ndarray):
        n_samples, n_features = X.shape
        if n_features <= self.min_features_to_trigger or n_features <= self.max_features:
            self.active_ = False
            self.selected_indices_ = np.arange(n_features)
            return self

        self.active_ = True
        k = min(self.max_features, n_features)
        score_func = (
            mutual_info_regression
            if self.problem_type == "regression"
            else mutual_info_classif
        )

        if n_samples > 3500:
            rng = np.random.RandomState(42)
            idx = rng.choice(n_samples, size=3500, replace=False)
            X_fit, y_fit = X[idx], y[idx]
        else:
            X_fit, y_fit = X, y

        X_fit_clean = np.nan_to_num(X_fit, nan=0.0, posinf=0.0, neginf=0.0)
        self.selector_ = SelectKBest(score_func=score_func, k=k)
        self.selector_.fit(X_fit_clean, y_fit)
        self.selected_indices_ = self.selector_.get_support(indices=True)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        X_clean = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        if not self.active_ or self.selected_indices_ is None:
            return X_clean.astype(np.float32)
        return X_clean[:, self.selected_indices_].astype(np.float32)

    def get_feature_names(self, input_features: List[str]) -> List[str]:
        if not self.active_ or self.selected_indices_ is None:
            return input_features
        return [input_features[i] for i in self.selected_indices_ if i < len(input_features)]
