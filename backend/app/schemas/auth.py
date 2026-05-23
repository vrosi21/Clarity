from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Kept for backward compatibility; public registration is disabled at the route layer."""
    email: EmailStr
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str  # plain str — deliverability check would reject internal domains
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class OrgRoleInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    role_id: int
    role_name: str
    permissions: list[str]


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    full_name: str | None = None
    years_experience: int = 0
    is_active: bool = True
    bio: str | None = None
    org_role: OrgRoleInfo | None = None


class SelfUpdate(BaseModel):
    username: str | None = None
    current_password: str | None = None
    new_password: str | None = None
    bio: str | None = None
