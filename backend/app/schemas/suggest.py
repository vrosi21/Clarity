from pydantic import BaseModel, Field


class TicketSuggestRequest(BaseModel):
    title: str = Field(..., min_length=1)
    description: str | None = None
    category_ids: list[int] = []
    complexity: int | None = None


class ComplexityResult(BaseModel):
    score: int
    reasoning: str


class CategoryResult(BaseModel):
    match_id: int | None = None
    match_name: str | None = None
    new_suggestion: str | None = None
    confidence: float


class TagResult(BaseModel):
    suggested_tags: list[str] = []
    new_suggestions: list[str] = []


class WorkerSuggestion(BaseModel):
    user_id: int
    username: str
    score: float
    proficiency: float
    load_ratio: float
    reasons: list[str]


class TicketSuggestResponse(BaseModel):
    complexity: ComplexityResult | None = None
    category: CategoryResult | None = None
    tags: TagResult | None = None
    workers: list[WorkerSuggestion] = []


class SkillSuggestRequest(BaseModel):
    bio: str = Field(..., min_length=1)


class CategoryProficiencyResult(BaseModel):
    category: str
    proficiency: float


class SkillSuggestResponse(BaseModel):
    skills: list[str] = []
    primary_category: str | None = None
    seniority_hint: str | None = None
    category_proficiencies: list[CategoryProficiencyResult] = []


class SkillsApplyRequest(BaseModel):
    """Sent by the frontend when the admin confirms skills on the worker profile sheet."""
    category_proficiencies: list[CategoryProficiencyResult] = []
