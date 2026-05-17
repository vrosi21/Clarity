"""Abstract interface for assignment policies.

Random, round-robin, greedy, and RL policies all implement this interface.
This is what `AssignmentService` depends on (Dependency Inversion); the
concrete policy is wired in `app/core/dependencies.py`.
"""

from abc import ABC, abstractmethod

import numpy as np


class BaseAssignmentPolicy(ABC):
    """Selects which worker (by index) to assign a ticket to."""

    @abstractmethod
    def select_worker(self, state_vectors: list[np.ndarray], tau: float) -> int:
        """Return index into state_vectors of the chosen worker."""
        ...
