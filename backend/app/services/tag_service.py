from __future__ import annotations

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict

from app.repositories.tag_repository import TagRepository


class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str | None = None


class TagService:
    def __init__(self, tag_repo: TagRepository) -> None:
        self.tag_repo = tag_repo

    def list_all(self) -> list[TagResponse]:
        return [TagResponse.model_validate(t) for t in self.tag_repo.list_all()]

    def create(self, name: str, color: str | None = None) -> TagResponse:
        name = name.strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Tag name cannot be empty.",
            )
        if len(name) > 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Tag name must be 100 characters or fewer.",
            )
        if self.tag_repo.get_by_name(name) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Tag '{name}' already exists.",
            )
        tag = self.tag_repo.create(name=name, color=color)
        return TagResponse.model_validate(tag)
