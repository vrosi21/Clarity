"""FIFO experience replay buffer for the RL agent.

Each experience stores:
  - state: 17-dim state vector for the chosen (task, worker) pair.
  - reward: scalar reward from that assignment.
  - next_states: list of state vectors for ALL eligible workers for the
    NEXT task (with post-assignment worker loads). The trainer takes
    max Q over this set to compute the Bellman target. None = terminal.

Storing all next-state candidates (instead of just the chosen one) enables
correct TD(0) Q-learning: target = R + γ * max_j Q(s'_j).
"""

from __future__ import annotations

from collections import deque
from typing import NamedTuple

import numpy as np


class Experience(NamedTuple):
    state: np.ndarray
    reward: float
    next_states: list[np.ndarray] | None  # None = terminal; list = candidates for next task


class ReplayBuffer:
    """Fixed-capacity FIFO buffer — oldest experiences evicted when full."""

    def __init__(self, max_size: int = 50_000) -> None:
        self._buf: deque[Experience] = deque(maxlen=max_size)

    def store(
        self,
        state: np.ndarray,
        reward: float,
        next_states: list[np.ndarray] | None,
    ) -> None:
        copied_next = (
            [sv.copy() for sv in next_states] if next_states is not None else None
        )
        self._buf.append(Experience(state.copy(), reward, copied_next))

    def sample(self, batch_size: int, rng: np.random.Generator) -> list[Experience]:
        n = min(batch_size, len(self._buf))
        idxs = rng.choice(len(self._buf), size=n, replace=False)
        buf = list(self._buf)
        return [buf[int(i)] for i in idxs]

    def __len__(self) -> int:
        return len(self._buf)
