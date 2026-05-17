from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.permission_service import PermissionService, get_permission_service
from app.core.permissions import Permission
from app.models.enums import RoleScope
from app.models.user import User
from app.repositories.project_settings_repository import ProjectSettingsRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.stage_repository import StageRepository
from app.schemas.project_settings import (
    CategoryConfigResponse,
    CategoryConfigUpdate,
    ProjectSettingsResponse,
    RoleConstraintResponse,
    RoleConstraintUpdate,
)


class ProjectSettingsService:
    def __init__(
        self, db: Session, perm_svc: PermissionService | None = None
    ) -> None:
        self.db = db
        self.repo = ProjectSettingsRepository(db)
        self.role_repo = RoleRepository(db)
        self.stage_repo = StageRepository(db)
        self.perm_svc = perm_svc or get_permission_service()

    # ── Response builders ───────────────────────────────────────────────────
    def _constraint_to_response(self, c) -> RoleConstraintResponse:
        return RoleConstraintResponse(
            id=c.id,
            role_id=c.role_id,
            role_name=c.role.name if c.role else "",
            allowed_transitions=c.allowed_transitions,
            editable_fields=c.editable_fields,
            assignee_only=c.assignee_only,
            view_scope=c.view_scope,
        )

    def _category_to_response(self, c) -> CategoryConfigResponse:
        return CategoryConfigResponse(
            id=c.id,
            category_id=c.category_id,
            category_name=c.category.name if c.category else "",
            min_proficiency=c.min_proficiency,
            allowed_role_ids=c.allowed_role_ids,
        )

    # ── Reads ───────────────────────────────────────────────────────────────
    def get_settings(
        self, project_id: int, current_user: User
    ) -> ProjectSettingsResponse:
        self.perm_svc.require(
            current_user.id, Permission.PROJECTS_READ, project_id, self.db
        )
        constraints = self.repo.get_constraints(project_id)
        cat_configs = self.repo.get_category_configs(project_id)
        return ProjectSettingsResponse(
            role_constraints=[self._constraint_to_response(c) for c in constraints],
            category_configs=[self._category_to_response(c) for c in cat_configs],
        )

    # ── Writes ──────────────────────────────────────────────────────────────
    def upsert_constraint(
        self,
        project_id: int,
        data: RoleConstraintUpdate,
        current_user: User,
    ) -> RoleConstraintResponse:
        self.perm_svc.require(
            current_user.id, Permission.PROJECTS_MANAGE_SETTINGS, project_id, self.db
        )
        role = self.role_repo.get_by_id(data.role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        if role.scope not in (RoleScope.PROJECT, RoleScope.BOTH):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role is not applicable at the project level",
            )
        if data.allowed_transitions is not None:
            stages = self.stage_repo.list_for_project(project_id)
            stage_ids = {s.id for s in stages}
            for pair in data.allowed_transitions:
                if pair[0] not in stage_ids or pair[1] not in stage_ids:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Transition references stage not in project: {pair}",
                    )
        row = self.repo.upsert_constraint(project_id, data)
        self.db.commit()
        self.db.refresh(row)
        return self._constraint_to_response(row)

    def delete_constraint(
        self, project_id: int, role_id: int, current_user: User
    ) -> None:
        self.perm_svc.require(
            current_user.id, Permission.PROJECTS_MANAGE_SETTINGS, project_id, self.db
        )
        if not self.repo.delete_constraint(project_id, role_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Constraint not found"
            )
        self.db.commit()

    def upsert_category_config(
        self,
        project_id: int,
        data: CategoryConfigUpdate,
        current_user: User,
    ) -> CategoryConfigResponse:
        self.perm_svc.require(
            current_user.id, Permission.PROJECTS_MANAGE_SETTINGS, project_id, self.db
        )
        if data.allowed_role_ids is not None:
            for rid in data.allowed_role_ids:
                role = self.role_repo.get_by_id(rid)
                if role is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Role {rid} not found",
                    )
                if role.scope not in (RoleScope.PROJECT, RoleScope.BOTH):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Role {rid} is not applicable at the project level",
                    )
        row = self.repo.upsert_category_config(project_id, data)
        self.db.commit()
        self.db.refresh(row)
        return self._category_to_response(row)
