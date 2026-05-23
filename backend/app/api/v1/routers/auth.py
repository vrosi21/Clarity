from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, SelfUpdate, TokenResponse, UserResponse
from app.services.auth_service import AuthService


class UserSearchResult(BaseModel):
    id: int
    username: str
    email: str
    full_name: str | None

router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])


def _service(db: Session) -> AuthService:
    return AuthService(UserRepository(db))


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    return _service(db).login(req, db)


@router.get("/me", response_model=UserResponse)
def me(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    return _service(db).to_response(current_user, db)


@users_router.get("/search", response_model=list[UserSearchResult])
def search_users(
    q: Annotated[str, Query(min_length=1, max_length=100)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[UserSearchResult]:
    users = UserRepository(db).search(q)
    return [
        UserSearchResult(id=u.id, username=u.username, email=u.email, full_name=u.full_name)
        for u in users
    ]


@users_router.patch("/me", response_model=UserResponse)
def update_me(
    data: SelfUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    svc = _service(db)
    user = svc.update_self(current_user, data, db)
    return svc.to_response(user, db)
