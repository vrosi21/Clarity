from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_perm_service, require_permission
from app.core.permission_service import PermissionService
from app.core.permissions import Permission
from app.models.user import User
from app.repositories.simulation_repository import SimulationRepository
from app.schemas.simulation import (
    SimulationRunRequest,
    SimulationRunResponse,
    SimulationRunSummaryResponse,
    SyntheticTeamCreate,
    SyntheticTeamListItem,
    SyntheticTeamResponse,
)
from app.services.simulation_service import SimulationService

router = APIRouter(prefix="/simulation", tags=["simulation"])

_PERM = Permission.SIMULATION_RUN


def _svc(db: Session) -> SimulationService:
    return SimulationService(SimulationRepository())


def _require_sim(
    current_user: Annotated[User, Depends(require_permission(_PERM, project_id_param=None))],
) -> User:
    return current_user


# ── Run endpoints ──────────────────────────────────────────────────────────────

@router.post(
    "/projects/{project_id}/run",
    response_model=SimulationRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def run_simulation(
    project_id: int,
    req: SimulationRunRequest,
    current_user: Annotated[User, Depends(_require_sim)],
    db: Annotated[Session, Depends(get_db)],
) -> SimulationRunResponse:
    svc = _svc(db)
    run = svc.run_project_simulation(
        project_id=project_id,
        user_id=current_user.id,
        team_source=req.team_source,
        synthetic_team_id=req.synthetic_team_id,
        rl_config_overrides=(
            req.rl_config_overrides.model_dump(exclude_none=True)
            if req.rl_config_overrides
            else None
        ),
        db=db,
    )
    db.commit()
    db.refresh(run)
    return SimulationRunResponse.model_validate(run)


@router.get("/runs", response_model=list[SimulationRunSummaryResponse])
def list_runs(
    project_id: int,
    current_user: Annotated[User, Depends(_require_sim)],
    db: Annotated[Session, Depends(get_db)],
) -> list[SimulationRunSummaryResponse]:
    runs = _svc(db).list_runs(project_id, db)
    return [SimulationRunSummaryResponse.model_validate(r) for r in runs]


@router.get("/runs/{run_id}", response_model=SimulationRunResponse)
def get_run(
    run_id: int,
    current_user: Annotated[User, Depends(_require_sim)],
    db: Annotated[Session, Depends(get_db)],
) -> SimulationRunResponse:
    run = _svc(db).get_run(run_id, db)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return SimulationRunResponse.model_validate(run)


# ── Synthetic team endpoints ───────────────────────────────────────────────────

@router.post("/teams", response_model=SyntheticTeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(
    req: SyntheticTeamCreate,
    current_user: Annotated[User, Depends(_require_sim)],
    db: Annotated[Session, Depends(get_db)],
) -> SyntheticTeamResponse:
    workers_data = [w.model_dump() for w in req.workers]
    team = _svc(db).create_team(
        user_id=current_user.id,
        name=req.name,
        description=req.description,
        workers_data=workers_data,
        db=db,
    )
    db.commit()
    db.refresh(team)
    return SyntheticTeamResponse.model_validate(team)


@router.get("/teams", response_model=list[SyntheticTeamListItem])
def list_teams(
    current_user: Annotated[User, Depends(_require_sim)],
    db: Annotated[Session, Depends(get_db)],
) -> list[SyntheticTeamListItem]:
    teams = _svc(db).list_teams(db)
    return [
        SyntheticTeamListItem(
            id=t.id,
            name=t.name,
            description=t.description,
            created_by=t.created_by,
            created_at=t.created_at,
            worker_count=len(t.workers),
        )
        for t in teams
    ]


@router.delete("/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(
    team_id: int,
    current_user: Annotated[User, Depends(_require_sim)],
    db: Annotated[Session, Depends(get_db)],
    svc_perm: Annotated[PermissionService, Depends(get_perm_service)],
) -> None:
    svc = _svc(db)
    team = svc.get_team(team_id, db)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    is_creator = team.created_by == current_user.id
    is_root = svc_perm.has(current_user.id, Permission.ORG_MANAGE_SETTINGS, None, db)
    if not is_creator and not is_root:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the creator or root may delete this team")

    svc.delete_team(team, db)
    db.commit()
