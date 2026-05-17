from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.repositories.member_repository import MemberRepository
from app.repositories.rl_config_repository import RLConfigRepository
from app.schemas.rl_config import RLConfigResponse, RLConfigUpdate
from app.services.rl_config_service import RLConfigService

router = APIRouter(prefix="/projects/{project_id}/rl-config", tags=["rl-config"])


def _service(db: Session) -> RLConfigService:
    return RLConfigService(RLConfigRepository(db), MemberRepository(db))


@router.get("", response_model=RLConfigResponse)
def get_config(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RLConfigResponse:
    return _service(db).get_config(project_id, current_user, db)


@router.patch("", response_model=RLConfigResponse)
def update_config(
    project_id: int,
    req: RLConfigUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RLConfigResponse:
    return _service(db).update_config(project_id, req, current_user, db)
