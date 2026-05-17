from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import TicketLinkType

if TYPE_CHECKING:
    from app.models.ticket import Ticket


class TicketLink(Base):
    __tablename__ = "ticket_links"
    __table_args__ = (UniqueConstraint("source_ticket_id", "target_ticket_id", name="uq_ticket_link_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    target_ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[TicketLinkType] = mapped_column(
        Enum(TicketLinkType, name="ticket_link_type", create_type=False, values_callable=lambda x: [e.value for e in x]), nullable=False, default=TicketLinkType.RELATES_TO
    )

    source_ticket: Mapped[Ticket] = relationship(
        back_populates="source_links", foreign_keys=[source_ticket_id]
    )
    target_ticket: Mapped[Ticket] = relationship(
        back_populates="target_links", foreign_keys=[target_ticket_id]
    )
