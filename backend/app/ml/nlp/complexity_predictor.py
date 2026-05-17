"""Complexity predictors: embed a task description → predict complexity 1–5.

Follows the same ABC pattern as BaseEfficiencyPredictor (Open/Closed: add a new
predictor by subclassing, zero changes to existing code).

Single Responsibility: each class fits and predicts — nothing else.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class BaseComplexityPredictor(ABC):
    """Predict task complexity (int 1–5) from an embedding vector."""

    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Fit on (N, dim) embedding matrix X and integer labels y in [1, 5]."""
        ...

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Return int array of predicted complexity values in [1, 5]."""
        ...


class RidgeComplexityPredictor(BaseComplexityPredictor):
    """Ridge regression on embeddings, output clipped and rounded to 1–5.

    Ridge is preferred over k-NN for production: it generalises better to
    unseen text (the regularisation prevents overfitting to training domains)
    and inference is O(d) not O(N·d).

    alpha=10 is a conservative default that avoids over-shrinkage while
    handling the high dimensionality of MiniLM embeddings (384 features).
    """

    def __init__(self, alpha: float = 10.0) -> None:
        from sklearn.linear_model import Ridge
        self._model = Ridge(alpha=alpha)

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self._model.fit(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        raw = self._model.predict(X)
        return np.clip(np.round(raw), 1, 5).astype(int)
