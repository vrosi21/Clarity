from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.permissions import Permission
from app.models.enums import RoleScope
from app.models.user import User
from app.schemas.role import (
    AssignOrgRoleRequest,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
)
from app.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[RoleResponse])
def list_roles(
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    scope: RoleScope | None = Query(default=None),
) -> list[RoleResponse]:
    return RoleService(db).list_roles(scope)


@router.get("/{role_id}", response_model=RoleResponse)
def get_role(
    role_id: int,
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RoleResponse:
    return RoleService(db).get_role(role_id)


@router.post("", response_model=RoleResponse, status_code=201)
def create_role(
    data: RoleCreate,
    current_user: Annotated[
        User, Depends(require_permission(Permission.ORG_MANAGE_ROLES, project_id_param=None))
    ],
    db: Annotated[Session, Depends(get_db)],
) -> RoleResponse:
    return RoleService(db).create_role(data, current_user)


@router.patch("/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    data: RoleUpdate,
    current_user: Annotated[
        User, Depends(require_permission(Permission.ORG_MANAGE_ROLES, project_id_param=None))
    ],
    db: Annotated[Session, Depends(get_db)],
) -> RoleResponse:
    return RoleService(db).update_role(role_id, data, current_user)


@router.delete("/{role_id}", status_code=204)
def delete_role(
    role_id: int,
    current_user: Annotated[
        User, Depends(require_permission(Permission.ORG_MANAGE_ROLES, project_id_param=None))
    ],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    RoleService(db).delete_role(role_id, current_user)


@router.put("/assign/{user_id}", response_model=RoleResponse)
def assign_org_role(
    user_id: int,
    data: AssignOrgRoleRequest,
    current_user: Annotated[
        User, Depends(require_permission(Permission.ORG_MANAGE_USERS, project_id_param=None))
    ],
    db: Annotated[Session, Depends(get_db)],
) -> RoleResponse:
    return RoleService(db).assign_org_role(user_id, data.role_id, current_user)
