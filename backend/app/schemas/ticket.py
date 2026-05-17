from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TicketPriority


class TicketCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    priority: TicketPriority = TicketPriority.P3
    complexity: int = Field(default=3, ge=1, le=5)
    stage_id: int
    category_id: int | None = None
    estimated_minutes: int | None = None
    assignee_id: int | None = None


class TicketUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    priority: TicketPriority | None = None
    complexity: int | None = Field(default=None, ge=1, le=5)
    stage_id: int | None = None
    category_id: int | None = None
    estimated_minutes: int | None = None
    assignee_id: int | None = None


class TicketMoveRequest(BaseModel):
    stage_id: int


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    stage_id: int
    title: str
    description: str | None
    priority: TicketPriority
    complexity: int
    category_id: int | None
    category_name: str | None = None
    estimated_minutes: int | None
    assignee_id: int | None
    assignee_username: str | None = None
    created_at: datetime
    updated_at: datetime
