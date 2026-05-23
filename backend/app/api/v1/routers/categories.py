from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permission_service import get_permission_service
from app.core.permissions import Permission
from app.models.user import User
from app.repositories.category_repository import CategoryRepository
from app.schemas.rl_config import CategoryResponse
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64,
                      description="Lowercase slug, e.g. 'devops' or 'machine learning'")
    description: str = Field(default="", max_length=255)


def _svc(db: Session) -> CategoryService:
    return CategoryService(CategoryRepository(db))


@router.get("", response_model=list[CategoryResponse])
def list_categories(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[CategoryResponse]:
    return _svc(db).list_all()


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    body: CategoryCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CategoryResponse:
    """Create a new global category. Requires categories:manage permission."""
    get_permission_service().require(current_user.id, Permission.CATEGORIES_MANAGE, None, db)
    return _svc(db).create(name=body.name, description=body.description)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a category. Requires categories:manage permission."""
    get_permission_service().require(current_user.id, Permission.CATEGORIES_MANAGE, None, db)
    _svc(db).delete(category_id)
