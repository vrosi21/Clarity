from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.permissions import Permission
from app.models.user import User
from app.schemas.project_settings import (
    CategoryConfigResponse,
    CategoryConfigUpdate,
    ProjectSettingsResponse,
    RoleConstraintResponse,
    RoleConstraintUpdate,
)
from app.services.project_settings_service import ProjectSettingsService

router = APIRouter(
    prefix="/projects/{project_id}/settings", tags=["project-settings"]
)


@router.get("", response_model=ProjectSettingsResponse)
def get_settings(
    project_id: int,
    current_user: Annotated[User, Depends(require_permission(Permission.PROJECTS_READ))],
    db: Annotated[Session, Depends(get_db)],
) -> ProjectSettingsResponse:
    return ProjectSettingsService(db).get_settings(project_id, current_user)


@router.put("/constraints", response_model=RoleConstraintResponse)
def upsert_constraint(
    project_id: int,
    data: RoleConstraintUpdate,
    current_user: Annotated[
        User, Depends(require_permission(Permission.PROJECTS_MANAGE_SETTINGS))
    ],
    db: Annotated[Session, Depends(get_db)],
) -> RoleConstraintResponse:
    return ProjectSettingsService(db).upsert_constraint(project_id, data, current_user)


@router.delete("/constraints/{role_id}", status_code=204)
def delete_constraint(
    project_id: int,
    role_id: int,
    current_user: Annotated[
        User, Depends(require_permission(Permission.PROJECTS_MANAGE_SETTINGS))
    ],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    ProjectSettingsService(db).delete_constraint(project_id, role_id, current_user)


@router.put("/category-configs", response_model=CategoryConfigResponse)
def upsert_category_config(
    project_id: int,
    data: CategoryConfigUpdate,
    current_user: Annotated[
        User, Depends(require_permission(Permission.PROJECTS_MANAGE_SETTINGS))
    ],
    db: Annotated[Session, Depends(get_db)],
) -> CategoryConfigResponse:
    return ProjectSettingsService(db).upsert_category_config(
        project_id, data, current_user
    )
