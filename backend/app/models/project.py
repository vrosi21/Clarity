from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.project_category_config import ProjectCategoryConfig
    from app.models.project_member import ProjectMember
    from app.models.project_role_constraint import ProjectRoleConstraint
    from app.models.stage import Stage
    from app.models.ticket import Ticket
    from app.models.user import User


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    created_by: Mapped[User | None] = relationship(foreign_keys=[created_by_id])
    members: Mapped[list[ProjectMember]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    stages: Mapped[list[Stage]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    tickets: Mapped[list[Ticket]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    role_constraints: Mapped[list[ProjectRoleConstraint]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    category_configs: Mapped[list[ProjectCategoryConfig]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
