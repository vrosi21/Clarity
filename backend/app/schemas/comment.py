from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    content: str = Field(min_length=1)
    parent_id: int | None = None


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    user_id: int
    username: str | None = None
    created_at: datetime
    parent_id: int | None
