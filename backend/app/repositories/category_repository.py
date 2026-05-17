from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category


class CategoryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> list[Category]:
        return list(self.db.execute(select(Category).order_by(Category.name.asc())).scalars().all())

    def get_by_id(self, category_id: int) -> Category | None:
        return self.db.get(Category, category_id)

    def get_by_name(self, name: str) -> Category | None:
        return self.db.execute(select(Category).where(Category.name == name)).scalar_one_or_none()
