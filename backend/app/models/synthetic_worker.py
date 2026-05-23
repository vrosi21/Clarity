from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.synthetic_team import SyntheticTeam


class SyntheticWorker(Base):
    __tablename__ = "synthetic_workers"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("synthetic_teams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    seniority: Mapped[str] = mapped_column(String(20), nullable=False)  # junior/mid/senior/lead
    years_experience: Mapped[float] = mapped_column(Float, nullable=False)
    primary_category: Mapped[str] = mapped_column(String(100), nullable=False)
    category_proficiency: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    base_productivity: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    burnout_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=2400)

    team: Mapped[SyntheticTeam] = relationship(back_populates="workers")
