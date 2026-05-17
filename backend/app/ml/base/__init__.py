"""Abstract base classes (interfaces) for ML components.

Following the Dependency Inversion principle: high-level modules
(services, RL agent, training notebooks) depend on these abstractions,
not on concrete implementations.
"""

from app.ml.base.policy import BaseAssignmentPolicy
from app.ml.base.predictor import BaseEfficiencyPredictor

__all__ = ["BaseAssignmentPolicy", "BaseEfficiencyPredictor"]
