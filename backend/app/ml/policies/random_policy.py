"""Random assignment policy — uniform random over eligible workers.

This is the weakest baseline. Any policy that consistently beats random
has learned real signal; if it doesn't, the state features carry no
information useful for assignment decisions.
"""

from __future__ import annotations

import numpy as np

from app.ml.base.policy import BaseAssignmentPolicy


class RandomPolicy(BaseAssignmentPolicy):
    def __init__(self, seed: int | None = None) -> None:
        self._rng = np.random.default_rng(seed)

    def select_worker(self, state_vectors: list[np.ndarray], tau: float = 1.0) -> int:
        return int(self._rng.integers(len(state_vectors)))
