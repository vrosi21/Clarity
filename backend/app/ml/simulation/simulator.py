"""Discrete-event sprint simulator — the core data-generation engine.

The Simulator runs one or many sprints and emits a row per *completed*
assignment containing exactly the dataset schema documented in the project
context. It is deliberately minimal: it knows nothing about the database,
nothing about FastAPI, and nothing about the assignment policy under
evaluation. Its single responsibility is to produce honest, reproducible
training data given a noise strategy and a generator pair.

Reproducibility: every stochastic decision goes through one
`np.random.Generator` derived from the user-provided seed. The global
numpy random state is never touched.

Algorithm (per sprint):
  1. Generate workers and tasks.
  2. Lay out arrival times: 70% at t=0, 30% spread over the first 60% of
     a 5-day sprint window.
  3. Loop:
        - move arrived tasks into an `available` queue (priority FIFO);
        - greedily try to assign each available task to a uniformly random
          eligible worker;
        - if no progress is possible, advance the clock to the next
          completion or arrival event.
  4. On task completion: free the worker's load and record the realised
     efficiency_ratio in their per-category history (used as the
     `historical_efficiency` feature for *future* assignments).

The Simulator deliberately uses a uniformly random eligible-worker policy:
the RL agent is trained from this data, it does not drive the simulation.
"""

from __future__ import annotations

import heapq
import math
from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd

from app.ml.simulation.generator import TaskGenerator, WorkerGenerator
from app.ml.simulation.noise import BaseNoiseStrategy
from app.ml.simulation.task import SimTask
from app.ml.simulation.worker import (
    CANONICAL_CATEGORIES,
    SENIORITY_RANK,
    SimWorker,
)

# 5-day sprint at 8 hours/day = 2400 minutes. Used only to lay out arrivals.
SPRINT_MINUTES: int = 5 * 8 * 60

# Late-arriving 30% of tasks come in over the first 60% of the sprint.
LATE_ARRIVAL_WINDOW: float = SPRINT_MINUTES * 0.6

# Hard guard against infinite loops (degenerate parameter combinations).
_MAX_LOOP_ITERS: int = 1_000_000

# Minimum proficiency for a worker to be considered for a task category.
# Below this, a real PM would not make the assignment. If no worker clears
# this bar we fall back to the least-bad eligible worker rather than holding
# the task indefinitely.
_PROFICIENCY_FLOOR: float = 0.12


