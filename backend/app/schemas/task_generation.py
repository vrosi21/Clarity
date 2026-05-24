from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TaskGenerationConfig(BaseModel):
    complexity_profile: Literal["simple", "medium", "complex"] = "medium"
    total_hours_min: int = Field(default=40, ge=10, le=2000)
    total_hours_max: int = Field(default=200, ge=10, le=2000)
    task_count: int = Field(default=15, ge=3, le=50)


class GenerateTasksRequest(BaseModel):
    generation_config: TaskGenerationConfig


class CategoryDiffusionEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    category_id: int
    category_name: str
    weight: float
    description: str
    is_new: bool
    color: str


class GeneratedTicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    stage_id: int
    title: str
    description: str | None
    priority: str
    complexity: int
    category_id: int | None
    category_name: str | None
    category_color: str | None = None
    estimated_minutes: int | None
