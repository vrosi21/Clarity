"""Greedy assignment policy — picks the worker with the lowest predicted efficiency ratio.

This is the strongest non-RL baseline: always assign to whoever the regressor
predicts will finish fastest relative to the estimate. It has no lookahead and
cannot price in opportunity cost (e.g., giving your best backend engineer a
trivial ticket when a critical one arrives ten minutes later). This is exactly
the gap the RL agent is designed to close.
"""

from __future__ import annotations

import numpy as np

from app.ml.agent.state_builder import (
    IDX_PREDICTED_EFF,
    IDX_PREDICTED_EFF_NLP,
    STATE_DIM,
    STATE_DIM_NLP,
)
from app.ml.base.policy import BaseAssignmentPolicy


class GreedyPolicy(BaseAssignmentPolicy):
    """Always pick the worker whose predicted_eff_norm is lowest.

    Detects which state-vector layout is in use (legacy vs NLP) by inspecting
    the vector length, so the same policy works in both modes without config.
    """

    def select_worker(self, state_vectors: list[np.ndarray], tau: float = 1.0) -> int:
        dim = state_vectors[0].shape[0]
        idx = IDX_PREDICTED_EFF_NLP if dim == STATE_DIM_NLP else IDX_PREDICTED_EFF
        preds = np.array([sv[idx] for sv in state_vectors])
        return int(np.argmin(preds))
