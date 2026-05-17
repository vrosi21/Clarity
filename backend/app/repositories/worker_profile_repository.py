from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.worker_profile import WorkerProfile
from app.models.worker_skill_profile import WorkerSkillProfile


class WorkerProfileRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, profile_id: int) -> WorkerProfile | None:
        stmt = (
            select(WorkerProfile)
            .options(selectinload(WorkerProfile.skill_profiles))
            .where(WorkerProfile.id == profile_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_user_id(self, user_id: int) -> WorkerProfile | None:
        stmt = (
            select(WorkerProfile)
            .options(selectinload(WorkerProfile.skill_profiles))
            .where(WorkerProfile.user_id == user_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, user_id: int, **fields) -> WorkerProfile:
        profile = WorkerProfile(user_id=user_id, **fields)
        self.db.add(profile)
        self.db.flush()
        return profile

    def update(self, profile: WorkerProfile, **fields) -> WorkerProfile:
        for k, v in fields.items():
            if v is not None:
                setattr(profile, k, v)
        self.db.flush()
        return profile

    def upsert_skill(
        self, worker_id: int, category_id: int, proficiency: float
    ) -> WorkerSkillProfile:
        stmt = select(WorkerSkillProfile).where(
            WorkerSkillProfile.worker_id == worker_id,
            WorkerSkillProfile.category_id == category_id,
        )
        existing = self.db.execute(stmt).scalar_one_or_none()
        if existing is not None:
            existing.proficiency = proficiency
            self.db.flush()
            return existing
        skill = WorkerSkillProfile(
            worker_id=worker_id, category_id=category_id, proficiency=proficiency
        )
        self.db.add(skill)
        self.db.flush()
        return skill
