from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.ml.registry import ModelRegistry, get_model_registry
from app.models.user import User
from app.repositories.member_repository import MemberRepository
from app.repositories.ticket_repository import TicketRepository
from app.services.assignment_service import (
    AssignmentService,
    CandidateSuggestion,
)

router = APIRouter(
    prefix="/projects/{project_id}/tickets/{ticket_id}", tags=["assignment"]
)


def _service(db: Session, registry: ModelRegistry) -> AssignmentService:
    return AssignmentService(
        db=db,
        ticket_repo=TicketRepository(db),
        member_repo=MemberRepository(db),
        registry=registry,
    )


class CandidateOut(BaseModel):
    user_id: int
    username: str
    q_value: float | None
    probability: float | None
    proficiency: float
    load_ratio: float


class AssignResponse(BaseModel):
    ticket_id: int
    assigned_user_id: int
    policy_used: str
    q_value: float | None
    suggestions: list[CandidateOut]


def _to_out(s: CandidateSuggestion) -> CandidateOut:
    return CandidateOut(
        user_id=s.user_id,
        username=s.username,
        q_value=s.q_value,
        probability=s.probability,
        proficiency=s.proficiency,
        load_ratio=s.load_ratio,
    )


@router.post("/assign-rl", response_model=AssignResponse)
def assign_rl(
    project_id: int,
    ticket_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    registry: Annotated[ModelRegistry, Depends(get_model_registry)],
) -> AssignResponse:
    result = _service(db, registry).assign(project_id, ticket_id, current_user)
    return AssignResponse(
        ticket_id=result.ticket_id,
        assigned_user_id=result.assigned_user_id,
        policy_used=result.policy_used,
        q_value=result.q_value,
        suggestions=[_to_out(s) for s in result.suggestions],
    )


@router.get("/assignment-suggestions", response_model=list[CandidateOut])
def get_suggestions(
    project_id: int,
    ticket_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    registry: Annotated[ModelRegistry, Depends(get_model_registry)],
) -> list[CandidateOut]:
    return [
        _to_out(s)
        for s in _service(db, registry).suggestions(project_id, ticket_id, current_user)
    ]
