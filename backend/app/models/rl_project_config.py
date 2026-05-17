from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.project import Project


class RLProjectConfig(Base):
    __tablename__ = "rl_project_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    w_priority: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    w_efficiency: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    w_overload: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    w_throughput: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    gamma: Mapped[float] = mapped_column(Float, nullable=False, default=0.95)
    fine_tune_every_n_completions: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    replay_buffer_max_size: Mapped[int] = mapped_column(Integer, nullable=False, default=5000)

    project: Mapped[Project] = relationship()
