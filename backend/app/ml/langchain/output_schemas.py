"""Pydantic schemas consumed by LangChain PydanticOutputParser.

Each shape is the strict contract the LLM must conform to. JSON mode + the
parser's format instructions make Ollama emit valid output the vast majority of
the time; the calling function still wraps everything in try/except.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ComplexityOutput(BaseModel):
    score: int = Field(ge=1, le=5, description="Complexity 1 (trivial) to 5 (very complex)")
    reasoning: str = Field(description="One-sentence explanation")


class CategoryOutput(BaseModel):
    match_id: int | None = Field(default=None, description="ID of best existing match, or null")
    match_name: str | None = Field(default=None)
    new_suggestion: str | None = Field(
        default=None, description="Proposed new category name when nothing fits"
    )
    confidence: float = Field(ge=0.0, le=1.0)


class TagOutput(BaseModel):
    suggested_tags: list[str] = Field(
        default_factory=list, description="UX tag names from the existing set that apply"
    )
    new_suggestions: list[str] = Field(
        default_factory=list, description="New tag names not in the existing set"
    )


class CategoryProficiency(BaseModel):
    category: str = Field(description="Category name, must be from the provided list")
    proficiency: float = Field(
        ge=0.0, le=1.0,
        description=(
            "Estimated proficiency 0.0-1.0. "
            "0.9+ = expert/lead-level. 0.7-0.9 = strong/senior. "
            "0.4-0.7 = solid working knowledge. 0.2-0.4 = some exposure. "
            "Only include categories with clear evidence in the bio."
        ),
    )


class CategoryDiffusionItem(BaseModel):
    category_name: str = Field(description="Lowercase, slug-style canonical category name")
    weight: float = Field(ge=0.0, le=1.0, description="Relative weight (0-1) of this category in the plan; weights need not sum to 1")
    description: str = Field(description="One-sentence explanation of why this category is needed")


class CategoryDiffusionOutput(BaseModel):
    plan: list[CategoryDiffusionItem] = Field(default_factory=list)


class GeneratedTaskItem(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="")
    category_name: str
    complexity: int = Field(ge=1, le=5)
    estimated_minutes: int = Field(ge=15, le=4800)
    priority: str = Field(description="One of: p1, p2, p3, p4, p5")
    tag_names: list[str] = Field(default_factory=list)


class GeneratedTasksOutput(BaseModel):
    tasks: list[GeneratedTaskItem] = Field(default_factory=list)


class SkillOutput(BaseModel):
    skills: list[str] = Field(
        default_factory=list, description="Extracted skill/technology names"
    )
    primary_category: str | None = Field(
        default=None, description="Best matching category from the provided list"
    )
    seniority_hint: str | None = Field(
        default=None, description="junior/mid/senior/lead if inferable"
    )
    category_proficiencies: list[CategoryProficiency] = Field(
        default_factory=list,
        description=(
            "Proficiency estimate per relevant category. "
            "Only include categories where the bio provides clear evidence. "
            "Do not invent scores."
        ),
    )
