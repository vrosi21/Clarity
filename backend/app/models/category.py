from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.ticket import Ticket
    from app.models.worker_skill_profile import WorkerSkillProfile


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str] = mapped_column(String(16), nullable=False, default="#64748b")

    tickets: Mapped[list[Ticket]] = relationship(back_populates="category")
    worker_skill_profiles: Mapped[list[WorkerSkillProfile]] = relationship(
        back_populates="category", cascade="all, delete-orphan", passive_deletes=True
    )
