"""RL assignment policy — Boltzmann (softmax) sampling over Q-values.

τ (temperature) controls exploration vs. exploitation:
    τ → 0:   near-deterministic, always picks max-Q worker (sprint/exploit mode)
    τ → ∞:   near-uniform random (maximum exploration / learning mode)
    τ = 0.3: default — moderate exploitation with some exploration

The Boltzmann formulation is the natural choice for the MDP framing: it
has a clear probabilistic interpretation, a well-defined temperature
parameter that admin can tune, and produces soft action probabilities
rather than a hard argmax (useful for the assignment suggestion UI).
"""

from __future__ import annotations

import numpy as np

from app.ml.agent.q_network import LinearQNetwork
from app.ml.base.policy import BaseAssignmentPolicy


class RLPolicy(BaseAssignmentPolicy):
    def __init__(self, q_network: LinearQNetwork) -> None:
        self._q = q_network

    def select_worker(self, state_vectors: list[np.ndarray], tau: float = 0.3) -> int:
        q_vals = np.array([self._q.predict(sv) for sv in state_vectors], dtype=float)
        # Subtract max for numerical stability before exp.
        shifted = q_vals - q_vals.max()
        tau = max(tau, 1e-6)
        exp_q = np.exp(shifted / tau)
        probs = exp_q / exp_q.sum()
        return int(np.random.choice(len(state_vectors), p=probs))

    def q_values(self, state_vectors: list[np.ndarray]) -> np.ndarray:
        """Raw Q-values for all candidates — used by the assignment suggestion UI."""
        return np.array([self._q.predict(sv) for sv in state_vectors])

    def probabilities(self, state_vectors: list[np.ndarray], tau: float = 0.3) -> np.ndarray:
        """Boltzmann probabilities — used for confidence display in the UI."""
        q_vals = self.q_values(state_vectors)
        shifted = q_vals - q_vals.max()
        exp_q = np.exp(shifted / max(tau, 1e-6))
        return exp_q / exp_q.sum()
