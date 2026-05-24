from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.fsm import InvalidTransitionError, TaskFSM
from app.core.permission_service import PermissionService, get_permission_service
from app.core.permissions import Permission
from app.models.enums import StageType
from app.models.ticket import Ticket
from app.models.user import User
from app.repositories.member_repository import MemberRepository
from app.repositories.stage_repository import StageRepository
from app.repositories.ticket_repository import TicketRepository
from app.schemas.ticket import TicketCreate, TicketResponse, TicketUpdate


def _to_response(ticket: Ticket) -> TicketResponse:
    return TicketResponse(
        id=ticket.id,
        project_id=ticket.project_id,
        stage_id=ticket.stage_id,
        title=ticket.title,
        description=ticket.description,
        priority=ticket.priority,
        complexity=ticket.complexity,
        category_id=ticket.category_id,
        category_name=ticket.category.name if ticket.category else None,
        category_color=ticket.category.color if ticket.category else None,
        estimated_minutes=ticket.estimated_minutes,
        assignee_id=ticket.assignee_id,
        assignee_username=ticket.assignee.username if ticket.assignee else None,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


class TicketService:
    def __init__(
        self,
        ticket_repo: TicketRepository,
        stage_repo: StageRepository,
        member_repo: MemberRepository,
        perm_svc: PermissionService | None = None,
    ) -> None:
        self.ticket_repo = ticket_repo
        self.stage_repo = stage_repo
        self.member_repo = member_repo
        self.perm_svc = perm_svc or get_permission_service()

    # ------------------------------------------------------------------

    def _validate_stage_in_project(self, stage_id: int, project_id: int) -> None:
        stage = self.stage_repo.get_by_id(stage_id)
        if stage is None or stage.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stage does not belong to this project",
            )

    def _filter_by_view_scope(
        self, tickets: list[Ticket], user_id: int, project_id: int, db: Session
    ) -> list[Ticket]:
        scope = self.perm_svc.get_view_scope(user_id, project_id, db)
        if scope == "assigned":
            return [t for t in tickets if t.assignee_id == user_id]
        return tickets

    def _check_assignee_only(
        self, ticket: Ticket, user_id: int, project_id: int, db: Session
    ) -> None:
        if not self.perm_svc.assignee_only(user_id, project_id, db):
            return
        if ticket.assignee_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Restricted to tickets assigned to you",
            )

    # ------------------------------------------------------------------

    def list_tickets(
        self,
        project_id: int,
        stage_id: int | None,
        current_user: User,
        db: Session,
    ) -> list[TicketResponse]:
        self.perm_svc.require(
            current_user.id, Permission.TICKETS_READ, project_id, db
        )
        tickets = self.ticket_repo.list_for_project(project_id, stage_id)
        tickets = self._filter_by_view_scope(tickets, current_user.id, project_id, db)
        return [_to_response(t) for t in tickets]

    def get_ticket(
        self, project_id: int, ticket_id: int, current_user: User, db: Session
    ) -> TicketResponse:
        self.perm_svc.require(
            current_user.id, Permission.TICKETS_READ, project_id, db
        )
        ticket = self.ticket_repo.get_by_id(ticket_id)
        if ticket is None or ticket.project_id != project_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        scope = self.perm_svc.get_view_scope(current_user.id, project_id, db)
        if scope == "assigned" and ticket.assignee_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        return _to_response(ticket)

    def create_ticket(
        self,
        project_id: int,
        req: TicketCreate,
        current_user: User,
        db: Session,
    ) -> TicketResponse:
        self.perm_svc.require(
            current_user.id, Permission.TICKETS_CREATE, project_id, db
        )
        self._validate_stage_in_project(req.stage_id, project_id)
        ticket = self.ticket_repo.create(
            project_id=project_id,
            stage_id=req.stage_id,
            title=req.title,
            description=req.description,
            priority=req.priority,
            complexity=req.complexity,
            category_id=req.category_id,
            estimated_minutes=req.estimated_minutes,
            assignee_id=req.assignee_id,
        )
        db.commit()
        ticket = self.ticket_repo.get_by_id(ticket.id)
        return _to_response(ticket)

    def update_ticket(
        self,
        project_id: int,
        ticket_id: int,
        req: TicketUpdate,
        current_user: User,
        db: Session,
    ) -> TicketResponse:
        self.perm_svc.require(
            current_user.id, Permission.TICKETS_UPDATE, project_id, db
        )
        ticket = self.ticket_repo.get_by_id(ticket_id)
        if ticket is None or ticket.project_id != project_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        self._check_assignee_only(ticket, current_user.id, project_id, db)

        updates = req.model_dump(exclude_unset=True)

        # Enforce editable_fields constraint, if any.
        allowed = self.perm_svc.get_editable_fields(current_user.id, project_id, db)
        if allowed is not None:
            forbidden = [k for k in updates.keys() if k not in allowed]
            if forbidden:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Fields not editable for your role: {forbidden}",
                )

        if "stage_id" in updates and updates["stage_id"] is not None:
            self._validate_stage_in_project(updates["stage_id"], project_id)

        self.ticket_repo.update(ticket, **updates)
        db.commit()
        ticket = self.ticket_repo.get_by_id(ticket.id)
        return _to_response(ticket)

    def delete_ticket(
        self, project_id: int, ticket_id: int, current_user: User, db: Session
    ) -> None:
        self.perm_svc.require(
            current_user.id, Permission.TICKETS_DELETE, project_id, db
        )
        ticket = self.ticket_repo.get_by_id(ticket_id)
        if ticket is None or ticket.project_id != project_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        self.ticket_repo.delete(ticket)
        db.commit()

    def move_ticket(
        self,
        project_id: int,
        ticket_id: int,
        stage_id: int,
        current_user: User,
        db: Session,
    ) -> TicketResponse:
        ticket = self.ticket_repo.get_by_id(ticket_id)
        if ticket is None or ticket.project_id != project_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        self._check_assignee_only(ticket, current_user.id, project_id, db)
        self._validate_stage_in_project(stage_id, project_id)

        # Permission + per-project transition gate.
        if not self.perm_svc.can_transition(
            current_user.id, project_id, ticket.stage_id, stage_id, db
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role cannot perform this stage transition",
            )

        stages = self.stage_repo.list_for_project(project_id)
        if self._is_fsm_configured(stages):
            try:
                TaskFSM(stages).validate(ticket.stage_id, stage_id)
            except InvalidTransitionError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
                )

        dest_stage = self.stage_repo.get_by_id(stage_id)
        self.ticket_repo.move_to_stage(ticket, stage_id)
        db.commit()
        ticket = self.ticket_repo.get_by_id(ticket.id)
        if dest_stage and dest_stage.type == StageType.FINAL:
            _update_worker_nlp_embedding(ticket, db)
        return _to_response(ticket)

    @staticmethod
    def _is_fsm_configured(stages: list) -> bool:
        types = {s.type for s in stages if s.type is not None}
        return StageType.START in types and StageType.FINAL in types

    def assign_ticket(
        self,
        project_id: int,
        ticket_id: int,
        assignee_user_id: int | None,
        current_user: User,
        db: Session,
    ) -> TicketResponse:
        self.perm_svc.require(
            current_user.id, Permission.TICKETS_ASSIGN, project_id, db
        )
        ticket = self.ticket_repo.get_by_id(ticket_id)
        if ticket is None or ticket.project_id != project_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        if assignee_user_id is not None:
            membership = self.member_repo.get_membership(project_id, assignee_user_id)
            if membership is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Assignee is not a project member",
                )
            # Require the candidate to have tickets:be_assigned (worker-eligible).
            if not self.perm_svc.has(
                assignee_user_id, Permission.TICKETS_BE_ASSIGNED, project_id, db
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Assignee's role cannot receive assignments",
                )
        self.ticket_repo.assign_to_worker(ticket, assignee_user_id)
        db.commit()
        ticket = self.ticket_repo.get_by_id(ticket.id)
        return _to_response(ticket)


