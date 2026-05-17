from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permission_service import PermissionService, get_permission_service
from app.core.permissions import Permission
from app.models.enums import RoleScope
from app.models.project_member import ProjectMember
from app.models.role import Role
from app.models.user import User
from app.models.user_org_role import UserOrgRole
from app.repositories.role_repository import RoleRepository
from app.schemas.role import RoleCreate, RoleResponse, RoleUpdate


class RoleService:
    def __init__(
        self, db: Session, perm_svc: PermissionService | None = None
    ) -> None:
        self.db = db
        self.repo = RoleRepository(db)
        self.perm_svc = perm_svc or get_permission_service()

    # ── Helpers ─────────────────────────────────────────────────────────────
    def _to_response(self, role: Role) -> RoleResponse:
        return RoleResponse.model_validate(role)

    def _require_org_manage_roles(self, user: User) -> None:
        self.perm_svc.require(
            user.id, Permission.ORG_MANAGE_ROLES, None, self.db
        )

    def _require_org_manage_users(self, user: User) -> None:
        self.perm_svc.require(
            user.id, Permission.ORG_MANAGE_USERS, None, self.db
        )

    # ── Reads ───────────────────────────────────────────────────────────────
    def list_roles(self, scope_filter: RoleScope | None = None) -> list[RoleResponse]:
        return [self._to_response(r) for r in self.repo.list_all(scope_filter)]

    def get_role(self, role_id: int) -> RoleResponse:
        role = self.repo.get_by_id(role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return self._to_response(role)

    # ── Writes ──────────────────────────────────────────────────────────────
    def create_role(self, data: RoleCreate, current_user: User) -> RoleResponse:
        self._require_org_manage_roles(current_user)
        if self.repo.get_by_name(data.name) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Role name already exists",
            )
        role = Role(
            name=data.name,
            description=data.description,
            scope=data.scope,
            is_builtin=False,
            permissions=list(data.permissions),
        )
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return self._to_response(role)

    def update_role(
        self, role_id: int, data: RoleUpdate, current_user: User
    ) -> RoleResponse:
        self._require_org_manage_roles(current_user)
        role = self.repo.get_by_id(role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        if role.is_builtin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Built-in roles cannot be modified",
            )
        if data.name is not None and data.name != role.name:
            if self.repo.get_by_name(data.name) is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Role name already exists",
                )
            role.name = data.name
        if data.description is not None:
            role.description = data.description
        if data.permissions is not None:
            role.permissions = list(data.permissions)
        self.db.commit()
        self.db.refresh(role)
        return self._to_response(role)

    def delete_role(self, role_id: int, current_user: User) -> None:
        self._require_org_manage_roles(current_user)
        role = self.repo.get_by_id(role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        if role.is_builtin:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Built-in roles cannot be deleted",
            )
        org_use = self.db.execute(
            select(UserOrgRole.user_id).where(UserOrgRole.role_id == role_id).limit(1)
        ).first()
        proj_use = self.db.execute(
            select(ProjectMember.id).where(ProjectMember.role_id == role_id).limit(1)
        ).first()
        if org_use is not None or proj_use is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Role is in use; reassign users before deleting",
            )
        self.db.delete(role)
        self.db.commit()

    def assign_org_role(
        self, user_id: int, role_id: int, current_user: User
    ) -> RoleResponse:
        self._require_org_manage_users(current_user)
        role = self.repo.get_by_id(role_id)
        if role is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        if role.scope == RoleScope.PROJECT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role is not assignable at the org level",
            )
        if role.name == "root_user":
            existing = self.db.execute(
                select(UserOrgRole)
                .join(Role, UserOrgRole.role_id == Role.id)
                .where(Role.name == "root_user")
            ).scalar_one_or_none()
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Root user already exists",
                )
        target = self.db.get(User, user_id)
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        self.repo.assign_org_role(user_id, role_id, current_user.id)
        self.db.commit()
        return self._to_response(role)
