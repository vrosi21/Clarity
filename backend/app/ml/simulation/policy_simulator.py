"""Policy-driven sprint simulator — used for RL training and baseline evaluation.

Key fix over the original: **next_states in each Experience are now the
candidate state vectors for ALL eligible workers for the NEXT task, computed
with post-assignment worker loads.**

This produces correct TD(0) Q-learning targets:
    target = R + γ * max_j Q(s'_j)

Previously, next_state was the chosen worker's state vector for the next
*different* task — causally disconnected from the current action. That made
the Bellman gradient signal effectively random noise, which is why RL
performed no better than random despite training.

The correct formulation captures opportunity cost: after assigning W to T,
W's load increases, which reduces the max Q achievable for the next task.
If W was critical for the next task (high proficiency), the opportunity cost
is high and the Q-value for (T, W) should be discounted accordingly.
"""

from __future__ import annotations

import heapq
import math
from collections import defaultdict
from typing import Any

import numpy as np

from app.ml.agent.replay_buffer import Experience
from app.ml.agent.state_builder import build_state_vector, build_state_vector_nlp
from app.ml.base.policy import BaseAssignmentPolicy
from app.ml.base.predictor import BaseEfficiencyPredictor
from app.ml.simulation.simulator import Simulator
from app.ml.simulation.task import SimTask
from app.ml.simulation.worker import SimWorker

_MAX_LOOP_ITERS: int = 1_000_000
_PROFICIENCY_FLOOR: float = 0.12
# Cap the number of candidate state vectors stored per experience to avoid
# memory blow-up on large teams. If the eligible pool exceeds this, sample
# randomly — the max-Q estimate is still approximately correct.
_MAX_NEXT_CANDIDATES: int = 15


def compute_reward(
    row: dict[str, Any],
    w_priority: float = 1.0,
    w_efficiency: float = 1.0,
    w_overload: float = 2.0,
) -> float:
    """Compute scalar reward from a completed-assignment row.

    Higher is better:
        + priority component: P1 tasks completing efficiently matter most.
        + efficiency component: 1/eff_ratio rewarded (lower ratio = faster).
        - overload penalty: assigning to a heavily loaded worker penalised.
    """
    efficiency_score = min(1.0 / max(row["efficiency_ratio"], 0.1), 2.0)
    priority_score = row["priority_numeric"] / 5.0
    overload_penalty = float(row["load_ratio_at_assignment"] > 0.8)
    return (
        w_priority * priority_score
        + w_efficiency * efficiency_score
        - w_overload * overload_penalty
    )


def _eligible_pool(
    workers: list[SimWorker],
    task: SimTask,
) -> list[SimWorker]:
    """Return the filtered pool of workers eligible for this task."""
    capacity_eligible = [
        w for w in workers
        if w.is_available
        and w.current_load + task.estimated_minutes <= w.burnout_threshold
    ]
    if not capacity_eligible:
        return []
    eligible = [
        w for w in capacity_eligible
        if w.category_proficiency.get(task.category, 0.0) >= _PROFICIENCY_FLOOR
    ]
    if eligible:
        return eligible
    # Fall back to the single least-bad worker.
    return [
        max(
            capacity_eligible,
            key=lambda w: w.category_proficiency.get(task.category, 0.0),
        )
    ]


def _build_next_state_candidates(
    next_task: SimTask,
    workers: list[SimWorker],
    regressor: BaseEfficiencyPredictor,
    rng: np.random.Generator,
    use_nlp: bool = False,
) -> list[np.ndarray] | None:
    """Build candidate state vectors for *next_task* with current worker loads.

    Returns None if no worker is eligible (terminal).
    Returns a list of state vectors — one per eligible candidate, capped at
    _MAX_NEXT_CANDIDATES to bound memory.
    """
    pool = _eligible_pool(workers, next_task)
    if not pool:
        return None
    if len(pool) > _MAX_NEXT_CANDIDATES:
        idxs = rng.choice(len(pool), size=_MAX_NEXT_CANDIDATES, replace=False)
        pool = [pool[int(i)] for i in idxs]
    builder = build_state_vector_nlp if use_nlp else build_state_vector
    return [
        builder(next_task, w, regressor, w.load_ratio())
        for w in pool
    ]


