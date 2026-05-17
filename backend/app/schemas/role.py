from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.permissions import Permission
from app.models.enums import RoleScope


def _validate_permissions(perms: list[str]) -> list[str]:
    allowed = set(Permission.ALL)
    unknown = [p for p in perms if p not in allowed]
    if unknown:
        raise ValueError(f"Unknown permissions: {sorted(unknown)}")
    # Deduplicate, preserve order
    seen: set[str] = set()
    result: list[str] = []
    for p in perms:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    scope: RoleScope
    permissions: list[str] = Field(default_factory=list)

    @field_validator("permissions")
    @classmethod
    def _check_perms(cls, v: list[str]) -> list[str]:
        return _validate_permissions(v)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    permissions: list[str] | None = None

    @field_validator("permissions")
    @classmethod
    def _check_perms(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        return _validate_permissions(v)


class RoleResponse(BaseModel):
    id: int
    name: str
    description: str | None
    scope: RoleScope
    is_builtin: bool
    permissions: list[str]
    model_config = ConfigDict(from_attributes=True)


class AssignOrgRoleRequest(BaseModel):
    role_id: int
