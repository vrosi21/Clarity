"""Semantic skill-match score between a worker embedding and a task embedding.

Single Responsibility: one function, one number.

This replaces the lookup:
    worker.category_proficiency.get(task.category, 0.2)
with a continuous cosine similarity in [0, 1] computed in embedding space.
"""
from __future__ import annotations

import numpy as np


def skill_match(worker_emb: np.ndarray, task_emb: np.ndarray) -> float:
    """Return a float in [0, 1] representing semantic skill-task alignment.

    0 = completely orthogonal / mismatched.
    1 = perfect semantic alignment.

    Cosine similarity is rescaled from [-1, 1] to [0, 1] so the output is
    directly substitutable for a proficiency score (which also lives in [0, 1]).
    A tiny epsilon in the denominator prevents division by zero on zero vectors.
    """
    w = worker_emb / (np.linalg.norm(worker_emb) + 1e-9)
    t = task_emb / (np.linalg.norm(task_emb) + 1e-9)
    cosine = float(np.dot(w, t))       # in [-1, 1]
    return (cosine + 1.0) / 2.0        # rescale to [0, 1]
