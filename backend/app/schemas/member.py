from pydantic import BaseModel, ConfigDict


class MemberAddRequest(BaseModel):
    user_id: int
    role_id: int


class MemberUpdateRequest(BaseModel):
    role_id: int


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    email: str
    role_id: int
    role_name: str
    role_permissions: list[str]
