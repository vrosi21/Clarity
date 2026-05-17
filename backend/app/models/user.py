from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.comment import Comment
    from app.models.project_member import ProjectMember
    from app.models.ticket import Ticket
    from app.models.user_org_role import UserOrgRole
    from app.models.worker_profile import WorkerProfile


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    years_experience: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project_memberships: Mapped[list[ProjectMember]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    assigned_tickets: Mapped[list[Ticket]] = relationship(back_populates="assignee")
    comments: Mapped[list[Comment]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    worker_profile: Mapped[WorkerProfile | None] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan", passive_deletes=True
    )
    org_role: Mapped[UserOrgRole | None] = relationship(
        back_populates="user",
        foreign_keys="UserOrgRole.user_id",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
