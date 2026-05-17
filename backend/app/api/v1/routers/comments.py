from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.repositories.comment_repository import CommentRepository
from app.repositories.member_repository import MemberRepository
from app.repositories.ticket_repository import TicketRepository
from app.schemas.comment import CommentCreate, CommentResponse
from app.services.comment_service import CommentService

router = APIRouter(prefix="/tickets/{ticket_id}/comments", tags=["comments"])


def _service(db: Session) -> CommentService:
    return CommentService(
        CommentRepository(db), TicketRepository(db), MemberRepository(db)
    )


@router.get("", response_model=list[CommentResponse])
def list_comments(
    ticket_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[CommentResponse]:
    return _service(db).list_comments(ticket_id, current_user, db)


@router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(
    ticket_id: int,
    req: CommentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CommentResponse:
    return _service(db).create_comment(ticket_id, req, current_user, db)


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    ticket_id: int,
    comment_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    _service(db).delete_comment(ticket_id, comment_id, current_user, db)
