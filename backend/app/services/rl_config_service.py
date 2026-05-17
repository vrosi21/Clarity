from sqlalchemy.orm import Session

from app.core.permission_service import PermissionService, get_permission_service
from app.core.permissions import Permission
from app.models.user import User
from app.repositories.member_repository import MemberRepository
from app.repositories.rl_config_repository import RLConfigRepository
from app.schemas.rl_config import RLConfigResponse, RLConfigUpdate


_DEFAULTS = {
    "temperature": 0.5,
    "w_priority": 1.0,
    "w_efficiency": 1.0,
    "w_overload": 1.0,
    "w_throughput": 1.0,
    "gamma": 0.95,
    "fine_tune_every_n_completions": 50,
    "replay_buffer_max_size": 5000,
}


class RLConfigService:
    def __init__(
        self,
        rl_repo: RLConfigRepository,
        member_repo: MemberRepository,
        perm_svc: PermissionService | None = None,
    ) -> None:
        self.rl_repo = rl_repo
        self.member_repo = member_repo
        self.perm_svc = perm_svc or get_permission_service()

    def get_config(
        self, project_id: int, current_user: User, db: Session
    ) -> RLConfigResponse:
        self.perm_svc.require(
            current_user.id, Permission.PROJECTS_READ, project_id, db
        )
        config = self.rl_repo.get_for_project(project_id)
        if config is None:
            return RLConfigResponse(project_id=project_id, **_DEFAULTS)
        return RLConfigResponse.model_validate(config)

    def update_config(
        self,
        project_id: int,
        req: RLConfigUpdate,
        current_user: User,
        db: Session,
    ) -> RLConfigResponse:
        self.perm_svc.require(
            current_user.id, Permission.PROJECTS_MANAGE_SETTINGS, project_id, db
        )
        config = self.rl_repo.upsert(project_id, **req.model_dump(exclude_unset=True))
        db.commit()
        db.refresh(config)
        return RLConfigResponse.model_validate(config)
