from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.project_category_config import ProjectCategoryConfig
from app.models.project_role_constraint import ProjectRoleConstraint
from app.schemas.project_settings import CategoryConfigUpdate, RoleConstraintUpdate


class ProjectSettingsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Role constraints ────────────────────────────────────────────────────
    def get_constraints(self, project_id: int) -> list[ProjectRoleConstraint]:
        return list(
            self.db.execute(
                select(ProjectRoleConstraint)
                .options(joinedload(ProjectRoleConstraint.role))
                .where(ProjectRoleConstraint.project_id == project_id)
                .order_by(ProjectRoleConstraint.role_id)
            )
            .scalars()
            .all()
        )

    def get_constraint(
        self, project_id: int, role_id: int
    ) -> ProjectRoleConstraint | None:
        return self.db.execute(
            select(ProjectRoleConstraint)
            .options(joinedload(ProjectRoleConstraint.role))
            .where(
                ProjectRoleConstraint.project_id == project_id,
                ProjectRoleConstraint.role_id == role_id,
            )
        ).scalar_one_or_none()

    def upsert_constraint(
        self, project_id: int, data: RoleConstraintUpdate
    ) -> ProjectRoleConstraint:
        existing = self.get_constraint(project_id, data.role_id)
        if existing is None:
            row = ProjectRoleConstraint(
                project_id=project_id,
                role_id=data.role_id,
                allowed_transitions=data.allowed_transitions,
                editable_fields=data.editable_fields,
                assignee_only=data.assignee_only,
                view_scope=data.view_scope,
            )
            self.db.add(row)
            self.db.flush()
            self.db.refresh(row)
            return row
        existing.allowed_transitions = data.allowed_transitions
        existing.editable_fields = data.editable_fields
        existing.assignee_only = data.assignee_only
        existing.view_scope = data.view_scope
        self.db.flush()
        return existing

    def delete_constraint(self, project_id: int, role_id: int) -> bool:
        existing = self.get_constraint(project_id, role_id)
        if existing is None:
            return False
        self.db.delete(existing)
        self.db.flush()
        return True

    # ── Category configs ────────────────────────────────────────────────────
    def get_category_configs(self, project_id: int) -> list[ProjectCategoryConfig]:
        return list(
            self.db.execute(
                select(ProjectCategoryConfig)
                .options(joinedload(ProjectCategoryConfig.category))
                .where(ProjectCategoryConfig.project_id == project_id)
                .order_by(ProjectCategoryConfig.category_id)
            )
            .scalars()
            .all()
        )

    def get_category_config(
        self, project_id: int, category_id: int
    ) -> ProjectCategoryConfig | None:
        return self.db.execute(
            select(ProjectCategoryConfig)
            .options(joinedload(ProjectCategoryConfig.category))
            .where(
                ProjectCategoryConfig.project_id == project_id,
                ProjectCategoryConfig.category_id == category_id,
            )
        ).scalar_one_or_none()

    def upsert_category_config(
        self, project_id: int, data: CategoryConfigUpdate
    ) -> ProjectCategoryConfig:
        existing = self.get_category_config(project_id, data.category_id)
        if existing is None:
            row = ProjectCategoryConfig(
                project_id=project_id,
                category_id=data.category_id,
                min_proficiency=data.min_proficiency,
                allowed_role_ids=data.allowed_role_ids,
            )
            self.db.add(row)
            self.db.flush()
            self.db.refresh(row)
            return row
        existing.min_proficiency = data.min_proficiency
        existing.allowed_role_ids = data.allowed_role_ids
        self.db.flush()
        return existing
