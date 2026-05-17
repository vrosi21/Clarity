from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.worker_profile import WorkerProfile


class WorkerSkillProfile(Base):
    __tablename__ = "worker_skill_profiles"
    __table_args__ = (
        UniqueConstraint("worker_id", "category_id", name="uq_worker_skill_profile_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    worker_id: Mapped[int] = mapped_column(
        ForeignKey("worker_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    proficiency: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    efficiency: Mapped[float | None] = mapped_column(Float, nullable=True)
    nlp_embedding: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    nlp_ticket_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )

    worker: Mapped[WorkerProfile] = relationship(back_populates="skill_profiles")
    category: Mapped[Category] = relationship(back_populates="worker_skill_profiles")
