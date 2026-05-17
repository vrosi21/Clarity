from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import StageType

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.ticket import Ticket


class Stage(Base):
    __tablename__ = "stages"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[StageType | None] = mapped_column(Enum(StageType, name="stage_type", create_type=False, values_callable=lambda x: [e.value for e in x]), nullable=True)
    color: Mapped[str | None] = mapped_column(String(32), nullable=True)

    project: Mapped[Project] = relationship(back_populates="stages")
    tickets: Mapped[list[Ticket]] = relationship(
        back_populates="stage", cascade="all, delete-orphan", passive_deletes=True
    )
