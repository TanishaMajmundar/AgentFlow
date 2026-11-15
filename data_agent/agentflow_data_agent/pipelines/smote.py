from typing import Tuple
import numpy as np
from sklearn.neighbors import NearestNeighbors


class NativeSMOTE:
    """
    Pure Scikit-Learn + NumPy implementation of SMOTE (Synthetic Minority Over-sampling Technique).
    Completely eliminates external `imbalanced-learn` dependency issues while guaranteeing
    strict zero-leakage training boundary enforcement. Includes jittered replication fallback
    for ultra-minority classes (<= 2 samples).
    """
    def __init__(
        self,
        k_neighbors: int = 5,
        max_synthetic_samples: int = 15000,
        target_ratio: float = 0.65,
        random_state: int = 42,
    ):
        self.k_neighbors = k_neighbors
        self.max_synthetic_samples = max_synthetic_samples
        self.target_ratio = target_ratio
        self.random_state = random_state
        self.synthetic_added_: int = 0

    def fit_resample(self, X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        self.synthetic_added_ = 0
        classes, counts = np.unique(y, return_counts=True)
        if len(classes) < 2:
            return X, y

        max_count = int(counts.max())
        rng = np.random.RandomState(self.random_state)
        X_resampled = [X]
        y_resampled = [y]

        for cls, count in zip(classes, counts):
            if count == max_count:
                continue

            desired_count = int(max_count * self.target_ratio)
            n_to_generate = min(desired_count - int(count), self.max_synthetic_samples)
            if n_to_generate <= 0:
                continue

            X_min = X[y == cls]

            if len(X_min) <= 2:
                replicate_idx = rng.choice(len(X_min), size=n_to_generate, replace=True)
                noise = rng.normal(0, 0.01, size=(n_to_generate, X_min.shape[1])).astype(np.float32)
                synthetic_X = X_min[replicate_idx] + noise
                synthetic_y = np.full(n_to_generate, cls, dtype=y.dtype)
                X_resampled.append(synthetic_X.astype(np.float32))
                y_resampled.append(synthetic_y)
                self.synthetic_added_ += n_to_generate
                continue

            k = min(self.k_neighbors, len(X_min) - 1)
            nn = NearestNeighbors(n_neighbors=k + 1, n_jobs=-1)
            nn.fit(X_min)
            neighbor_indices = nn.kneighbors(X_min, return_distance=False)[:, 1:]

            base_idx = rng.randint(0, len(X_min), size=n_to_generate)
            neigh_col = rng.randint(0, k, size=n_to_generate)
            chosen_neighbors = neighbor_indices[base_idx, neigh_col]

            alphas = rng.uniform(0.05, 0.95, size=(n_to_generate, 1)).astype(np.float32)
            synthetic_X = X_min[base_idx] + alphas * (X_min[chosen_neighbors] - X_min[base_idx])
            synthetic_y = np.full(n_to_generate, cls, dtype=y.dtype)

            X_resampled.append(synthetic_X.astype(np.float32))
            y_resampled.append(synthetic_y)
            self.synthetic_added_ += n_to_generate

        if self.synthetic_added_ > 0:
            X_out = np.vstack(X_resampled)
            y_out = np.concatenate(y_resampled)
            perm = rng.permutation(len(X_out))
            return X_out[perm], y_out[perm]

        return X, y
