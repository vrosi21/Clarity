from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SeniorityLevel


class WorkerProfileCreate(BaseModel):
    seniority: SeniorityLevel
    years_experience: int = Field(default=0, ge=0)
    primary_category_id: int | None = None


class WorkerProfileUpdate(BaseModel):
    seniority: SeniorityLevel | None = None
    years_experience: int | None = Field(default=None, ge=0)
    primary_category_id: int | None = None
    base_productivity: float | None = Field(default=None, gt=0)
    burnout_threshold: int | None = Field(default=None, gt=0)
    is_available: bool | None = None


class SkillProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    proficiency: float
    efficiency: float | None


class WorkerProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    username: str | None = None
    seniority: SeniorityLevel
    years_experience: int
    primary_category_id: int | None
    base_productivity: float
    burnout_threshold: int
    is_available: bool
    skill_profiles: list[SkillProfileResponse] = []


class SkillProfileUpsert(BaseModel):
    category_id: int
    proficiency: float = Field(ge=0.0, le=1.0)
