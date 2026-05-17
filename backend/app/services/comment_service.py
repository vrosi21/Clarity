from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.permission_service import PermissionService, get_permission_service
from app.core.permissions import Permission
from app.models.user import User
from app.repositories.comment_repository import CommentRepository
from app.repositories.member_repository import MemberRepository
from app.repositories.ticket_repository import TicketRepository
from app.schemas.comment import CommentCreate, CommentResponse


class CommentService:
    def __init__(
        self,
        comment_repo: CommentRepository,
        ticket_repo: TicketRepository,
        member_repo: MemberRepository,
        perm_svc: PermissionService | None = None,
    ) -> None:
        self.comment_repo = comment_repo
        self.ticket_repo = ticket_repo
        self.member_repo = member_repo
        self.perm_svc = perm_svc or get_permission_service()

    def _ticket_or_404(self, ticket_id: int):
        ticket = self.ticket_repo.get_by_id(ticket_id)
        if ticket is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
        return ticket

    def list_comments(
        self, ticket_id: int, current_user: User, db: Session
    ) -> list[CommentResponse]:
        ticket = self._ticket_or_404(ticket_id)
        self.perm_svc.require(
            current_user.id, Permission.COMMENTS_READ, ticket.project_id, db
        )
        return [
            CommentResponse(
                id=c.id,
                content=c.content,
                user_id=c.user_id,
                username=c.user.username if c.user else None,
                created_at=c.created_at,
                parent_id=c.parent_id,
            )
            for c in self.comment_repo.list_for_ticket(ticket_id)
        ]

    def create_comment(
        self,
        ticket_id: int,
        req: CommentCreate,
        current_user: User,
        db: Session,
    ) -> CommentResponse:
        ticket = self._ticket_or_404(ticket_id)
        self.perm_svc.require(
            current_user.id, Permission.COMMENTS_CREATE, ticket.project_id, db
        )
        comment = self.comment_repo.create(
            ticket_id=ticket_id,
            user_id=current_user.id,
            content=req.content,
            parent_id=req.parent_id,
        )
        db.commit()
        db.refresh(comment)
        return CommentResponse(
            id=comment.id,
            content=comment.content,
            user_id=comment.user_id,
            username=current_user.username,
            created_at=comment.created_at,
            parent_id=comment.parent_id,
        )

    def delete_comment(
        self, ticket_id: int, comment_id: int, current_user: User, db: Session
    ) -> None:
        ticket = self._ticket_or_404(ticket_id)
        comment = self.comment_repo.get_by_id(comment_id)
        if comment is None or comment.ticket_id != ticket_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
        is_own = comment.user_id == current_user.id
        if is_own:
            self.perm_svc.require(
                current_user.id, Permission.COMMENTS_DELETE_OWN, ticket.project_id, db
            )
        else:
            self.perm_svc.require(
                current_user.id, Permission.COMMENTS_DELETE_ANY, ticket.project_id, db
            )
        self.comment_repo.delete(comment)
        db.commit()
