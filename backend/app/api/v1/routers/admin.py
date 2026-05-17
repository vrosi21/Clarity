"""Admin routers.

Two routers in this file:
- `router`: project-level LTS/FSM verification at /projects/{project_id}/admin
- `global_admin_router`: global user management at /admin
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin, require_permission
from app.core.fsm import TaskFSM
from app.core.lts import SystemLTS
from app.core.permissions import Permission
from app.ml.registry import ModelRegistry, get_model_registry
from app.models.enums import StageType
from app.models.user import User
from app.repositories.stage_repository import StageRepository
from app.repositories.ticket_repository import TicketRepository
from app.schemas.admin import (
    AdminUserCreate,
    AdminUserUpdate,
    DashboardStats,
    SkillProfileBulkSet,
    SkillProfileEntry,
    UserDetailOut,
)
from app.services.admin_service import AdminService

router = APIRouter(prefix="/projects/{project_id}/admin", tags=["admin"])
global_admin_router = APIRouter(prefix="/admin", tags=["admin-mgmt"])


class ModelReloadResponse(BaseModel):
    has_regressor: bool
    has_q_network: bool


class SafetyViolationOut(BaseModel):
    ticket_id: int
    reached_stage_id: int
    reason: str


class VerifyResponse(BaseModel):
    fsm_configured: bool
    reachable_state_count: int
    transition_count: int
    safe: bool
    truncated: bool
    safety_violations: list[SafetyViolationOut]


@router.get("/verify", response_model=VerifyResponse)
def verify_project(
    project_id: int,
    _: Annotated[User, Depends(require_permission(Permission.PROJECTS_MANAGE_SETTINGS))],
    db: Annotated[Session, Depends(get_db)],
    max_states: int = 50_000,
) -> VerifyResponse:
    stages = StageRepository(db).list_for_project(project_id)
    if not stages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Project has no stages"
        )

    types = {s.type for s in stages if s.type is not None}
    fsm_configured = StageType.START in types and StageType.FINAL in types
    if not fsm_configured:
        return VerifyResponse(
            fsm_configured=False,
            reachable_state_count=0,
            transition_count=0,
            safe=True,
            truncated=False,
            safety_violations=[],
        )

    try:
        TaskFSM(stages)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"FSM construction failed: {e}",
        )

    tickets = TicketRepository(db).list_for_project(project_id)
    ticket_stage_map = {t.id: t.stage_id for t in tickets}
    if not ticket_stage_map:
        return VerifyResponse(
            fsm_configured=True,
            reachable_state_count=0,
            transition_count=0,
            safe=True,
            truncated=False,
            safety_violations=[],
        )

    report = SystemLTS(stages, ticket_stage_map, max_states=max_states).explore()
    return VerifyResponse(
        fsm_configured=True,
        reachable_state_count=report.reachable_state_count,
        transition_count=report.transition_count,
        safe=report.safe,
        truncated=report.truncated,
        safety_violations=[
            SafetyViolationOut(
                ticket_id=v.ticket_id,
                reached_stage_id=v.reached_stage_id,
                reason=v.reason,
            )
            for v in report.safety_violations
        ],
    )


@router.post("/reload-models", response_model=ModelReloadResponse)
def reload_models(
    project_id: int,
    _: Annotated[User, Depends(require_permission(Permission.PROJECTS_MANAGE_SETTINGS))],
    registry: Annotated[ModelRegistry, Depends(get_model_registry)],
) -> ModelReloadResponse:
    registry.reload()
    return ModelReloadResponse(
        has_regressor=registry.has_regressor,
        has_q_network=registry.has_q_network,
    )


# ── Global admin routes ──────────────────────────────────────────────────────


@global_admin_router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> DashboardStats:
    return AdminService(db).get_dashboard_stats()


@global_admin_router.get("/users", response_model=list[UserDetailOut])
def list_users(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> list[UserDetailOut]:
    return AdminService(db).list_users()


@global_admin_router.post("/users", response_model=UserDetailOut, status_code=201)
def create_user(
    data: AdminUserCreate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> UserDetailOut:
    return AdminService(db).create_user(data, current_user)


@global_admin_router.get("/users/{user_id}", response_model=UserDetailOut)
def get_user(
    user_id: int,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> UserDetailOut:
    return AdminService(db).get_user(user_id)


@global_admin_router.patch("/users/{user_id}", response_model=UserDetailOut)
def update_user(
    user_id: int,
    data: AdminUserUpdate,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> UserDetailOut:
    return AdminService(db).update_user(user_id, data, current_user)


@global_admin_router.delete("/users/{user_id}", status_code=204)
def deactivate_user(
    user_id: int,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    AdminService(db).deactivate_user(user_id, current_user)


@global_admin_router.get("/users/{user_id}/skills", response_model=list[SkillProfileEntry])
def get_skills(
    user_id: int,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> list[SkillProfileEntry]:
    return AdminService(db).get_user(user_id).skills


@global_admin_router.put("/users/{user_id}/skills", response_model=list[SkillProfileEntry])
def set_skills(
    user_id: int,
    data: SkillProfileBulkSet,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> list[SkillProfileEntry]:
    return AdminService(db).set_skill_profiles(user_id, data)
