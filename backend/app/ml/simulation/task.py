"""SimTask dataclass — a synthetic ticket used by the data simulator.

Each SimTask is a pure data object describing one unit of work. The
simulator never mutates a SimTask; it only reads its fields when computing
eligibility and actual_minutes.

`arrival_time` is set by the simulator (not the generator) and represents
the simulated minute at which the task becomes available to be assigned.

`title`, `description`, and `embedding` are populated only in NLP mode
(TaskGenerator.generate(use_nlp=True)). In legacy mode they stay at their
defaults and the simulator falls back to category_proficiency lookup.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np


@dataclass
class SimTask:
    """Synthetic ticket carried through one simulated sprint."""

    id: int
    category: str               # one of CANONICAL_CATEGORIES (soft label in NLP mode)
    complexity: int             # 1–5
    priority: int               # 1 (highest) – 5 (lowest)
    estimated_minutes: int      # PM's estimate
    requires_min_seniority: int  # 0=anyone, 1=mid+, 2=senior+, 3=lead only

    # Set by the simulator when laying out the sprint timeline.
    arrival_time: float = 0.0

    # NLP mode fields — populated by TaskGenerator when use_nlp=True.
    title: str = ""
    description: str = ""
    # Embedding is set by the NLP-aware generator; None in legacy mode.
    embedding: np.ndarray | None = None
