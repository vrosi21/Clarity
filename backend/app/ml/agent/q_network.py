"""Q-function approximators — pure NumPy, no PyTorch dependency.

LinearQNetwork:  Q(s) = s @ w + b          — simple, interpretable
MLPQNetwork:     Q(s) = MLP(s) [17→64→32→1] — captures feature interactions

Both expose the same predict / predict_batch / update_batch / get_weights /
set_weights interface so RLPolicy and RLTrainer work unchanged regardless
of which network is active.

MLPQNetwork uses the Adam optimiser with proper bias correction, which is
significantly more stable than vanilla SGD for noisy RL gradient signals.
"""

from __future__ import annotations

from copy import deepcopy

import numpy as np


# ─────────────────────────────────────────── LinearQNetwork (kept for compat) ─

class LinearQNetwork:
    """Q(s) = s @ w + b, trained by mini-batch SGD (MSE loss)."""

    def __init__(self, state_dim: int, lr: float = 1e-3) -> None:
        rng = np.random.default_rng(42)
        self.w: np.ndarray = rng.normal(0.0, 0.01, size=state_dim)
        self.b: float = 0.0
        self.lr = lr
        self.state_dim = state_dim

    def predict(self, s: np.ndarray) -> float:
        return float(s @ self.w + self.b)

    def predict_batch(self, S: np.ndarray) -> np.ndarray:
        return S @ self.w + self.b

    def update_batch(self, S: np.ndarray, targets: np.ndarray) -> float:
        preds = self.predict_batch(S)
        errors = preds - targets
        self.w -= self.lr * (S.T @ errors) / len(S)
        self.b -= self.lr * float(errors.mean())
        return float((errors ** 2).mean())

    def get_weights(self) -> dict[str, np.ndarray]:
        return {"w": self.w.copy(), "b": np.array([self.b])}

    def set_weights(self, weights: dict[str, np.ndarray]) -> None:
        self.w = weights["w"].copy()
        self.b = float(weights["b"][0])

    def copy_from(self, other: LinearQNetwork) -> None:
        self.w[:] = other.w
        self.b = other.b


# ─────────────────────────────────────────────── MLPQNetwork (recommended) ─

