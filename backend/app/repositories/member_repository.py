from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.project_member import ProjectMember
from app.models.role import Role


class MemberRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_membership(self, project_id: int, user_id: int) -> ProjectMember | None:
        stmt = (
            select(ProjectMember)
            .options(joinedload(ProjectMember.role))
            .where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_members(self, project_id: int) -> list[ProjectMember]:
        stmt = (
            select(ProjectMember)
            .options(joinedload(ProjectMember.user), joinedload(ProjectMember.role))
            .where(ProjectMember.project_id == project_id)
        )
        return list(self.db.execute(stmt).scalars().all())

    def add_member(self, project_id: int, user_id: int, role_id: int) -> ProjectMember:
        member = ProjectMember(
            project_id=project_id, user_id=user_id, role_id=role_id
        )
        self.db.add(member)
        self.db.flush()
        self.db.refresh(member)
        # Eager-load role for response serialization.
        _ = member.role
        return member

    def update_role(self, member: ProjectMember, role_id: int) -> ProjectMember:
        member.role_id = role_id
        self.db.flush()
        self.db.refresh(member)
        _ = member.role
        return member

    def remove_member(self, member: ProjectMember) -> None:
        self.db.delete(member)
        self.db.flush()

    def get_user_role_in_project(
        self, project_id: int, user_id: int
    ) -> Role | None:
        m = self.get_membership(project_id, user_id)
        return m.role if m else None

    def list_members_with_perm(self, project_id: int, permission: str) -> list[ProjectMember]:
        """Return members whose role permission list contains the given permission."""
        stmt = (
            select(ProjectMember)
            .options(joinedload(ProjectMember.user), joinedload(ProjectMember.role))
            .join(Role, Role.id == ProjectMember.role_id)
            .where(
                ProjectMember.project_id == project_id,
                Role.permissions.contains([permission]),
            )
        )
        return list(self.db.execute(stmt).scalars().all())
