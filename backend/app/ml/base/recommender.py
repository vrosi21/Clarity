"""Abstract interfaces for the recommendation layer.

SRP  : each ABC covers exactly one recommendation concern.
OCP  : new strategies = new subclass, zero existing changes.
LSP  : concrete classes are drop-in substitutes.
ISP  : each ABC exposes only what its consumer needs.
DIP  : RecommendationService depends on these ABCs, not concrete classes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class CategoryScore:
    category_id: int
    category_name: str
    confidence: float  # 0.0 – 1.0


@dataclass
class ComplexityScore:
    value: int         # 1–5
    confidence: float  # 0.0 – 1.0
    basis: str         # "heuristic" | "historical" | "heuristic+historical"


@dataclass
class WorkerScore:
    user_id: int
    username: str
    score: float       # 0.0 – 1.0 (normalised)
    proficiency: float
    load_ratio: float
    reasons: list[str] = field(default_factory=list)


class BaseCategoryRecommender(ABC):
    @abstractmethod
    def recommend(self, text: str, top_k: int = 3) -> list[CategoryScore]:
        """Return top_k categories ranked by relevance to text."""


class BaseComplexityRecommender(ABC):
    @abstractmethod
    def recommend(
        self,
        text: str,
        category_names: list[str] | None = None,
    ) -> ComplexityScore:
        """Return a story-points suggestion for the given ticket text.

        category_names — all categories selected for this ticket (may be empty).
        When multiple categories are provided, implementations should average or
        otherwise aggregate their priors.
        """


class BaseWorkerScorer(ABC):
    @abstractmethod
    def score(
        self,
        text: str,
        category_names: list[str],
        complexity: int,
        project_id: int,
        db,
    ) -> list[WorkerScore]:
        """Return eligible workers ranked by suitability for this ticket.

        category_names — all selected categories; workers are scored against
        the full set.  The first entry is treated as the primary category for
        eligibility gates (min_proficiency, allowed_role_ids).
        """
