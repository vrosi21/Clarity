from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import TicketPriority

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.comment import Comment
    from app.models.project import Project
    from app.models.stage import Stage
    from app.models.tag import Tag
    from app.models.ticket_link import TicketLink
    from app.models.ticket_tag import TicketTag
    from app.models.user import User


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (CheckConstraint("complexity BETWEEN 1 AND 5", name="ck_ticket_complexity"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False)
    stage_id: Mapped[int] = mapped_column(ForeignKey("stages.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, name="ticket_priority", create_type=False, values_callable=lambda x: [e.value for e in x]), nullable=False, default=TicketPriority.P3
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), index=True, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # RL fields: complexity = how hard the task is (1-5); separate from priority (urgency)
    # category_id FK references categories.id — create Category model (roadmap step 6) before migrating
    complexity: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), index=True, nullable=True
    )
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    spent_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    project: Mapped[Project] = relationship(back_populates="tickets")
    stage: Mapped[Stage] = relationship(back_populates="tickets")
    assignee: Mapped[User | None] = relationship(back_populates="assigned_tickets")
    category: Mapped[Category | None] = relationship(back_populates="tickets")

    parent: Mapped[Ticket | None] = relationship(
        "Ticket", remote_side="Ticket.id", back_populates="children", foreign_keys=[parent_id]
    )
    children: Mapped[list[Ticket]] = relationship(
        "Ticket", back_populates="parent", cascade="all, delete-orphan", passive_deletes=True
    )

    source_links: Mapped[list[TicketLink]] = relationship(
        back_populates="source_ticket",
        foreign_keys="TicketLink.source_ticket_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    target_links: Mapped[list[TicketLink]] = relationship(
        back_populates="target_ticket",
        foreign_keys="TicketLink.target_ticket_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    tag_links: Mapped[list[TicketTag]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", passive_deletes=True
    )
    tags: Mapped[list[Tag]] = relationship(secondary="ticket_tags", viewonly=True)

    comments: Mapped[list[Comment]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", passive_deletes=True
    )
