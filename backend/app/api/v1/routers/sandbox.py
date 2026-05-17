from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.repositories.member_repository import MemberRepository
from app.repositories.stage_repository import StageRepository
from app.schemas.sandbox import (
    SandboxResetResponse,
    SandboxSeedRequest,
    SandboxSeedResponse,
)
from app.services.sandbox_service import SandboxService

router = APIRouter(prefix="/projects/{project_id}/sandbox", tags=["sandbox"])


def _service(db: Session) -> SandboxService:
    return SandboxService(
        db=db, member_repo=MemberRepository(db), stage_repo=StageRepository(db)
    )


@router.post("/seed", response_model=SandboxSeedResponse)
def seed_sandbox(
    project_id: int,
    req: SandboxSeedRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SandboxSeedResponse:
    return _service(db).seed(
        project_id=project_id,
        current_user=current_user,
        n_workers=req.n_workers,
        n_tickets=req.n_tickets,
        seed=req.seed,
        reset_first=req.reset_first,
    )


@router.post("/reset", response_model=SandboxResetResponse)
def reset_sandbox(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SandboxResetResponse:
    return _service(db).reset(project_id=project_id, current_user=current_user)
