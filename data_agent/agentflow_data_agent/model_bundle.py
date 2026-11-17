"""AgentFlowModel: the object stored in best_model.pkl.

raw CSV rows -> Data Agent preprocessing -> trained model -> original class labels.
SECURITY: pickle files can run code when loaded. Only load files you trust.
"""
import numpy as np
import pandas as pd

from agentflow_data_agent.utils.io_handlers import clean_column_names


def _restore_labels(classes):
    labels = [str(c) for c in classes]
    try:
        nums = [float(x) for x in labels]
        if all(n.is_integer() for n in nums):
            return [int(n) for n in nums]      # "0"/"1" -> 0/1
    except ValueError:
        pass
    return labels


class AgentFlowModel:
    def __init__(self, preprocessor, estimator, meta):
        self.preprocessor = preprocessor
        self.estimator = estimator
        self.meta = dict(meta)
        enc = (getattr(preprocessor, "pipeline_dict", {}) or {}).get("target_label_encoder")
        self.class_labels = _restore_labels(enc.classes_) if enc is not None else None

    def _prepare(self, df):
        raw = clean_column_names(pd.DataFrame(df).copy())   # same header cleaning as training
        return self.preprocessor.transform(raw)

    def predict(self, df):
        pred = self.estimator.predict(self._prepare(df))
        if self.class_labels is None:
            return np.asarray(pred, dtype=float)
        return np.array([self.class_labels[int(i)] for i in pred], dtype=object)

    def predict_proba(self, df):
        if not hasattr(self.estimator, "predict_proba"):
            raise AttributeError("This model does not provide probabilities.")
        return self.estimator.predict_proba(self._prepare(df))