from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.repositories.member_repository import MemberRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.member import MemberAddRequest, MemberResponse, MemberUpdateRequest
from app.services.member_service import MemberService

router = APIRouter(prefix="/projects/{project_id}/members", tags=["members"])


def _service(db: Session) -> MemberService:
    return MemberService(
        MemberRepository(db), UserRepository(db), RoleRepository(db)
    )


@router.get("", response_model=list[MemberResponse])
def list_members(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[MemberResponse]:
    return _service(db).list_members(project_id, current_user, db)


@router.post("", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def add_member(
    project_id: int,
    req: MemberAddRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MemberResponse:
    return _service(db).add_member(project_id, req, current_user, db)


@router.patch("/{user_id}", response_model=MemberResponse)
def update_member_role(
    project_id: int,
    user_id: int,
    req: MemberUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MemberResponse:
    return _service(db).update_member_role(project_id, user_id, req, current_user, db)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    project_id: int,
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    _service(db).remove_member(project_id, user_id, current_user, db)
