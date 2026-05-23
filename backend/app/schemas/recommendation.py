from pydantic import BaseModel


class RecommendRequest(BaseModel):
    title: str
    description: str | None = None
    # Multiple category IDs — supports multi-category ticket tagging.
    # Empty list means no categories selected yet.
    category_ids: list[int] = []
    complexity: int | None = None


class CategorySuggestion(BaseModel):
    category_id: int
    category_name: str
    confidence: float


class ComplexitySuggestion(BaseModel):
    value: int
    confidence: float
    basis: str  # "heuristic" | "historical" | "heuristic+historical"


class WorkerSuggestion(BaseModel):
    user_id: int
    username: str
    score: float
    proficiency: float
    load_ratio: float
    reasons: list[str]


class RecommendResponse(BaseModel):
    categories: list[CategorySuggestion]
    complexity: ComplexitySuggestion | None
    workers: list[WorkerSuggestion]
    has_enough_history: bool
    # Set when the NLP model doesn't match any existing category well enough.
    # Contains a candidate name extracted from the ticket title.
    # Only visible to users with categories:manage — enforced on the frontend.
    suggested_new_category: str | None = None
