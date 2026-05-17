"""Abstract interface for efficiency-ratio regressors.

Any concrete regressor (k-NN, decision tree, linear, MLP, XGBoost, ...) must
implement this interface so the RL state builder and training pipeline can
consume them interchangeably (Liskov Substitution).
"""

from abc import ABC, abstractmethod

import numpy as np


class BaseEfficiencyPredictor(ABC):
    """Predicts efficiency_ratio = actual_minutes / estimated_minutes."""

    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Fit the regressor on a feature matrix X and target vector y."""
        ...

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Return predicted efficiency_ratios for each row of X."""
        ...
