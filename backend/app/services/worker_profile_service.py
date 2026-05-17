from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permission_service import PermissionService, get_permission_service
from app.core.permissions import Permission
from app.models.project_member import ProjectMember
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.repositories.worker_profile_repository import WorkerProfileRepository
from app.schemas.worker_profile import (
    SkillProfileResponse,
    SkillProfileUpsert,
    WorkerProfileCreate,
    WorkerProfileResponse,
    WorkerProfileUpdate,
)


def _to_response(profile, username: str | None) -> WorkerProfileResponse:
    return WorkerProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        username=username,
        seniority=profile.seniority,
        years_experience=profile.years_experience,
        primary_category_id=profile.primary_category_id,
        base_productivity=profile.base_productivity,
        burnout_threshold=profile.burnout_threshold,
        is_available=profile.is_available,
        skill_profiles=[
            SkillProfileResponse.model_validate(sp) for sp in profile.skill_profiles
        ],
    )


def _can_manage_target_user(
    perm_svc: PermissionService, current_user_id: int, target_user_id: int, db: Session
) -> bool:
    """True if current user has org-level user-management permission, or has
    `projects:manage_members` in any project the target user belongs to."""
    if perm_svc.has(current_user_id, Permission.ORG_MANAGE_USERS, None, db):
        return True
    target_projects = db.execute(
        select(ProjectMember.project_id).where(ProjectMember.user_id == target_user_id)
    ).scalars().all()
    for pid in target_projects:
        if perm_svc.has(current_user_id, Permission.PROJECTS_MANAGE_MEMBERS, pid, db):
            return True
    return False


class WorkerProfileService:
    def __init__(
        self,
        worker_repo: WorkerProfileRepository,
        user_repo: UserRepository,
        perm_svc: PermissionService | None = None,
    ) -> None:
        self.worker_repo = worker_repo
        self.user_repo = user_repo
        self.perm_svc = perm_svc or get_permission_service()

    def get_profile(
        self, user_id: int, current_user: User, db: Session
    ) -> WorkerProfileResponse:
        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        profile = self.worker_repo.get_by_user_id(user_id)
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Worker profile not found"
            )
        return _to_response(profile, user.username)

    def create_or_update_profile(
        self,
        user_id: int,
        req: WorkerProfileCreate | WorkerProfileUpdate,
        current_user: User,
        db: Session,
    ) -> WorkerProfileResponse:
        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if user_id != current_user.id and not _can_manage_target_user(
            self.perm_svc, current_user.id, user_id, db
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permission to edit this profile",
            )

        profile = self.worker_repo.get_by_user_id(user_id)
        data = req.model_dump(exclude_unset=True)
        if profile is None:
            if "seniority" not in data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="seniority is required to create a worker profile",
                )
            profile = self.worker_repo.create(user_id=user_id, **data)
        else:
            self.worker_repo.update(profile, **data)
        db.commit()
        profile = self.worker_repo.get_by_user_id(user_id)
        return _to_response(profile, user.username)

    def upsert_skill(
        self,
        user_id: int,
        req: SkillProfileUpsert,
        current_user: User,
        db: Session,
    ) -> SkillProfileResponse:
        if not _can_manage_target_user(self.perm_svc, current_user.id, user_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permission to edit this profile",
            )
        profile = self.worker_repo.get_by_user_id(user_id)
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Worker profile must exist before adding skills",
            )
        skill = self.worker_repo.upsert_skill(profile.id, req.category_id, req.proficiency)
        db.commit()
        db.refresh(skill)
        return SkillProfileResponse.model_validate(skill)
