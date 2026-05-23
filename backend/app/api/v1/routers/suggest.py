"""LangChain-backed suggestion endpoints (Grok API).

All frontend suggestions — category, complexity, tags, workers — go through
here. The embedding-based /recommend endpoint is no longer used by the frontend;
sentence-transformer embeddings are retained for backend worker profile updates only.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permission_service import get_permission_service
from app.core.permissions import Permission
from app.models.user import User
from app.schemas.suggest import (
    CategoryProficiencyResult,
    ComplexityResult,
    CategoryResult,
    TagResult,
    SkillSuggestRequest,
    SkillSuggestResponse,
    SkillsApplyRequest,
    TicketSuggestRequest,
    TicketSuggestResponse,
    WorkerSuggestion,
)
from app.services.suggest_service import SuggestService

ticket_suggest_router = APIRouter(
    prefix="/projects/{project_id}/tickets", tags=["suggest"]
)
skill_suggest_router = APIRouter(prefix="/users/me/skills", tags=["suggest"])


@ticket_suggest_router.post("/suggest", response_model=TicketSuggestResponse)
async def suggest_ticket(
    project_id: int,
    body: TicketSuggestRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TicketSuggestResponse:
    """Concurrent complexity + category + tag + worker suggestion via LangChain/Grok.

    Always returns 200. Any sub-result may be null/empty if the API is unavailable
    or the LLM output failed validation. Workers are scored via the feature-based
    scorer using DB worker profiles — no LLM call required for that section.
    """
    get_permission_service().require(
        current_user.id, Permission.TICKETS_READ, project_id, db
    )
    result = await SuggestService().suggest_for_ticket(
        title=body.title,
        description=body.description,
        project_id=project_id,
        category_ids=body.category_ids,
        complexity=body.complexity,
        db=db,
    )
    return TicketSuggestResponse(
        complexity=(
            ComplexityResult(score=result.complexity.score, reasoning=result.complexity.reasoning)
            if result.complexity else None
        ),
        category=(
            CategoryResult(
                match_id=result.category.match_id,
                match_name=result.category.match_name,
                new_suggestion=result.category.new_suggestion,
                confidence=result.category.confidence,
            ) if result.category else None
        ),
        tags=(
            TagResult(
                suggested_tags=result.tags.suggested_tags,
                new_suggestions=result.tags.new_suggestions,
            ) if result.tags else None
        ),
        workers=[
            WorkerSuggestion(
                user_id=w.user_id,
                username=w.username,
                score=w.score,
                proficiency=w.proficiency,
                load_ratio=w.load_ratio,
                reasons=w.reasons,
            )
            for w in result.workers
        ],
    )


@skill_suggest_router.post("/suggest", response_model=SkillSuggestResponse)
async def suggest_skills(
    body: SkillSuggestRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SkillSuggestResponse:
    """Parse a bio into skills + primary category + seniority hint + per-category
    proficiency estimates. Suggestion only -- nothing is persisted until the user
    confirms in the frontend and the profile is saved."""
    result = await SuggestService().suggest_skills_from_bio(body.bio, db)
    if result.skills is None:
        return SkillSuggestResponse()
    s = result.skills
    return SkillSuggestResponse(
        skills=s.skills,
        primary_category=s.primary_category,
        seniority_hint=s.seniority_hint,
        category_proficiencies=[
            CategoryProficiencyResult(category=cp.category, proficiency=cp.proficiency)
            for cp in (s.category_proficiencies or [])
        ],
    )


@skill_suggest_router.post("/apply", status_code=204)
async def apply_skills(
    body: SkillsApplyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Persist accepted category proficiency scores for the current user.

    Called when the admin clicks Save on the worker profile sheet, after the
    user has reviewed and accepted/rejected the LLM-suggested proficiency chips.
    Only writes rows for categories the frontend explicitly includes.
    """
    from sqlalchemy import select
    from app.models.category import Category
    from app.models.worker_profile import WorkerProfile
    from app.models.worker_skill_profile import WorkerSkillProfile

    wp = db.execute(
        select(WorkerProfile).where(WorkerProfile.user_id == current_user.id)
    ).scalar_one_or_none()
    if wp is None:
        return

    name_to_id = {
        c.name: c.id
        for c in db.execute(
            select(Category).where(
                Category.name.in_([cp.category for cp in body.category_proficiencies])
            )
        ).scalars().all()
    }

    for cp in body.category_proficiencies:
        cat_id = name_to_id.get(cp.category)
        if cat_id is None:
            continue
        sp = db.execute(
            select(WorkerSkillProfile).where(
                WorkerSkillProfile.worker_id == wp.id,
                WorkerSkillProfile.category_id == cat_id,
            )
        ).scalar_one_or_none()
        if sp is None:
            sp = WorkerSkillProfile(
                worker_id=wp.id, category_id=cat_id, proficiency=cp.proficiency
            )
            db.add(sp)
        else:
            sp.proficiency = cp.proficiency

    db.commit()
