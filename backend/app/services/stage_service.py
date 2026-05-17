from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.permission_service import PermissionService, get_permission_service
from app.core.permissions import Permission
from app.models.stage import Stage
from app.models.user import User
from app.repositories.member_repository import MemberRepository
from app.repositories.stage_repository import StageRepository
from app.schemas.stage import StageCreate, StageUpdate


class StageService:
    def __init__(
        self,
        stage_repo: StageRepository,
        member_repo: MemberRepository,
        perm_svc: PermissionService | None = None,
    ) -> None:
        self.stage_repo = stage_repo
        self.member_repo = member_repo
        self.perm_svc = perm_svc or get_permission_service()

    def list_stages(
        self, project_id: int, current_user: User, db: Session
    ) -> list[Stage]:
        self.perm_svc.require(
            current_user.id, Permission.PROJECTS_READ, project_id, db
        )
        return self.stage_repo.list_for_project(project_id)

    def create_stage(
        self, project_id: int, req: StageCreate, current_user: User, db: Session
    ) -> Stage:
        self.perm_svc.require(
            current_user.id, Permission.STAGES_CREATE, project_id, db
        )
        stage = self.stage_repo.create(
            project_id=project_id,
            name=req.name,
            order=req.order,
            type=req.type,
            color=req.color,
        )
        db.commit()
        db.refresh(stage)
        return stage

    def update_stage(
        self,
        project_id: int,
        stage_id: int,
        req: StageUpdate,
        current_user: User,
        db: Session,
    ) -> Stage:
        self.perm_svc.require(
            current_user.id, Permission.STAGES_UPDATE, project_id, db
        )
        stage = self.stage_repo.get_by_id(stage_id)
        if stage is None or stage.project_id != project_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage not found")
        self.stage_repo.update(stage, **req.model_dump(exclude_unset=True))
        db.commit()
        db.refresh(stage)
        return stage

    def delete_stage(
        self, project_id: int, stage_id: int, current_user: User, db: Session
    ) -> None:
        self.perm_svc.require(
            current_user.id, Permission.STAGES_DELETE, project_id, db
        )
        stage = self.stage_repo.get_by_id(stage_id)
        if stage is None or stage.project_id != project_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stage not found")
        self.stage_repo.delete(stage)
        db.commit()

    def reorder_stages(
        self,
        project_id: int,
        ordered_ids: list[int],
        current_user: User,
        db: Session,
    ) -> list[Stage]:
        self.perm_svc.require(
            current_user.id, Permission.STAGES_REORDER, project_id, db
        )
        stages = self.stage_repo.reorder(project_id, ordered_ids)
        db.commit()
        return stages
