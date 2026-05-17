"""SOLID permission resolution.

- SRP : each resolver handles one permission source.
- OCP : new sources = new resolver class, no existing changes.
- LSP : any BasePermissionResolver is substitutable.
- ISP : resolvers expose only resolve().
- DIP : PermissionService depends on the abstract base, not concrete classes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.permissions import Permission
from app.models.project_member import ProjectMember
from app.models.project_role_constraint import ProjectRoleConstraint
from app.models.user_org_role import UserOrgRole


class BasePermissionResolver(ABC):
    @abstractmethod
    def resolve(
        self, user_id: int, project_id: int | None, db: Session
    ) -> frozenset[str]:
        """Permissions contributed by this resolver."""


class OrgPermissionResolver(BasePermissionResolver):
    """Permissions granted by the user's org-level role."""

    def resolve(
        self, user_id: int, project_id: int | None, db: Session
    ) -> frozenset[str]:
        row = db.execute(
            select(UserOrgRole)
            .options(joinedload(UserOrgRole.role))
            .where(UserOrgRole.user_id == user_id)
        ).scalar_one_or_none()
        if row is None or row.role is None:
            return frozenset()
        return frozenset(row.role.permissions or [])


class ProjectPermissionResolver(BasePermissionResolver):
    """Permissions granted by the user's project-level role membership."""

    def resolve(
        self, user_id: int, project_id: int | None, db: Session
    ) -> frozenset[str]:
        if project_id is None:
            return frozenset()
        row = db.execute(
            select(ProjectMember)
            .options(joinedload(ProjectMember.role))
            .where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        ).scalar_one_or_none()
        if row is None or row.role is None:
            return frozenset()
        return frozenset(row.role.permissions or [])


class PermissionService:
    """Aggregates resolver chain. Org permissions always included."""

    def __init__(self, resolvers: list[BasePermissionResolver]) -> None:
        self._resolvers = resolvers

    def get_effective(
        self, user_id: int, project_id: int | None, db: Session
    ) -> frozenset[str]:
        result: set[str] = set()
        for r in self._resolvers:
            result |= r.resolve(user_id, project_id, db)
        return frozenset(result)

    def has(
        self, user_id: int, permission: str, project_id: int | None, db: Session
    ) -> bool:
        return permission in self.get_effective(user_id, project_id, db)

    def require(
        self,
        user_id: int,
        permission: str,
        project_id: int | None,
        db: Session,
        detail: str = "Insufficient permissions",
    ) -> None:
        if not self.has(user_id, permission, project_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=detail
            )

    def _get_constraint(
        self, user_id: int, project_id: int, db: Session
    ) -> tuple[ProjectMember | None, ProjectRoleConstraint | None]:
        membership = db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        ).scalar_one_or_none()
        if membership is None:
            return None, None
        constraint = db.execute(
            select(ProjectRoleConstraint).where(
                ProjectRoleConstraint.project_id == project_id,
                ProjectRoleConstraint.role_id == membership.role_id,
            )
        ).scalar_one_or_none()
        return membership, constraint

    def can_transition(
        self,
        user_id: int,
        project_id: int,
        from_stage_id: int,
        to_stage_id: int,
        db: Session,
    ) -> bool:
        if not self.has(user_id, Permission.TICKETS_MOVE, project_id, db):
            return False
        membership, constraint = self._get_constraint(user_id, project_id, db)
        if membership is None:
            # Org-level permission with no membership: allow.
            return True
        if constraint is None or constraint.allowed_transitions is None:
            return True
        return [from_stage_id, to_stage_id] in constraint.allowed_transitions

    def get_view_scope(
        self, user_id: int, project_id: int, db: Session
    ) -> str:
        _, constraint = self._get_constraint(user_id, project_id, db)
        if constraint is None:
            return "all"
        return constraint.view_scope

    def get_editable_fields(
        self, user_id: int, project_id: int, db: Session
    ) -> list[str] | None:
        _, constraint = self._get_constraint(user_id, project_id, db)
        if constraint is None:
            return None
        return constraint.editable_fields

    def assignee_only(
        self, user_id: int, project_id: int, db: Session
    ) -> bool:
        _, constraint = self._get_constraint(user_id, project_id, db)
        if constraint is None:
            return False
        return bool(constraint.assignee_only)


def get_permission_service() -> PermissionService:
    """Dependency factory — wire concretions in one place (DI)."""
    return PermissionService([OrgPermissionResolver(), ProjectPermissionResolver()])
