from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.ticket import Ticket
    from app.models.ticket_tag import TicketTag


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    color: Mapped[str | None] = mapped_column(String(32), nullable=True)

    ticket_links: Mapped[list[TicketTag]] = relationship(
        back_populates="tag", cascade="all, delete-orphan", passive_deletes=True
    )
    tickets: Mapped[list[Ticket]] = relationship(secondary="ticket_tags", viewonly=True)
