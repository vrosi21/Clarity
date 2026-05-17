from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.tag import Tag
    from app.models.ticket import Ticket


class TicketTag(Base):
    __tablename__ = "ticket_tags"

    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

    ticket: Mapped[Ticket] = relationship(back_populates="tag_links")
    tag: Mapped[Tag] = relationship(back_populates="ticket_links")
