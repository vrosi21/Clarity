from typing import Annotated, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permission_service import PermissionService, get_permission_service
from app.core.permissions import Permission
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")
    return user


def get_perm_service() -> PermissionService:
    return get_permission_service()


def require_permission(
    permission: str, project_id_param: str | None = "project_id"
) -> Callable[..., User]:
    """Returns a FastAPI dependency that checks the effective permission.

    Project id (if any) is extracted from the path under `project_id_param`.
    Pass `project_id_param=None` for purely org-level checks.
    """

    def dep(
        request: Request,
        current_user: Annotated[User, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_db)],
        svc: Annotated[PermissionService, Depends(get_perm_service)],
    ) -> User:
        project_id: int | None = None
        if project_id_param:
            raw = request.path_params.get(project_id_param)
            if raw is not None:
                try:
                    project_id = int(raw)
                except (TypeError, ValueError):
                    project_id = None
        svc.require(current_user.id, permission, project_id, db)
        return current_user

    return dep


def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    svc: Annotated[PermissionService, Depends(get_perm_service)],
) -> User:
    """Org-level admin (or root) — currently keyed on `org:manage_users`."""
    svc.require(
        current_user.id, Permission.ORG_MANAGE_USERS, None, db,
        detail="Admin access required",
    )
    return current_user
