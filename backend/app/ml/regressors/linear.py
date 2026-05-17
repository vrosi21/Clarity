"""Ridge regression efficiency predictor.

Implements BaseEfficiencyPredictor. Provides interpretable coefficients and
acts as the weakest-baseline: if the non-linear models don't beat Ridge by a
meaningful margin the feature engineering likely needs work.
"""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import Ridge

from app.ml.base.predictor import BaseEfficiencyPredictor


class LinearPredictor(BaseEfficiencyPredictor):
    """Ridge regressor wrapper — predicts efficiency_ratio."""

    def __init__(self, alpha: float = 1.0) -> None:
        self._model = Ridge(alpha=alpha)

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self._model.fit(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self._model.predict(X)

    def coef(self) -> np.ndarray:
        return self._model.coef_
