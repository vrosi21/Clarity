from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import StageType


class StageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    order: int
    type: StageType
    color: str | None = None


class StageUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    order: int | None = None
    color: str | None = None


class StageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    order: int
    type: StageType | None
    color: str | None


class StageReorderRequest(BaseModel):
    ordered_ids: list[int]
