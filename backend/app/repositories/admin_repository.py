from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.role import Role
from app.models.ticket import Ticket
from app.models.user import User
from app.models.user_org_role import UserOrgRole
from app.models.worker_profile import WorkerProfile
from app.models.worker_skill_profile import WorkerSkillProfile
from app.schemas.admin import SkillProfileEntry


class AdminRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all_users(self) -> list[User]:
        return list(
            self.db.execute(select(User).order_by(User.id)).scalars().all()
        )

    def get_user_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def create_user(
        self,
        email: str,
        username: str,
        hashed_password: str,
        full_name: str | None = None,
        years_experience: int = 0,
    ) -> User:
        user = User(
            email=email,
            username=username,
            full_name=full_name,
            years_experience=years_experience,
            hashed_password=hashed_password,
            is_active=True,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def update_user(self, user_id: int, **fields) -> User | None:
        user = self.db.get(User, user_id)
        if user is None:
            return None
        for key, val in fields.items():
            if val is not None:
                setattr(user, key, val)
        self.db.flush()
        return user

    def deactivate_user(self, user_id: int) -> bool:
        user = self.db.get(User, user_id)
        if user is None:
            return False
        user.is_active = False
        self.db.flush()
        return True

    def count_users(self) -> int:
        return self.db.execute(select(func.count()).select_from(User)).scalar_one()

    def get_skill_profiles(self, user_id: int) -> list[WorkerSkillProfile]:
        wp = self.db.execute(
            select(WorkerProfile).where(WorkerProfile.user_id == user_id)
        ).scalar_one_or_none()
        if wp is None:
            return []
        return list(
            self.db.execute(
                select(WorkerSkillProfile).where(WorkerSkillProfile.worker_id == wp.id)
            )
            .scalars()
            .all()
        )

    def set_skill_profiles(
        self, user_id: int, skills: list[SkillProfileEntry]
    ) -> list[WorkerSkillProfile]:
        wp = self.db.execute(
            select(WorkerProfile).where(WorkerProfile.user_id == user_id)
        ).scalar_one_or_none()
        if wp is None:
            return []

        for entry in skills:
            proficiency = float(max(0.0, min(1.0, entry.proficiency)))
            stmt = (
                pg_insert(WorkerSkillProfile)
                .values(
                    worker_id=wp.id,
                    category_id=entry.category_id,
                    proficiency=proficiency,
                )
                .on_conflict_do_update(
                    constraint="uq_worker_skill_profile_pair",
                    set_={"proficiency": proficiency},
                )
            )
            self.db.execute(stmt)
        self.db.flush()

        return list(
            self.db.execute(
                select(WorkerSkillProfile).where(WorkerSkillProfile.worker_id == wp.id)
            )
            .scalars()
            .all()
        )

    def get_dashboard_stats(self) -> dict:
        total_users = self.db.execute(select(func.count()).select_from(User)).scalar_one()
        total_projects = self.db.execute(select(func.count()).select_from(Project)).scalar_one()
        active_tickets = self.db.execute(select(func.count()).select_from(Ticket)).scalar_one()

        role_rows = self.db.execute(
            select(Role.name, func.count(UserOrgRole.user_id).label("cnt"))
            .outerjoin(UserOrgRole, UserOrgRole.role_id == Role.id)
            .group_by(Role.id, Role.name)
            .order_by(Role.name)
        ).all()
        users_by_role = [{"role_name": r.name, "user_count": r.cnt} for r in role_rows]

        workload_rows = self.db.execute(
            select(User.username, func.count(Ticket.id).label("cnt"))
            .outerjoin(Ticket, Ticket.assignee_id == User.id)
            .group_by(User.id, User.username)
            .order_by(func.count(Ticket.id).desc())
        ).all()
        workload_by_user = [
            {"username": r.username, "assigned_ticket_count": r.cnt} for r in workload_rows
        ]

        return {
            "total_users": total_users,
            "total_projects": total_projects,
            "active_tickets": active_tickets,
            "users_by_role": users_by_role,
            "workload_by_user": workload_by_user,
        }
