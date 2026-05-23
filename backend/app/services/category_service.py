from fastapi import HTTPException, status

from app.repositories.category_repository import CategoryRepository
from app.schemas.rl_config import CategoryResponse


class CategoryService:
    def __init__(self, category_repo: CategoryRepository) -> None:
        self.category_repo = category_repo

    def list_all(self) -> list[CategoryResponse]:
        return [CategoryResponse.model_validate(c) for c in self.category_repo.list_all()]

    def create(self, name: str, description: str) -> CategoryResponse:
        name = name.lower().strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="Category name cannot be empty.")
        if len(name) > 64:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail="Category name must be 64 characters or fewer.")
        if self.category_repo.get_by_name(name) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"Category '{name}' already exists.")
        cat = self.category_repo.create(name=name, description=description)
        return CategoryResponse.model_validate(cat)

    def delete(self, category_id: int) -> None:
        cat = self.category_repo.get_by_id(category_id)
        if cat is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Category not found.")
        self.category_repo.delete(cat)
