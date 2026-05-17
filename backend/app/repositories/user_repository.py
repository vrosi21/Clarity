from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.execute(select(User).where(User.email == email)).scalar_one_or_none()

    def exists_by_email(self, email: str) -> bool:
        return self.get_by_email(email) is not None

    def get_by_username(self, username: str) -> User | None:
        return self.db.execute(select(User).where(User.username == username)).scalar_one_or_none()

    def count(self) -> int:
        from sqlalchemy import func, select
        return self.db.execute(select(func.count()).select_from(User)).scalar_one()

    def create(
        self,
        email: str,
        username: str,
        hashed_password: str,
        is_active: bool = True,
    ) -> User:
        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            is_active=is_active,
        )
        self.db.add(user)
        self.db.flush()
        return user
