from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.ticket import Ticket


class TicketRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _base_query(self):
        return select(Ticket).options(
            joinedload(Ticket.category), joinedload(Ticket.assignee)
        )

    def get_by_id(self, ticket_id: int) -> Ticket | None:
        stmt = self._base_query().where(Ticket.id == ticket_id)
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def list_for_project(
        self, project_id: int, stage_id: int | None = None
    ) -> list[Ticket]:
        stmt = self._base_query().where(Ticket.project_id == project_id)
        if stage_id is not None:
            stmt = stmt.where(Ticket.stage_id == stage_id)
        stmt = stmt.order_by(Ticket.position.asc(), Ticket.id.asc())
        return list(self.db.execute(stmt).unique().scalars().all())

    def list_for_stage(self, stage_id: int) -> list[Ticket]:
        stmt = self._base_query().where(Ticket.stage_id == stage_id).order_by(
            Ticket.position.asc(), Ticket.id.asc()
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def create(self, project_id: int, **fields) -> Ticket:
        ticket = Ticket(project_id=project_id, **fields)
        self.db.add(ticket)
        self.db.flush()
        return ticket

    def update(self, ticket: Ticket, **fields) -> Ticket:
        for k, v in fields.items():
            setattr(ticket, k, v)
        self.db.flush()
        return ticket

    def delete(self, ticket: Ticket) -> None:
        self.db.delete(ticket)
        self.db.flush()

    def move_to_stage(self, ticket: Ticket, stage_id: int) -> Ticket:
        ticket.stage_id = stage_id
        self.db.flush()
        return ticket

    def assign_to_worker(self, ticket: Ticket, user_id: int | None) -> Ticket:
        ticket.assignee_id = user_id
        self.db.flush()
        return ticket
