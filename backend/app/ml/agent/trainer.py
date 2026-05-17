"""RL trainer — correct TD(0) Q-learning with a target network.

Key design decisions vs the original:

1. **Proper Bellman target via multi-state next_Q**
   Each Experience stores `next_states: list[np.ndarray] | None` — all
   candidate state vectors for the next task's eligible workers (with updated
   loads). The target is:
       target_i = R_i + γ * max_j Q_target(s'_{i,j})
   Using max Q over all candidates is correct Q-learning regardless of the
   behavioural policy (off-policy). Previously, a single next_state from the
   *chosen* worker of the next (different) task was used — causally wrong.

2. **Target network** (Mnih et al., 2015)
   A frozen copy of the Q-network is used to compute Bellman targets. The
   copy is refreshed every `target_update_freq` gradient steps. Without this,
   the Bellman target shifts every step (the Q-network chases its own shadow),
   causing training oscillation.

3. **Reward clipping**
   Clips rewards to [-5, 5] before computing targets. This prevents a small
   number of high-efficiency assignments from dominating gradient updates.
"""

from __future__ import annotations

from copy import deepcopy

import numpy as np

from app.ml.agent.q_network import LinearQNetwork, MLPQNetwork
from app.ml.agent.replay_buffer import ReplayBuffer

QNetwork = LinearQNetwork | MLPQNetwork


class RLTrainer:
    """Pulls mini-batches from the replay buffer and updates the Q-network."""

    def __init__(
        self,
        q_network: QNetwork,
        replay_buffer: ReplayBuffer,
        gamma: float = 0.9,
        batch_size: int = 128,
        min_buffer_size: int = 256,
        target_update_freq: int = 50,
        reward_clip: float = 5.0,
    ) -> None:
        self.q = q_network
        self.buf = replay_buffer
        self.gamma = gamma
        self.batch_size = batch_size
        self.min_buffer_size = min_buffer_size
        self.target_update_freq = target_update_freq
        self.reward_clip = reward_clip
        self._steps = 0
        # Target network — frozen copy updated every `target_update_freq` steps.
        self.q_target: QNetwork = deepcopy(q_network)

    def train_step(self, rng: np.random.Generator) -> float | None:
        """One Bellman update. Returns MSE loss, or None if buffer too small."""
        if len(self.buf) < self.min_buffer_size:
            return None

        batch = self.buf.sample(self.batch_size, rng)
        S = np.stack([e.state for e in batch])             # (B, D)
        R = np.clip(
            [e.reward for e in batch],
            -self.reward_clip,
            self.reward_clip,
        )                                                   # (B,)

        # Bellman targets using the TARGET network.
        next_Q = np.zeros(len(batch), dtype=float)
        for i, exp in enumerate(batch):
            if exp.next_states:
                # max Q over ALL candidates for the next task (correct Q-learning).
                next_Q[i] = max(
                    self.q_target.predict(sv) for sv in exp.next_states
                )
            # else: terminal → next_Q[i] stays 0

        targets = R + self.gamma * next_Q

        # Gradient step on the online network.
        loss = self.q.update_batch(S, targets)
        self._steps += 1

        # Periodically refresh the target network.
        if self._steps % self.target_update_freq == 0:
            self._sync_target()

        return loss

    def train_n_steps(self, n: int, rng: np.random.Generator) -> list[float]:
        """Run up to n training steps. Returns list of losses for steps that ran."""
        losses = []
        for _ in range(n):
            loss = self.train_step(rng)
            if loss is not None:
                losses.append(loss)
        return losses

    def _sync_target(self) -> None:
        if isinstance(self.q, MLPQNetwork) and isinstance(self.q_target, MLPQNetwork):
            self.q_target.copy_from(self.q)
        elif isinstance(self.q, LinearQNetwork) and isinstance(self.q_target, LinearQNetwork):
            self.q_target.copy_from(self.q)
