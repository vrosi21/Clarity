from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permission_service import get_permission_service
from app.core.permissions import Permission
from app.models.category import Category
from app.models.user import User
from app.schemas.recommendation import RecommendRequest, RecommendResponse
from app.services.recommendation_service import get_recommendation_service

router = APIRouter(prefix="/projects/{project_id}/recommend", tags=["recommend"])


@router.post("", response_model=RecommendResponse)
def recommend(
    project_id: int,
    req: RecommendRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RecommendResponse:
    """
    Returns category, complexity, and worker suggestions for a partial ticket.
    Read-only. Safe to call on every keystroke (debounced client-side).
    Never returns 5xx — partial failures yield empty sub-lists.
    """
    get_permission_service().require(
        current_user.id, Permission.TICKETS_READ, project_id, db
    )

    category_names: list[str] = []
    if req.category_ids:
        cats = db.execute(
            select(Category).where(Category.id.in_(req.category_ids))
        ).scalars().all()
        # Preserve the order the client sent.
        id_to_name = {c.id: c.name for c in cats}
        category_names = [id_to_name[cid] for cid in req.category_ids if cid in id_to_name]

    svc = get_recommendation_service(db)
    result = svc.recommend(
        title=req.title,
        description=req.description,
        category_ids=req.category_ids,
        category_names=category_names,
        complexity=req.complexity,
        project_id=project_id,
        db=db,
    )

    return RecommendResponse(
        categories=[
            {"category_id": c.category_id, "category_name": c.category_name,
             "confidence": c.confidence}
            for c in result.categories
        ],
        complexity=(
            {"value": result.complexity.value, "confidence": result.complexity.confidence,
             "basis": result.complexity.basis}
            if result.complexity else None
        ),
        workers=[
            {"user_id": w.user_id, "username": w.username, "score": w.score,
             "proficiency": w.proficiency, "load_ratio": w.load_ratio,
             "reasons": w.reasons}
            for w in result.workers
        ],
        has_enough_history=result.has_enough_history,
        suggested_new_category=result.suggested_new_category,
    )
