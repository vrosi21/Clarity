"""Decision-tree efficiency regressor.

Implements BaseEfficiencyPredictor. Provides human-interpretable feature
importances — useful for validating that proficiency_for_task_category is the
dominant predictor as the simulation formula requires.
"""

from __future__ import annotations

import numpy as np
from sklearn.tree import DecisionTreeRegressor

from app.ml.base.predictor import BaseEfficiencyPredictor


class DTPredictor(BaseEfficiencyPredictor):
    """Decision-tree regressor wrapper — predicts efficiency_ratio."""

    def __init__(self, max_depth: int = 8) -> None:
        self._model = DecisionTreeRegressor(max_depth=max_depth, random_state=42)

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self._model.fit(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self._model.predict(X)

    def feature_importances(self) -> np.ndarray:
        return self._model.feature_importances_
