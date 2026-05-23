from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Synthetic worker ───────────────────────────────────────────────────────────

class SyntheticWorkerCreate(BaseModel):
    name: str
    seniority: Literal["junior", "mid", "senior", "lead"]
    years_experience: float = Field(ge=0, le=20)
    primary_category: str
    category_proficiency: dict[str, float] = Field(default_factory=dict)
    base_productivity: float = Field(default=1.0, ge=0.1, le=3.0)
    burnout_threshold: int = Field(default=2400, ge=60)


class SyntheticWorkerResponse(BaseModel):
    id: int
    team_id: int
    name: str
    seniority: str
    years_experience: float
    primary_category: str
    category_proficiency: dict[str, float]
    base_productivity: float
    burnout_threshold: int

    model_config = {"from_attributes": True}


# ── Synthetic team ─────────────────────────────────────────────────────────────

class SyntheticTeamCreate(BaseModel):
    name: str
    description: str | None = None
    workers: list[SyntheticWorkerCreate] = Field(min_length=1)


class SyntheticTeamResponse(BaseModel):
    id: int
    name: str
    description: str | None
    created_by: int
    created_at: datetime
    workers: list[SyntheticWorkerResponse] = []

    model_config = {"from_attributes": True}


class SyntheticTeamListItem(BaseModel):
    id: int
    name: str
    description: str | None
    created_by: int
    created_at: datetime
    worker_count: int

    model_config = {"from_attributes": True}


# ── Simulation run ─────────────────────────────────────────────────────────────

class RLConfigOverride(BaseModel):
    temperature: float | None = Field(default=None, ge=0.01, le=2.0)
    w_priority: float | None = None
    w_efficiency: float | None = None
    w_overload: float | None = None
    w_throughput: float | None = None
    gamma: float | None = Field(default=None, ge=0.0, le=1.0)


class SimulationRunRequest(BaseModel):
    team_source: Literal["project", "synthetic"]
    synthetic_team_id: int | None = None
    rl_config_overrides: RLConfigOverride | None = None


class SimulationEventLog(BaseModel):
    t: float
    type: Literal["assigned", "stage_changed", "completed", "blocked"]
    ticket_id: int
    ticket_title: str
    worker_id: int
    worker_name: str
    from_stage: str | None = None
    to_stage: str | None = None
    q_value: float | None = None


class SimulationSummary(BaseModel):
    total_time: float
    avg_efficiency: float
    n_tasks: int
    n_blocked: int
    n_workers: int


class SimulationRunResponse(BaseModel):
    id: int
    project_id: int
    created_by: int
    created_at: datetime
    team_source: str
    synthetic_team_id: int | None
    rl_config_snapshot: dict[str, Any]
    event_log: list[dict[str, Any]]
    summary: dict[str, Any]
    status: str

    model_config = {"from_attributes": True}


class SimulationRunSummaryResponse(BaseModel):
    id: int
    project_id: int
    created_by: int
    created_at: datetime
    team_source: str
    synthetic_team_id: int | None
    summary: dict[str, Any]
    status: str

    model_config = {"from_attributes": True}
