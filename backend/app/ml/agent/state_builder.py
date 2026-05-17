"""RL state builder — constructs 17-dim feature vectors for Q-network input.

Each (ticket, worker) candidate pair maps to one state vector. The vector
includes the trained regressor's prediction as feature [13], bridging the
supervised learning stage (notebook 03) into the RL stage so the Q-network
benefits from learned efficiency signal without re-learning it from scratch.

Feature layout (STATE_DIM = 17):
    [0]    complexity_norm        task.complexity / 5.0
    [1]    priority_norm          (6 - task.priority) / 5.0
    [2]    est_minutes_norm       min(estimated / 480, 1.0)
    [3-10] category_onehot        8 binary flags (CANONICAL_CATEGORIES order)
    [11]   proficiency            worker.category_proficiency[task.category]
    [12]   load_ratio             worker.current_load / burnout_threshold
    [13]   predicted_eff_norm     regressor.predict(...) / 4.0, clipped [0,1]
    [14]   is_primary             float(task.category == worker.primary_category)
    [15]   seniority_norm         worker.seniority_numeric() / 3.0
    [16]   base_productivity      worker.base_productivity (~0.7–1.3)
"""

from __future__ import annotations

import numpy as np

from app.ml.base.predictor import BaseEfficiencyPredictor
from app.ml.simulation.task import SimTask
from app.ml.simulation.worker import CANONICAL_CATEGORIES, SimWorker

STATE_DIM: int = 17

# Index of predicted_eff_norm within the RL state vector — used by GreedyPolicy.
IDX_PREDICTED_EFF: int = 13

# Regression model expects 18 features in this order (matches notebook 03 FEATURES).
_N_REG_FEATURES: int = 18  # complexity, priority, est_min, 8 onehot, req_seniority, seniority, yrs_exp, proficiency, productivity, load_ratio, is_primary


def _regression_input(task: SimTask, worker: SimWorker, load_ratio: float) -> np.ndarray:
    """Build the 18-feature input the trained regressor expects."""
    cat_onehot = [float(task.category == c) for c in CANONICAL_CATEGORIES]
    return np.array(
        [
            float(task.complexity),
            float(6 - task.priority),
            min(task.estimated_minutes / 480.0, 1.0),
            *cat_onehot,
            float(task.requires_min_seniority),
            float(worker.seniority_numeric()),
            min(worker.years_experience / 20.0, 1.0),
            worker.category_proficiency.get(task.category, 0.0),
            worker.base_productivity,
            load_ratio,
            float(task.category == worker.primary_category),
        ],
        dtype=float,
    )


def build_state_vector(
    task: SimTask,
    worker: SimWorker,
    regressor: BaseEfficiencyPredictor,
    load_ratio: float | None = None,
) -> np.ndarray:
    """Return a STATE_DIM-dimensional state vector for a (task, worker) pair."""
    if load_ratio is None:
        load_ratio = worker.load_ratio()

    reg_in = _regression_input(task, worker, load_ratio)
    predicted_eff = float(regressor.predict(reg_in.reshape(1, -1))[0])
    predicted_eff_norm = float(np.clip(predicted_eff / 4.0, 0.0, 1.0))

    cat_onehot = [float(task.category == c) for c in CANONICAL_CATEGORIES]
    return np.array(
        [
            task.complexity / 5.0,
            (6 - task.priority) / 5.0,
            min(task.estimated_minutes / 480.0, 1.0),
            *cat_onehot,
            worker.category_proficiency.get(task.category, 0.0),
            load_ratio,
            predicted_eff_norm,
            float(task.category == worker.primary_category),
            worker.seniority_numeric() / 3.0,
            worker.base_productivity,
        ],
        dtype=float,
    )


# ── NLP-mode state builder ──────────────────────────────────────────────────
# Replaces the 8 category one-hots + proficiency + is_primary_specialisation
# (10 dims) with skill_match_score + is_strong_match (2 dims). Also drops the
# implicit category-lookup dependency, so workers and tasks from outside the
# canonical taxonomy are still scored correctly via embedding similarity.

STATE_DIM_NLP: int = 12

# Index of predicted_eff_norm within the NLP state vector — used by GreedyPolicy.
IDX_PREDICTED_EFF_NLP: int = 7

# Same rescaling formula as Simulator._simulate_actual_minutes(); kept here so
# the state builder produces identical skill_match_scores at training time.
_NLP_RESCALE_LO: float = 0.475
_NLP_RESCALE_DENOM: float = 0.055


def _nlp_skill_match_score(worker: SimWorker, task: SimTask) -> float:
    """Compute rescaled skill_match in [0, 1] from worker/task embeddings.

    Falls back to category_proficiency lookup when either embedding is missing —
    matching the Simulator's behaviour so legacy and NLP paths stay aligned.
    """
    if task.embedding is not None and worker.embedding is not None:
        from app.ml.nlp import skill_match as _skill_match
        raw = _skill_match(worker.embedding, task.embedding)
        return float(np.clip((raw - _NLP_RESCALE_LO) / _NLP_RESCALE_DENOM, 0.0, 1.0))
    return worker.category_proficiency.get(task.category, 0.2)


def _regression_input_nlp(
    task: SimTask, worker: SimWorker, load_ratio: float, skill: float
) -> np.ndarray:
    """Build the 10-feature input the NLP-trained regressor expects.

    Order matches notebook 03's training features (excludes historical_efficiency,
    which is mostly NaN at training time and excluded from the fit).
    """
    return np.array(
        [
            float(task.complexity),
            float(6 - task.priority),
            min(task.estimated_minutes / 480.0, 1.0),
            float(task.requires_min_seniority),
            float(worker.seniority_numeric()),
            min(worker.years_experience / 20.0, 1.0),
            skill,
            float(skill > 0.65),
            worker.base_productivity,
            load_ratio,
        ],
        dtype=float,
    )


def build_state_vector_nlp(
    task: SimTask,
    worker: SimWorker,
    regressor: BaseEfficiencyPredictor,
    load_ratio: float | None = None,
) -> np.ndarray:
    """Return a STATE_DIM_NLP-dimensional state vector for a (task, worker) pair.

    Feature layout:
        [0]  complexity_norm
        [1]  priority_norm
        [2]  est_minutes_norm
        [3]  requires_min_seniority_norm
        [4]  seniority_norm
        [5]  years_experience_norm
        [6]  skill_match_score          (replaces 8 one-hots + proficiency)
        [7]  predicted_eff_norm
        [8]  is_strong_match            (replaces is_primary_specialisation)
        [9]  load_ratio
        [10] base_productivity
        [11] task_complexity_x_skill    (interaction term — helps the linear Q-net)
    """
    if load_ratio is None:
        load_ratio = worker.load_ratio()

    skill = _nlp_skill_match_score(worker, task)

    reg_in = _regression_input_nlp(task, worker, load_ratio, skill)
    predicted_eff = float(regressor.predict(reg_in.reshape(1, -1))[0])
    predicted_eff_norm = float(np.clip(predicted_eff / 4.0, 0.0, 1.0))

    return np.array(
        [
            task.complexity / 5.0,
            (6 - task.priority) / 5.0,
            min(task.estimated_minutes / 480.0, 1.0),
            task.requires_min_seniority / 3.0,
            worker.seniority_numeric() / 3.0,
            min(worker.years_experience / 20.0, 1.0),
            skill,
            predicted_eff_norm,
            float(skill > 0.65),
            load_ratio,
            worker.base_productivity,
            (task.complexity / 5.0) * skill,
        ],
        dtype=float,
    )
