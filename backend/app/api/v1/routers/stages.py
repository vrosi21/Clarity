from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.repositories.member_repository import MemberRepository
from app.repositories.stage_repository import StageRepository
from app.schemas.stage import StageCreate, StageReorderRequest, StageResponse, StageUpdate
from app.services.stage_service import StageService

router = APIRouter(prefix="/projects/{project_id}/stages", tags=["stages"])


def _service(db: Session) -> StageService:
    return StageService(StageRepository(db), MemberRepository(db))


@router.get("", response_model=list[StageResponse])
def list_stages(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[StageResponse]:
    return [
        StageResponse.model_validate(s)
        for s in _service(db).list_stages(project_id, current_user, db)
    ]


@router.post("", response_model=StageResponse, status_code=status.HTTP_201_CREATED)
def create_stage(
    project_id: int,
    req: StageCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StageResponse:
    return StageResponse.model_validate(
        _service(db).create_stage(project_id, req, current_user, db)
    )


@router.patch("/{stage_id}", response_model=StageResponse)
def update_stage(
    project_id: int,
    stage_id: int,
    req: StageUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> StageResponse:
    return StageResponse.model_validate(
        _service(db).update_stage(project_id, stage_id, req, current_user, db)
    )


@router.delete("/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stage(
    project_id: int,
    stage_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    _service(db).delete_stage(project_id, stage_id, current_user, db)


@router.post("/reorder", response_model=list[StageResponse])
def reorder_stages(
    project_id: int,
    req: StageReorderRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[StageResponse]:
    return [
        StageResponse.model_validate(s)
        for s in _service(db).reorder_stages(project_id, req.ordered_ids, current_user, db)
    ]
