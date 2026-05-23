from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.tag import Tag


class TagRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> list[Tag]:
        return list(
            self.db.execute(select(Tag).order_by(Tag.name.asc())).scalars().all()
        )

    def get_by_name(self, name: str) -> Tag | None:
        return self.db.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none()

    def create(self, name: str, color: str | None = None) -> Tag:
        tag = Tag(name=name.strip(), color=color)
        self.db.add(tag)
        self.db.commit()
        self.db.refresh(tag)
        return tag
