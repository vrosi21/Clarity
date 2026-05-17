"""Round-robin assignment policy — cycles through workers by position.

Stronger than random because it avoids concentrating load on one worker,
but weaker than greedy because it ignores skill match entirely.
"""

from __future__ import annotations

import numpy as np

from app.ml.base.policy import BaseAssignmentPolicy


class RoundRobinPolicy(BaseAssignmentPolicy):
    def __init__(self) -> None:
        self._counter = 0

    def select_worker(self, state_vectors: list[np.ndarray], tau: float = 1.0) -> int:
        idx = self._counter % len(state_vectors)
        self._counter += 1
        return idx

    def reset(self) -> None:
        self._counter = 0
