from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.synthetic_team import SyntheticTeam
    from app.models.user import User


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    team_source: Mapped[str] = mapped_column(String(20), nullable=False)  # "project" | "synthetic"
    synthetic_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("synthetic_teams.id", ondelete="SET NULL"), nullable=True, index=True
    )
    rl_config_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    event_log: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")  # "completed" | "failed"

    project: Mapped[Project] = relationship(foreign_keys=[project_id])
    creator: Mapped[User] = relationship(foreign_keys=[created_by])
    synthetic_team: Mapped[SyntheticTeam | None] = relationship(foreign_keys=[synthetic_team_id])
