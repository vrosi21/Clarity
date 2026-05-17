from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import SeniorityLevel

if TYPE_CHECKING:
    from app.models.assignment_record import AssignmentRecord
    from app.models.user import User
    from app.models.worker_skill_profile import WorkerSkillProfile


class WorkerProfile(Base):
    __tablename__ = "worker_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    seniority: Mapped[SeniorityLevel] = mapped_column(
        Enum(SeniorityLevel, name="seniority_level", create_type=False, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    years_experience: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    primary_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    base_productivity: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    burnout_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=2400)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    user: Mapped[User] = relationship(back_populates="worker_profile")
    skill_profiles: Mapped[list[WorkerSkillProfile]] = relationship(
        back_populates="worker", cascade="all, delete-orphan", passive_deletes=True
    )
    assignment_records: Mapped[list[AssignmentRecord]] = relationship(
        back_populates="worker", cascade="all, delete-orphan", passive_deletes=True
    )
