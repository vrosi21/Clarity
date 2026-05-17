from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.repositories.member_repository import MemberRepository
from app.repositories.stage_repository import StageRepository
from app.repositories.ticket_repository import TicketRepository
from app.schemas.ticket import (
    TicketCreate,
    TicketMoveRequest,
    TicketResponse,
    TicketUpdate,
)
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/projects/{project_id}/tickets", tags=["tickets"])


def _service(db: Session) -> TicketService:
    return TicketService(
        TicketRepository(db), StageRepository(db), MemberRepository(db)
    )


@router.get("", response_model=list[TicketResponse])
def list_tickets(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    stage_id: Annotated[int | None, Query()] = None,
) -> list[TicketResponse]:
    return _service(db).list_tickets(project_id, stage_id, current_user, db)


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    project_id: int,
    req: TicketCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TicketResponse:
    return _service(db).create_ticket(project_id, req, current_user, db)


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    project_id: int,
    ticket_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TicketResponse:
    return _service(db).get_ticket(project_id, ticket_id, current_user, db)


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    project_id: int,
    ticket_id: int,
    req: TicketUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TicketResponse:
    return _service(db).update_ticket(project_id, ticket_id, req, current_user, db)


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(
    project_id: int,
    ticket_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    _service(db).delete_ticket(project_id, ticket_id, current_user, db)


@router.post("/{ticket_id}/move", response_model=TicketResponse)
def move_ticket(
    project_id: int,
    ticket_id: int,
    req: TicketMoveRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TicketResponse:
    return _service(db).move_ticket(project_id, ticket_id, req.stage_id, current_user, db)
