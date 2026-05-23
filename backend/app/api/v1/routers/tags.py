from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permission_service import get_permission_service
from app.core.permissions import Permission
from app.models.user import User
from app.repositories.tag_repository import TagRepository
from app.services.tag_service import TagResponse, TagService

router = APIRouter(prefix="/tags", tags=["tags"])


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: str | None = Field(default=None, max_length=32)


def _svc(db: Session) -> TagService:
    return TagService(TagRepository(db))


@router.get("", response_model=list[TagResponse])
def list_tags(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[TagResponse]:
    return _svc(db).list_all()


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def create_tag(
    body: TagCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TagResponse:
    """Create a global tag.

    Spec asked for `projects:manage_members` (project admin+). Tags are global —
    any holder of that permission in *any* project, or the org-level equivalent,
    is allowed. We accept the org-level `CATEGORIES_MANAGE` permission as the
    closest org-level analogue, since both are global vocab management.
    """
    perm_svc = get_permission_service()
    if not perm_svc.has(current_user.id, Permission.CATEGORIES_MANAGE, None, db):
        # Permission denied falls through to explicit 403 with consistent message.
        perm_svc.require(current_user.id, Permission.CATEGORIES_MANAGE, None, db)
    return _svc(db).create(name=body.name, color=body.color)