def _update_worker_nlp_embedding(ticket: Ticket, db: Session) -> None:
    """
    Called after a ticket reaches a FINAL stage.
    Recomputes worker's nlp_embedding for the ticket's category by averaging
    embeddings of their recent completed tickets in that category.
    Never raises — embedding failure must not block ticket movement.
    """
    if ticket.assignee_id is None or ticket.category_id is None:
        return
    try:
        from app.ml.recommenders.embedding_category_recommender import (
            EmbeddingCategoryRecommender,
        )
        enc = EmbeddingCategoryRecommender._encoder
        if enc is None:
            return

        import numpy as np
        from sqlalchemy import select as sa_select
        from app.ml.nlp.task_text import task_to_text
        from app.models.category import Category

        # Resolve category name so task_to_text can anchor the embedding —
        # must match the format used by the worker scorer at query time.
        cat_row = db.execute(
            sa_select(Category).where(Category.id == ticket.category_id)
        ).scalar_one_or_none()
        category_hint = cat_row.name if cat_row else None

        recent = db.execute(
            sa_select(Ticket.title, Ticket.description)
            .where(
                Ticket.assignee_id == ticket.assignee_id,
                Ticket.category_id == ticket.category_id,
                Ticket.id != ticket.id,
            )
            .order_by(Ticket.updated_at.desc())
            .limit(19)
        ).all()

        texts = [task_to_text(ticket.title, ticket.description, category_hint=category_hint)]
        for t_title, t_desc in recent:
            texts.append(task_to_text(t_title, t_desc, category_hint=category_hint))

        from app.models.worker_profile import WorkerProfile
        from app.models.worker_skill_profile import WorkerSkillProfile

        wp = db.execute(
            sa_select(WorkerProfile).where(WorkerProfile.user_id == ticket.assignee_id)
        ).scalar_one_or_none()
        if wp is None:
            return

        sp = db.execute(
            sa_select(WorkerSkillProfile).where(
                WorkerSkillProfile.worker_id == wp.id,
                WorkerSkillProfile.category_id == ticket.category_id,
            )
        ).scalar_one_or_none()
        if sp is None:
            return

        embs = enc.encode(texts)
        avg_emb = embs.mean(axis=0)
        norm = np.linalg.norm(avg_emb)
        avg_emb = avg_emb / max(norm, 1e-8)

        sp.nlp_embedding = avg_emb.tolist()
        sp.nlp_ticket_count = len(texts)
        db.flush()
    except Exception:
        pass
