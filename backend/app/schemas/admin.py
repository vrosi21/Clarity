from pydantic import BaseModel, ConfigDict


class AdminUserCreate(BaseModel):
    email: str
    username: str
    full_name: str | None = None
    password: str
    years_experience: int = 0
    org_role_id: int | None = None   # defaults to builtin "member" if None


class AdminUserUpdate(BaseModel):
    email: str | None = None
    username: str | None = None
    full_name: str | None = None
    years_experience: int | None = None
    is_active: bool | None = None
    org_role_id: int | None = None
    bio: str | None = None


class SkillProfileEntry(BaseModel):
    category_id: int
    proficiency: float


class SkillProfileBulkSet(BaseModel):
    skills: list[SkillProfileEntry]


class UserDetailOut(BaseModel):
    id: int
    email: str
    username: str
    full_name: str | None
    years_experience: int
    is_active: bool
    org_role_id: int | None
    org_role_name: str | None
    bio: str | None = None
    skills: list[SkillProfileEntry] = []
    model_config = ConfigDict(from_attributes=True)


class DashboardStats(BaseModel):
    total_users: int
    total_projects: int
    active_tickets: int
    users_by_role: list[dict]
    workload_by_user: list[dict]
