"""k-Nearest-Neighbours efficiency regressor.

Implements BaseEfficiencyPredictor. Simple non-parametric baseline that
requires no assumptions about the functional form of the formula.
"""

from __future__ import annotations

import numpy as np
from sklearn.neighbors import KNeighborsRegressor

from app.ml.base.predictor import BaseEfficiencyPredictor


class KNNPredictor(BaseEfficiencyPredictor):
    """k-NN regressor wrapper — predicts efficiency_ratio for a (task, worker) pair."""

    def __init__(self, n_neighbors: int = 7) -> None:
        self._model = KNeighborsRegressor(n_neighbors=n_neighbors)

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self._model.fit(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self._model.predict(X)
