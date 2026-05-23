"""
Orchestrates category, complexity, and worker recommendations.
Depends on ABCs -- concrete implementations injected at construction (DIP).
Never throws 5xx -- each recommender failure returns empty results.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.ml.base.recommender import (
    BaseCategoryRecommender,
    BaseComplexityRecommender,
    BaseWorkerScorer,
    CategoryScore,
    ComplexityScore,
    WorkerScore,
)

MIN_HISTORY_FOR_ESTIMATION = 20


@dataclass
class RecommendationResult:
    categories: list[CategoryScore]
    complexity: ComplexityScore | None
    workers: list[WorkerScore]
    has_enough_history: bool
    suggested_new_category: str | None = None


class RecommendationService:
    def __init__(
        self,
        category_recommender: BaseCategoryRecommender,
        complexity_recommender: BaseComplexityRecommender,
        worker_scorer: BaseWorkerScorer,
    ) -> None:
        self._cat = category_recommender
        self._cplx = complexity_recommender
        self._worker = worker_scorer

    def recommend(
        self,
        title: str,
        description: str | None,
        category_ids: list[int],
        category_names: list[str],
        complexity: int | None,
        project_id: int,
        db: Session,
    ) -> RecommendationResult:
        from app.ml.nlp.task_text import task_to_text

        # Plain text for category recommendation -- no hint yet, we don't know the
        # category until the recommender tells us.
        raw_text = f"{title} {description or ''}".strip()

        cats: list[CategoryScore] = []
        try:
            cats = self._cat.recommend(raw_text)
        except Exception:
            pass

        # Effective category names = explicit selection first, then fall back to
        # top NLP suggestion so the complexity heuristic always has something to work with.
        effective_names: list[str] = category_names or (
            [cats[0].category_name] if cats else []
        )

        # Structured text for worker scoring: include ALL selected/inferred category
        # names so the embedding is anchored to the full domain of the ticket.
        # Both sides use task_to_text for consistency.
        category_hint = ", ".join(effective_names) if effective_names else None
        text = task_to_text(title, description, category_hint=category_hint)

        cplx: ComplexityScore | None = None
        try:
            cplx = self._cplx.recommend(text, effective_names)
        except Exception:
            pass

        effective_complexity = complexity if complexity is not None else (cplx.value if cplx else 3)

        workers: list[WorkerScore] = []
        try:
            workers = self._worker.score(
                text=text,
                category_names=effective_names,
                complexity=effective_complexity,
                project_id=project_id,
                db=db,
            )
        except Exception:
            pass

        # Open-set detection: ask the category recommender if the text looks like
        # something none of the existing categories cover well.
        suggested_new: str | None = None
        try:
            if hasattr(self._cat, "suggest_new_name"):
                suggested_new = self._cat.suggest_new_name(raw_text)
        except Exception:
            pass

        return RecommendationResult(
            categories=cats,
            complexity=cplx,
            workers=workers,
            has_enough_history=_check_history(project_id, db),
            suggested_new_category=suggested_new,
        )


def _check_history(project_id: int, db: Session) -> bool:
    from app.models.assignment_record import AssignmentRecord
    from app.models.ticket import Ticket
    from sqlalchemy import func, select

    try:
        count = db.execute(
            select(func.count(AssignmentRecord.id))
            .join(Ticket, Ticket.id == AssignmentRecord.ticket_id)
            .where(
                Ticket.project_id == project_id,
                AssignmentRecord.actual_minutes.is_not(None),
            )
        ).scalar_one()
        return (count or 0) >= MIN_HISTORY_FOR_ESTIMATION
    except Exception:
        return False


def get_recommendation_service(db: Session) -> RecommendationService:
    """Wires concrete implementations. Swap here without touching the service."""
    from app.ml.recommenders.embedding_category_recommender import (
        EmbeddingCategoryRecommender,
    )
    from app.ml.recommenders.feature_worker_scorer import FeatureWorkerScorer
    from app.ml.recommenders.heuristic_complexity_recommender import (
        HeuristicComplexityRecommender,
    )
    from app.core.permission_service import get_permission_service
    from app.models.category import Category
    from sqlalchemy import select

    cats = db.execute(select(Category)).scalars().all()
    cat_id_map = {c.name: c.id for c in cats}

    return RecommendationService(
        category_recommender=EmbeddingCategoryRecommender(cat_id_map),
        complexity_recommender=HeuristicComplexityRecommender(),
        worker_scorer=FeatureWorkerScorer(get_permission_service()),
    )
