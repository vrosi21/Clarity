from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.repositories.worker_profile_repository import WorkerProfileRepository
from app.schemas.worker_profile import (
    SkillProfileResponse,
    SkillProfileUpsert,
    WorkerProfileResponse,
    WorkerProfileUpdate,
)
from app.services.worker_profile_service import WorkerProfileService

router = APIRouter(prefix="/users/{user_id}/worker-profile", tags=["worker-profiles"])


def _service(db: Session) -> WorkerProfileService:
    return WorkerProfileService(WorkerProfileRepository(db), UserRepository(db))


@router.get("", response_model=WorkerProfileResponse)
def get_profile(
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> WorkerProfileResponse:
    return _service(db).get_profile(user_id, current_user, db)


@router.put("", response_model=WorkerProfileResponse)
def upsert_profile(
    user_id: int,
    req: WorkerProfileUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> WorkerProfileResponse:
    return _service(db).create_or_update_profile(user_id, req, current_user, db)


@router.post("/skills", response_model=SkillProfileResponse)
def upsert_skill(
    user_id: int,
    req: SkillProfileUpsert,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SkillProfileResponse:
    return _service(db).upsert_skill(user_id, req, current_user, db)
