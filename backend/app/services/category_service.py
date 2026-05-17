from app.repositories.category_repository import CategoryRepository
from app.schemas.rl_config import CategoryResponse


class CategoryService:
    def __init__(self, category_repo: CategoryRepository) -> None:
        self.category_repo = category_repo

    def list_all(self) -> list[CategoryResponse]:
        return [CategoryResponse.model_validate(c) for c in self.category_repo.list_all()]
