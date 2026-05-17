"""SimWorker dataclass — synthetic worker used by the data simulator.

A SimWorker is a pure data object representing one team member during a
simulated sprint. It carries skill, productivity, capacity and current-load
state. The simulator mutates `current_load` (and only `current_load` /
`is_available`) as tasks are assigned and completed.

The 8 canonical categories are imported from this module so all parts of
the simulation share the same one-hot encoding width.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    import numpy as np

# Fixed canonical taxonomy. Never reorder or rename — these define the
# one-hot encoding width used by every downstream model.
CANONICAL_CATEGORIES: tuple[str, ...] = (
    "backend",
    "frontend",
    "devops",
    "design",
    "mobile",
    "data",
    "qa",
    "security",
)

Seniority = Literal["junior", "mid", "senior", "lead"]

SENIORITY_RANK: dict[str, int] = {
    "junior": 0,
    "mid": 1,
    "senior": 2,
    "lead": 3,
}


@dataclass
class SimWorker:
    """Synthetic worker for one simulated sprint."""

    id: int
    seniority: Seniority
    years_experience: int                       # 0–20
    primary_category: str                       # one of CANONICAL_CATEGORIES
    category_proficiency: dict[str, float]      # category -> 0.0–1.0 (all 8 keys)
    base_productivity: float                    # speed multiplier (0.7 = 30% faster)
    burnout_threshold: int                      # max assigned minutes
    current_load: int = 0                       # mutable: minutes of unfinished work
    is_available: bool = True
    # NLP mode field — populated by WorkerGenerator when use_nlp=True.
    embedding: np.ndarray | None = None

    def load_ratio(self) -> float:
        """Fraction of burnout threshold currently in flight."""
        if self.burnout_threshold <= 0:
            return 1.0
        return self.current_load / self.burnout_threshold

    def seniority_numeric(self) -> int:
        """Numeric encoding of seniority (junior=0, lead=3)."""
        return SENIORITY_RANK[self.seniority]