class PolicySimulator(Simulator):
    """Sprint simulator with pluggable assignment policy.

    Inherits noise model, row builder, and arrival-time logic from Simulator.
    Adds policy-based worker selection and RL experience collection with
    correct next-state construction.
    """

    def run_episode_with_policy(
        self,
        policy: BaseAssignmentPolicy,
        regressor: BaseEfficiencyPredictor,
        n_workers: int,
        n_tasks: int,
        seed: int,
        tau: float = 0.3,
        w_priority: float = 1.0,
        w_efficiency: float = 1.0,
        w_overload: float = 2.0,
        sprint_id: int = 0,
        use_nlp: bool = False,
        encoder=None,
    ) -> tuple[list[dict[str, Any]], list[Experience]]:
        rng = np.random.default_rng(seed)
        workers = self.worker_gen.generate(n_workers, rng=rng, use_nlp=use_nlp, encoder=encoder)
        tasks = self.task_gen.generate(n_tasks, rng=rng, use_nlp=use_nlp)
        self._assign_arrival_times(tasks, rng)
        return self._simulate_with_policy(
            workers, tasks, policy, regressor, tau,
            w_priority, w_efficiency, w_overload, rng, sprint_id,
            use_nlp=use_nlp,
        )

    def run_dataset_with_policy(
        self,
        policy: BaseAssignmentPolicy,
        regressor: BaseEfficiencyPredictor,
        n_episodes: int,
        seed: int = 0,
        tau: float = 0.3,
        w_priority: float = 1.0,
        w_efficiency: float = 1.0,
        w_overload: float = 2.0,
    ) -> tuple[list[dict[str, Any]], list[Experience]]:
        master = np.random.default_rng(seed)
        load_choices = np.array([15, 20, 30, 40, 50, 60])
        lo, hi = self.team_size_range

        all_rows: list[dict[str, Any]] = []
        all_exp: list[Experience] = []

        for episode in range(n_episodes):
            n_workers = int(master.integers(lo, hi + 1))
            n_tasks = int(master.choice(load_choices))
            ep_seed = int(master.integers(0, 2**31 - 1))
            rows, exps = self.run_episode_with_policy(
                policy=policy, regressor=regressor,
                n_workers=n_workers, n_tasks=n_tasks,
                seed=ep_seed, tau=tau,
                w_priority=w_priority, w_efficiency=w_efficiency,
                w_overload=w_overload, sprint_id=episode,
            )
            all_rows.extend(rows)
            all_exp.extend(exps)

        return all_rows, all_exp

    # ----------------------------------------------------------------- private

    def _simulate_with_policy(
        self,
        workers: list[SimWorker],
        tasks: list[SimTask],
        policy: BaseAssignmentPolicy,
        regressor: BaseEfficiencyPredictor,
        tau: float,
        w_priority: float,
        w_efficiency: float,
        w_overload: float,
        rng: np.random.Generator,
        sprint_id: int,
        use_nlp: bool = False,
    ) -> tuple[list[dict[str, Any]], list[Experience]]:
        builder = build_state_vector_nlp if use_nlp else build_state_vector
        pending = sorted(tasks, key=lambda t: (t.arrival_time, t.priority, t.id))
        pending_idx = 0

        available: list[SimTask] = []
        in_flight: list[tuple[float, int, int, str, int, float]] = []
        tiebreak_counter = 0

        history: dict[tuple[int, str], list[float]] = defaultdict(list)
        worker_by_id: dict[int, SimWorker] = {w.id: w for w in workers}

        # Each record: (chosen_sv, row, next_states)
        # next_states = candidate svs for the NEXT task with updated loads.
        assignment_records: list[tuple[np.ndarray, dict[str, Any], list[np.ndarray] | None]] = []
        clock = 0.0

        for _ in range(_MAX_LOOP_ITERS):
            if pending_idx >= len(pending) and not available and not in_flight:
                break

            while (
                pending_idx < len(pending)
                and pending[pending_idx].arrival_time <= clock + 1e-9
            ):
                available.append(pending[pending_idx])
                pending_idx += 1

            available.sort(key=lambda t: (t.priority, t.id))

            still_stuck: list[SimTask] = []
            assigned_any = False

            for task_i, task in enumerate(available):
                pool = _eligible_pool(workers, task)
                if not pool:
                    still_stuck.append(task)
                    continue

                # Build state vector for each candidate with CURRENT loads.
                state_vecs = [
                    builder(task, w, regressor, w.load_ratio())
                    for w in pool
                ]

                chosen_idx = policy.select_worker(state_vecs, tau)
                chosen = pool[chosen_idx]
                chosen_sv = state_vecs[chosen_idx]

                load_ratio = chosen.load_ratio()
                obs = history[(chosen.id, task.category)]
                hist_eff = float(np.mean(obs)) if len(obs) >= 3 else math.nan

                actual, was_blocked, proficiency = self._simulate_actual_minutes(chosen, task, rng)
                eff_ratio = actual / max(task.estimated_minutes, 1)
                task_completion_time = clock + actual

                # Update load BEFORE building next_state candidates so that
                # chosen's updated load is reflected in the next decision.
                chosen.current_load += task.estimated_minutes

                tiebreak_counter += 1
                heapq.heappush(
                    in_flight,
                    (
                        task_completion_time,
                        tiebreak_counter,
                        chosen.id,
                        task.category,
                        task.estimated_minutes,
                        eff_ratio,
                    ),
                )

                row = self._build_row(
                    task=task,
                    worker=chosen,
                    load_ratio_at_assignment=load_ratio,
                    historical_efficiency=hist_eff,
                    actual_minutes=actual,
                    efficiency_ratio=eff_ratio,
                    was_blocked=was_blocked,
                    sprint_id=sprint_id,
                    skill_match_score=proficiency,
                    arrival_time=task.arrival_time,
                    completion_time=task_completion_time,
                )

                # ── Build correct next_states (the critical fix) ──────────
                # Identify the next task and compute all eligible workers'
                # state vectors WITH the load update from this assignment.
                next_states: list[np.ndarray] | None = None
                if task_i + 1 < len(available):
                    # Next task is in the same clock-cycle batch.
                    next_states = _build_next_state_candidates(
                        available[task_i + 1], workers, regressor, rng, use_nlp=use_nlp,
                    )
                elif pending_idx < len(pending):
                    # Next task arrives in a future clock cycle.
                    # Use the highest-priority pending task as an approximation.
                    next_states = _build_next_state_candidates(
                        pending[pending_idx], workers, regressor, rng, use_nlp=use_nlp,
                    )
                # else: no more tasks → terminal (next_states = None)

                assignment_records.append((chosen_sv, row, next_states))
                assigned_any = True

            available = still_stuck

            if not assigned_any:
                next_complete = in_flight[0][0] if in_flight else math.inf
                next_arrive = (
                    pending[pending_idx].arrival_time
                    if pending_idx < len(pending)
                    else math.inf
                )
                next_time = min(next_complete, next_arrive)
                if next_time == math.inf:
                    break
                clock = next_time

                while in_flight and in_flight[0][0] <= clock + 1e-9:
                    _, _, worker_id, category, est_min, eff_ratio = heapq.heappop(in_flight)
                    w = worker_by_id[worker_id]
                    w.current_load = max(0, w.current_load - est_min)
                    history[(worker_id, category)].append(eff_ratio)

        rows = [rec[1] for rec in assignment_records]
        experiences: list[Experience] = [
            Experience(sv, compute_reward(row, w_priority, w_efficiency, w_overload), next_svs)
            for sv, row, next_svs in assignment_records
        ]
        return rows, experiences
