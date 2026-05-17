from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.ticket import Ticket
    from app.models.worker_profile import WorkerProfile


class AssignmentRecord(Base):
    __tablename__ = "assignment_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    worker_id: Mapped[int] = mapped_column(
        ForeignKey("worker_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rl_q_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    rl_state_vector: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    ticket: Mapped[Ticket] = relationship()
    worker: Mapped[WorkerProfile] = relationship(back_populates="assignment_records")
