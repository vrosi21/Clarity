from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import RoleScope
from app.models.role import Role
from app.models.user_org_role import UserOrgRole


class RoleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, role_id: int) -> Role | None:
        return self.db.get(Role, role_id)

    def get_by_name(self, name: str) -> Role | None:
        return self.db.execute(
            select(Role).where(Role.name == name)
        ).scalar_one_or_none()

    def list_all(self, scope: RoleScope | None = None) -> list[Role]:
        stmt = select(Role).order_by(Role.id)
        if scope is not None:
            stmt = stmt.where(Role.scope == scope)
        return list(self.db.execute(stmt).scalars().all())

    def get_org_role_for_user(self, user_id: int) -> UserOrgRole | None:
        return self.db.execute(
            select(UserOrgRole).where(UserOrgRole.user_id == user_id)
        ).scalar_one_or_none()

    def assign_org_role(
        self,
        user_id: int,
        role_id: int,
        assigned_by_id: int | None = None,
    ) -> UserOrgRole:
        existing = self.get_org_role_for_user(user_id)
        if existing is None:
            row = UserOrgRole(
                user_id=user_id, role_id=role_id, assigned_by_id=assigned_by_id
            )
            self.db.add(row)
            self.db.flush()
            return row
        existing.role_id = role_id
        existing.assigned_by_id = assigned_by_id
        self.db.flush()
        return existing
