from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.comment import Comment


class CommentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, comment_id: int) -> Comment | None:
        return self.db.get(Comment, comment_id)

    def list_for_ticket(self, ticket_id: int) -> list[Comment]:
        stmt = (
            select(Comment)
            .options(joinedload(Comment.user))
            .where(Comment.ticket_id == ticket_id)
            .order_by(Comment.created_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(
        self, ticket_id: int, user_id: int, content: str, parent_id: int | None
    ) -> Comment:
        comment = Comment(
            ticket_id=ticket_id, user_id=user_id, content=content, parent_id=parent_id
        )
        self.db.add(comment)
        self.db.flush()
        return comment

    def delete(self, comment: Comment) -> None:
        self.db.delete(comment)
        self.db.flush()
