"""Random Forest efficiency regressor.

Implements BaseEfficiencyPredictor. Ensemble of decision trees that reduces
variance vs a single tree while retaining interpretable feature importances.
Usually the strongest out-of-the-box model in the regressor comparison.
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestRegressor

from app.ml.base.predictor import BaseEfficiencyPredictor


class RFPredictor(BaseEfficiencyPredictor):
    """Random Forest regressor wrapper — predicts efficiency_ratio."""

    def __init__(self, n_estimators: int = 100, max_depth: int | None = None) -> None:
        self._model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42,
            n_jobs=-1,
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self._model.fit(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self._model.predict(X)

    def feature_importances(self) -> np.ndarray:
        return self._model.feature_importances_
