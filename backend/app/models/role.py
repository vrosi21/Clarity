from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import RoleScope

if TYPE_CHECKING:
    from app.models.project_member import ProjectMember
    from app.models.project_role_constraint import ProjectRoleConstraint
    from app.models.user_org_role import UserOrgRole


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope: Mapped[RoleScope] = mapped_column(
        Enum(RoleScope, name="role_scope", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    permissions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user_org_roles: Mapped[list[UserOrgRole]] = relationship(back_populates="role")
    project_members: Mapped[list[ProjectMember]] = relationship(back_populates="role")
    project_constraints: Mapped[list[ProjectRoleConstraint]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
