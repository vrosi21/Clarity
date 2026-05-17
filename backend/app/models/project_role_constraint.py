from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.role import Role


class ProjectRoleConstraint(Base):
    __tablename__ = "project_role_constraints"
    __table_args__ = (UniqueConstraint("project_id", "role_id", name="uq_prc_project_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    allowed_transitions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    editable_fields: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    assignee_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    view_scope: Mapped[str] = mapped_column(String(20), nullable=False, default="all")

    project: Mapped[Project] = relationship(back_populates="role_constraints")
    role: Mapped[Role] = relationship(back_populates="project_constraints")