class Simulator:
    """Runs sprints and emits completed-assignment dataset rows."""

    def __init__(
        self,
        noise_strategy: BaseNoiseStrategy | None = None,
        team_size_range: tuple[int, int] = (4, 12),
        worker_generator: WorkerGenerator | None = None,
        task_generator: TaskGenerator | None = None,
        seed: int | None = None,
    ) -> None:
        if noise_strategy is None:
            from app.ml.simulation.noise import LogNormalNoise
            noise_strategy = LogNormalNoise(sigma_multiplier=1.0)
        self.noise = noise_strategy
        self.team_size_range = team_size_range
        self.worker_gen = worker_generator or WorkerGenerator()
        self.task_gen = task_generator or TaskGenerator()
        self._default_seed = seed

    # ------------------------------------------------------------------ public

    def run_episode(
        self,
        n_workers: int,
        n_tasks: int,
        seed: int | None = None,
        sprint_id: int = 0,
        use_nlp: bool = False,
        encoder=None,
    ) -> list[dict[str, Any]]:
        """Simulate one sprint and return the list of dataset rows."""
        rng = np.random.default_rng(seed)
        workers = self.worker_gen.generate(n_workers, rng=rng, use_nlp=use_nlp, encoder=encoder)
        tasks = self.task_gen.generate(n_tasks, rng=rng, use_nlp=use_nlp)

        self._assign_arrival_times(tasks, rng)
        return self._simulate(workers, tasks, rng, sprint_id)

    def run_dataset(
        self,
        n_episodes: int,
        seed: int | None = None,
    ) -> pd.DataFrame:
        """Run many sprints with varied team size + load. Returns a DataFrame.

        Legacy mode only — use run_sprints() for NLP mode.
        """
        master = np.random.default_rng(seed)
        load_choices = np.array([15, 20, 30, 40, 50, 60])
        lo, hi = self.team_size_range

        rows: list[dict[str, Any]] = []
        for episode in range(n_episodes):
            n_workers = int(master.integers(lo, hi + 1))
            n_tasks = int(master.choice(load_choices))
            episode_seed = int(master.integers(0, 2**31 - 1))
            rows.extend(
                self.run_episode(
                    n_workers=n_workers,
                    n_tasks=n_tasks,
                    seed=episode_seed,
                    sprint_id=episode,
                    use_nlp=False,
                )
            )

        return pd.DataFrame(rows)

    def run_sprints(
        self,
        n_sprints: int,
        workers_per_sprint: tuple[int, int] = (4, 12),
        tasks_per_sprint: tuple[int, int] = (15, 60),
        task_generator: TaskGenerator | None = None,
        worker_generator: WorkerGenerator | None = None,
        use_nlp: bool = False,
        encoder=None,
        seed: int | None = None,
    ) -> list[dict[str, Any]]:
        """Run many sprints with NLP mode support. Returns raw row list."""
        effective_seed = seed if seed is not None else self._default_seed
        master = np.random.default_rng(effective_seed)

        # Allow per-call generator overrides without mutating instance state.
        orig_task_gen = self.task_gen
        orig_worker_gen = self.worker_gen
        if task_generator is not None:
            self.task_gen = task_generator
        if worker_generator is not None:
            self.worker_gen = worker_generator

        try:
            w_lo, w_hi = workers_per_sprint
            t_lo, t_hi = tasks_per_sprint
            rows: list[dict[str, Any]] = []
            for sprint in range(n_sprints):
                n_workers = int(master.integers(w_lo, w_hi + 1))
                n_tasks = int(master.integers(t_lo, t_hi + 1))
                sprint_seed = int(master.integers(0, 2**31 - 1))
                rows.extend(
                    self.run_episode(
                        n_workers=n_workers,
                        n_tasks=n_tasks,
                        seed=sprint_seed,
                        sprint_id=sprint,
                        use_nlp=use_nlp,
                        encoder=encoder,
                    )
                )
        finally:
            self.task_gen = orig_task_gen
            self.worker_gen = orig_worker_gen

        return rows

    # ----------------------------------------------------------------- private

    @staticmethod
    def _assign_arrival_times(tasks: list[SimTask], rng: np.random.Generator) -> None:
        """70% of tasks at t=0, 30% spread over LATE_ARRIVAL_WINDOW."""
        n = len(tasks)
        n_at_start = int(round(0.70 * n))
        n_late = n - n_at_start

        arrivals = [0.0] * n_at_start
        if n_late > 0:
            late = sorted(rng.uniform(0.0, LATE_ARRIVAL_WINDOW, size=n_late).tolist())
            arrivals.extend(late)

        # Shuffle arrival order across the task list so late arrivals are not
        # systematically the lowest-priority tasks.
        order = rng.permutation(n)
        for task, idx in zip(tasks, order):
            task.arrival_time = arrivals[idx]

    def _simulate(
        self,
        workers: list[SimWorker],
        tasks: list[SimTask],
        rng: np.random.Generator,
        sprint_id: int,
    ) -> list[dict[str, Any]]:
        # Pending arrivals sorted by arrival time, then priority for stability.
        pending = sorted(tasks, key=lambda t: (t.arrival_time, t.priority, t.id))
        pending_idx = 0

        available: list[SimTask] = []
        in_flight: list[tuple[float, int, int, str, int, float]] = []
        # tuple = (completion_time, tiebreak, worker_id, category, est_minutes, eff_ratio)
        tiebreak_counter = 0

        history: dict[tuple[int, str], list[float]] = defaultdict(list)
        worker_by_id: dict[int, SimWorker] = {w.id: w for w in workers}
        rows: list[dict[str, Any]] = []

        clock = 0.0

        for _ in range(_MAX_LOOP_ITERS):
            if pending_idx >= len(pending) and not available and not in_flight:
                break

            # 1) Absorb any arrivals at or before the current clock.
            while (
                pending_idx < len(pending)
                and pending[pending_idx].arrival_time <= clock + 1e-9
            ):
                available.append(pending[pending_idx])
                pending_idx += 1

            # Sort by priority (P1 first), FIFO within priority via task id.
            available.sort(key=lambda t: (t.priority, t.id))

            # 2) Try to assign every available task; collect what's still stuck.
            still_stuck: list[SimTask] = []
            assigned_any = False
            for task in available:
                # Capacity-eligible: available + within burnout.
                capacity_eligible = [
                    w for w in workers
                    if w.is_available
                    and w.current_load + task.estimated_minutes <= w.burnout_threshold
                ]
                if not capacity_eligible:
                    still_stuck.append(task)
                    continue

                eligible = [
                    w for w in capacity_eligible
                    if w.category_proficiency.get(task.category, 0.0) >= _PROFICIENCY_FLOOR
                ]
                if eligible:
                    chosen = eligible[int(rng.integers(0, len(eligible)))]
                else:
                    chosen = max(
                        capacity_eligible,
                        key=lambda w: w.category_proficiency.get(task.category, 0.0),
                    )

                # Snapshot features at assignment time.
                load_ratio = chosen.load_ratio()
                obs = history[(chosen.id, task.category)]
                hist_eff = float(np.mean(obs)) if len(obs) >= 3 else math.nan

                actual, was_blocked, proficiency = self._simulate_actual_minutes(chosen, task, rng)
                eff_ratio = actual / max(task.estimated_minutes, 1)
                task_completion_time = clock + actual

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

                rows.append(
                    self._build_row(
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
                )
                assigned_any = True

            available = still_stuck

            # 3) If nothing got assigned this round, advance time to the next event.
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

        return rows

    def _simulate_actual_minutes(
        self,
        worker: SimWorker,
        task: SimTask,
        rng: np.random.Generator,
    ) -> tuple[float, bool, float]:
        """Return (actual_minutes, was_blocked, proficiency).

        Skill is applied as a softened power-law instead of pure 1/proficiency
        so the multiplier stays in a sane range across the whole proficiency
        spectrum. The intercept sits below 1.0 to reflect that estimates in
        real teams are usually slightly padded — a top specialist genuinely
        beats the estimate. The dataset median lands ~1.7x, with about 7%
        of assignments completing under estimate.
            proficiency=1.0 -> 0.85x
            proficiency=0.7 -> ~0.98x
            proficiency=0.5 -> ~1.31x
            proficiency=0.3 -> ~1.61x
            proficiency=0.15 -> ~1.84x

        In NLP mode (both embeddings present), proficiency is computed as
        skill_match(worker_emb, task_emb) rescaled from the empirically observed
        raw score range → [0.0, 1.0]. all-MiniLM-L6-v2 similarity between
        software-domain worker/task texts is extremely compressed: raw cosine
        scores cluster tightly around 0.503 with std ≈ 0.014, putting the
        5th–95th pct at roughly [0.480, 0.526]. We clip to slightly wider bounds
        [0.475, 0.530] (span 0.055) so the full observed variance maps onto
        [0, 1] without truncating the tails.
        """
        if task.embedding is not None and worker.embedding is not None:
            # NLP mode: replace category_proficiency lookup with embedding similarity.
            # Lazy import — never loads sentence-transformers in legacy mode.
            from app.ml.nlp import skill_match as _skill_match
            raw_score = _skill_match(worker.embedding, task.embedding)
            # Rescale observed raw range [0.475, 0.530] → [0.0, 1.0].
            proficiency = float(np.clip((raw_score - 0.475) / 0.055, 0.0, 1.0))
        else:
            proficiency = worker.category_proficiency.get(task.category, 0.2)

        skill_multiplier = 0.85 + 1.2 * (1.0 - proficiency) ** 1.4
        base = task.estimated_minutes * skill_multiplier

        seniority_rank = SENIORITY_RANK[worker.seniority]
        complexity_gap = max(0, task.complexity - (seniority_rank + 1))
        complexity_penalty = 1.0 + complexity_gap * 0.15

        load_ratio = worker.current_load / max(worker.burnout_threshold, 1)
        if load_ratio < 0.5:
            load_penalty = 1.0
        elif load_ratio < 0.8:
            load_penalty = 1.0 + (load_ratio - 0.5) * 0.8
        else:
            load_penalty = 1.3 + (load_ratio - 0.8) * 3.0

        base_time = base * complexity_penalty * load_penalty * worker.base_productivity
        actual = self.noise.sample(base_time, task.complexity, rng)

        block_prob = max(0.0, (task.complexity / 5.0) * (1.0 - proficiency) * 0.3)
        was_blocked = bool(rng.random() < block_prob)
        if was_blocked:
            actual += float(rng.lognormal(mean=math.log(60.0), sigma=0.5))

        return float(actual), was_blocked, proficiency

    @staticmethod
    def _build_row(
        task: SimTask,
        worker: SimWorker,
        load_ratio_at_assignment: float,
        historical_efficiency: float,
        actual_minutes: float,
        efficiency_ratio: float,
        was_blocked: bool,
        sprint_id: int,
        skill_match_score: float,
        arrival_time: float = 0.0,
        completion_time: float = 0.0,
    ) -> dict[str, Any]:
        """Build one dataset row.

        NLP mode (task.embedding is not None): uses skill_match_score and
        is_strong_match; drops the 8 category one-hot columns,
        proficiency_for_task_category, and is_primary_specialisation.

        Legacy mode: retains the original schema with category one-hot columns.
        """
        nlp_mode = task.embedding is not None

        row: dict[str, Any] = {
            # task features
            "complexity": task.complexity,
            "priority_numeric": 6 - task.priority,  # P1 -> 5, P5 -> 1
            "estimated_minutes_norm": min(task.estimated_minutes / 480.0, 1.0),
            "requires_min_seniority": task.requires_min_seniority,
            # worker features
            "seniority_numeric": worker.seniority_numeric(),
            "years_experience_norm": worker.years_experience / 20.0,
            "base_productivity": worker.base_productivity,
            "load_ratio_at_assignment": load_ratio_at_assignment,
            "historical_efficiency": historical_efficiency,
            # target
            "actual_minutes": actual_minutes,
            "efficiency_ratio": efficiency_ratio,
            # metadata (not features)
            "worker_id": worker.id,
            "task_id": task.id,
            "task_category": task.category,
            "was_blocked": was_blocked,
            "sprint_id": sprint_id,
            "arrival_time": arrival_time,
            "completion_time": completion_time,
        }

        if nlp_mode:
            # NLP schema: continuous skill signal replaces discrete category features.
            row["skill_match_score"] = skill_match_score
            row["is_strong_match"] = int(skill_match_score > 0.65)
        else:
            # Legacy schema: 8 one-hot category columns + proficiency columns.
            for c in CANONICAL_CATEGORIES:
                row[f"category_{c}"] = int(task.category == c)
            row["proficiency_for_task_category"] = worker.category_proficiency.get(task.category, 0.0)
            row["is_primary_specialisation"] = int(task.category == worker.primary_category)

        return row
