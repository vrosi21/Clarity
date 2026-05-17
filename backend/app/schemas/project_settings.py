from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

ALLOWED_VIEW_SCOPES = {"all", "assigned"}

EDITABLE_FIELD_WHITELIST = {
    "title",
    "description",
    "priority",
    "complexity",
    "estimated_minutes",
    "spent_minutes",
    "due_date",
    "category",
    "assignee",
}


class RoleConstraintUpdate(BaseModel):
    role_id: int
    allowed_transitions: list[list[int]] | None = None
    editable_fields: list[str] | None = None
    assignee_only: bool = False
    view_scope: str = "all"

    @field_validator("view_scope")
    @classmethod
    def _check_view_scope(cls, v: str) -> str:
        if v not in ALLOWED_VIEW_SCOPES:
            raise ValueError(f"view_scope must be one of {sorted(ALLOWED_VIEW_SCOPES)}")
        return v

    @field_validator("allowed_transitions")
    @classmethod
    def _check_transitions(cls, v: list[list[int]] | None) -> list[list[int]] | None:
        if v is None:
            return v
        for pair in v:
            if len(pair) != 2:
                raise ValueError("Each transition must be [from_stage_id, to_stage_id]")
        return v

    @field_validator("editable_fields")
    @classmethod
    def _check_fields(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        unknown = [f for f in v if f not in EDITABLE_FIELD_WHITELIST]
        if unknown:
            raise ValueError(f"Unknown editable fields: {sorted(unknown)}")
        return v


class RoleConstraintResponse(BaseModel):
    id: int
    role_id: int
    role_name: str
    allowed_transitions: list[list[int]] | None
    editable_fields: list[str] | None
    assignee_only: bool
    view_scope: str
    model_config = ConfigDict(from_attributes=True)


class CategoryConfigUpdate(BaseModel):
    category_id: int
    min_proficiency: float = Field(default=0.0)
    allowed_role_ids: list[int] | None = None

    @field_validator("min_proficiency")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class CategoryConfigResponse(BaseModel):
    id: int
    category_id: int
    category_name: str
    min_proficiency: float
    allowed_role_ids: list[int] | None
    model_config = ConfigDict(from_attributes=True)


class ProjectSettingsResponse(BaseModel):
    role_constraints: list[RoleConstraintResponse]
    category_configs: list[CategoryConfigResponse]
