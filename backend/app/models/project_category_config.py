from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.project import Project


class ProjectCategoryConfig(Base):
    __tablename__ = "project_category_configs"
    __table_args__ = (
        UniqueConstraint("project_id", "category_id", name="uq_pcc_project_category"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    min_proficiency: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    allowed_role_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    project: Mapped[Project] = relationship(back_populates="category_configs")
    category: Mapped[Category] = relationship()