class MLPQNetwork:
    """Two-hidden-layer Q-network with Adam optimiser.

    Architecture: 17 → 64 → 32 → 1 with ReLU activations.

    A linear Q-function cannot model the interactions that drive opportunity
    cost (e.g. "proficiency matters *more* when task complexity is high").
    The MLP captures these with its first hidden layer, while remaining fast
    enough to train with NumPy on a CPU for the episode counts required here.

    Adam is used instead of SGD because:
      1. Adaptive per-parameter learning rates handle the wide variance in
         gradient magnitudes across the 17 input features.
      2. Bias correction prevents large initial updates that would destabilise
         the Bellman target in the first few hundred steps.
    """

    def __init__(
        self,
        state_dim: int = 17,
        hidden1: int = 64,
        hidden2: int = 32,
        lr: float = 3e-4,
        beta1: float = 0.9,
        beta2: float = 0.999,
        eps: float = 1e-8,
    ) -> None:
        self.state_dim = state_dim
        self.hidden1 = hidden1
        self.hidden2 = hidden2
        self.lr = lr
        self.beta1 = beta1
        self.beta2 = beta2
        self.eps = eps
        self._t = 0

        rng = np.random.default_rng(42)
        # He initialisation — appropriate for ReLU layers.
        self.w1 = rng.normal(0.0, np.sqrt(2.0 / state_dim), (state_dim, hidden1))
        self.b1 = np.zeros(hidden1)
        self.w2 = rng.normal(0.0, np.sqrt(2.0 / hidden1), (hidden1, hidden2))
        self.b2 = np.zeros(hidden2)
        self.w3 = rng.normal(0.0, np.sqrt(2.0 / hidden2), (hidden2, 1))
        self.b3 = np.zeros(1)

        # Adam moment accumulators.
        self._m = {n: np.zeros_like(p) for n, p in self._params()}
        self._v = {n: np.zeros_like(p) for n, p in self._params()}

    def _params(self):
        return [
            ("w1", self.w1), ("b1", self.b1),
            ("w2", self.w2), ("b2", self.b2),
            ("w3", self.w3), ("b3", self.b3),
        ]

    def predict(self, s: np.ndarray) -> float:
        h1 = np.maximum(0.0, s @ self.w1 + self.b1)
        h2 = np.maximum(0.0, h1 @ self.w2 + self.b2)
        return float((h2 @ self.w3 + self.b3).squeeze())

    def predict_batch(self, S: np.ndarray) -> np.ndarray:
        h1 = np.maximum(0.0, S @ self.w1 + self.b1)       # (B, H1)
        h2 = np.maximum(0.0, h1 @ self.w2 + self.b2)      # (B, H2)
        return (h2 @ self.w3 + self.b3).ravel()            # (B,)

    def update_batch(self, S: np.ndarray, targets: np.ndarray) -> float:
        B = len(S)
        # ── forward ─────────────────────────────────────────────────────
        h1_pre = S @ self.w1 + self.b1                     # (B, H1)
        h1 = np.maximum(0.0, h1_pre)
        h2_pre = h1 @ self.w2 + self.b2                    # (B, H2)
        h2 = np.maximum(0.0, h2_pre)
        out = (h2 @ self.w3 + self.b3).ravel()             # (B,)

        # ── MSE loss ────────────────────────────────────────────────────
        errors = out - targets                              # (B,)
        loss = float(np.mean(errors ** 2))

        # ── backward ────────────────────────────────────────────────────
        d_out = (2.0 / B) * errors                          # (B,)

        d_w3 = h2.T @ d_out.reshape(B, 1)                  # (H2, 1)
        d_b3 = np.array([d_out.sum()])

        d_h2 = d_out.reshape(B, 1) @ self.w3.T             # (B, H2)
        d_h2_pre = d_h2 * (h2_pre > 0)                    # ReLU gate
        d_w2 = h1.T @ d_h2_pre                             # (H1, H2)
        d_b2 = d_h2_pre.sum(axis=0)

        d_h1 = d_h2_pre @ self.w2.T                        # (B, H1)
        d_h1_pre = d_h1 * (h1_pre > 0)                    # ReLU gate
        d_w1 = S.T @ d_h1_pre                              # (D, H1)
        d_b1 = d_h1_pre.sum(axis=0)

        # ── Adam ────────────────────────────────────────────────────────
        self._t += 1
        bc1 = 1.0 - self.beta1 ** self._t
        bc2 = 1.0 - self.beta2 ** self._t

        for name, grad in [
            ("w1", d_w1), ("b1", d_b1),
            ("w2", d_w2), ("b2", d_b2),
            ("w3", d_w3), ("b3", d_b3),
        ]:
            m = self._m[name]
            v = self._v[name]
            m[:] = self.beta1 * m + (1.0 - self.beta1) * grad
            v[:] = self.beta2 * v + (1.0 - self.beta2) * grad ** 2
            step = self.lr * (m / bc1) / (np.sqrt(v / bc2) + self.eps)
            param = getattr(self, name)
            param -= step

        return loss

    def get_weights(self) -> dict[str, np.ndarray]:
        return {
            "w1": self.w1.copy(), "b1": self.b1.copy(),
            "w2": self.w2.copy(), "b2": self.b2.copy(),
            "w3": self.w3.copy(), "b3": self.b3.copy(),
            "meta_state_dim": np.array([self.state_dim]),
            "meta_hidden1": np.array([self.hidden1]),
            "meta_hidden2": np.array([self.hidden2]),
            "network_type": np.array(["mlp"]),
        }

    def set_weights(self, weights: dict[str, np.ndarray]) -> None:
        self.w1 = weights["w1"].copy()
        self.b1 = weights["b1"].copy()
        self.w2 = weights["w2"].copy()
        self.b2 = weights["b2"].copy()
        self.w3 = weights["w3"].copy()
        self.b3 = weights["b3"].copy()
        # Reset Adam moments so the loaded model can continue training cleanly.
        self._m = {n: np.zeros_like(p) for n, p in self._params()}
        self._v = {n: np.zeros_like(p) for n, p in self._params()}
        self._t = 0

    def copy_from(self, other: MLPQNetwork) -> None:
        self.w1[:] = other.w1
        self.b1[:] = other.b1
        self.w2[:] = other.w2
        self.b2[:] = other.b2
        self.w3[:] = other.w3
        self.b3[:] = other.b3
