from pydantic import BaseModel, Field


class SandboxSeedRequest(BaseModel):
    n_workers: int = Field(default=6, ge=1, le=50)
    n_tickets: int = Field(default=20, ge=1, le=500)
    seed: int | None = None
    # If True, also wipe any prior sandbox state in the project before seeding.
    reset_first: bool = False


class SandboxSeedResponse(BaseModel):
    project_id: int
    workers_created: int
    tickets_created: int
    bot_user_ids: list[int]


class SandboxResetResponse(BaseModel):
    project_id: int
    workers_removed: int
    tickets_removed: int
