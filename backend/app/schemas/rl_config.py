from pydantic import BaseModel, ConfigDict, Field


class RLConfigUpdate(BaseModel):
    temperature: float | None = Field(default=None, gt=0)
    w_priority: float | None = None
    w_efficiency: float | None = None
    w_overload: float | None = None
    w_throughput: float | None = None
    gamma: float | None = Field(default=None, ge=0.0, le=1.0)
    fine_tune_every_n_completions: int | None = Field(default=None, gt=0)
    replay_buffer_max_size: int | None = Field(default=None, gt=0)


class RLConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: int
    temperature: float
    w_priority: float
    w_efficiency: float
    w_overload: float
    w_throughput: float
    gamma: float
    fine_tune_every_n_completions: int
    replay_buffer_max_size: int


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    color: str
