from typing import Any, Dict
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


class AgentFlowPipeline(BaseEstimator, TransformerMixin):
    """
    Production-Ready Inference Pipeline Container:
    Encapsulates all sequential transformation stages, schema metadata, and drift baselines.
    Ensures safe, deterministic inference on unseen test streams with automatic schema alignment.
    """
    def __init__(self, pipeline_dict: Dict[str, Any]):
        self.pipeline_dict = pipeline_dict

    def transform(self, df_new: pd.DataFrame) -> pd.DataFrame:
        p = self.pipeline_dict
        df = df_new.copy()

        if p["target_col"] in df.columns:
            df = df.drop(columns=[p["target_col"]])

        df = p["type_cleaner"].transform(df)
        df = df.drop(columns=[c for c in p["dropped_cols"] if c in df.columns], errors="ignore")
        df = p["dt_extractor"].transform(df)
        df = p["nlp_extractor"].transform(df)
        df = p["enricher"].transform(df)
        df = p["skew_transformer"].transform(df)
        df = p["collinearity_pruner"].transform(df)

        expected_cols = p["expected_col_transformer_columns"]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = 0.0

        cols_to_keep = [c for c in expected_cols if c in df.columns]
        df = df[cols_to_keep]

        mat = p["col_transformer"].transform(df)
        mat_sel = p["selector"].transform(mat)
        if p["pca_model"] is not None:
            mat_sel = p["pca_model"].transform(mat_sel)

        final_cols = p["final_feature_names"]
        if mat_sel.shape[1] == len(final_cols):
            return pd.DataFrame(mat_sel, columns=final_cols)
        return pd.DataFrame(mat_sel, columns=[f"feat_{i}" for i in range(mat_sel.shape[1])])
