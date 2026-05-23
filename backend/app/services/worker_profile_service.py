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
        bio=profile.bio,
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
        bio_changed = "bio" in data and (profile is None or profile.bio != data["bio"])
        if profile is None:
            if "seniority" not in data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="seniority is required to create a worker profile",
                )
            profile = self.worker_repo.create(user_id=user_id, **data)
        else:
            self.worker_repo.update(profile, **data)

        if bio_changed and profile.bio:
            _refresh_bio_embedding(profile, db)

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


def _refresh_bio_embedding(profile, db: Session) -> None:
    """Re-encode bio text and write it into WorkerSkillProfile.nlp_embedding.

    Targets the primary_category if set; otherwise every existing skill profile
    is updated with the same embedding (categories share the same bio).
    Never raises — encoder failure must not block the profile save.
    """
    try:
        from app.ml.nlp.encoder import SemanticEncoder
        from app.models.worker_skill_profile import WorkerSkillProfile

        encoder = SemanticEncoder()
        # Anchor the bio embedding with the worker's known skill categories so
        # the dot product against task embeddings (which include "Area: X") lands
        # in the same semantic space. E.g. "bio text\nSkilled in: backend, devops"
        cat_names = [sp.category.name for sp in (profile.skill_profiles or []) if sp.category]
        text_to_encode = profile.bio
        if cat_names:
            text_to_encode = f"{profile.bio}\nSkilled in: {', '.join(cat_names)}"
        embedding = encoder.encode_one(text_to_encode).tolist()

        targets: list[WorkerSkillProfile] = []
        if profile.primary_category_id:
            existing = db.execute(
                select(WorkerSkillProfile).where(
                    WorkerSkillProfile.worker_id == profile.id,
                    WorkerSkillProfile.category_id == profile.primary_category_id,
                )
            ).scalar_one_or_none()
            if existing is None:
                existing = WorkerSkillProfile(
                    worker_id=profile.id,
                    category_id=profile.primary_category_id,
                    proficiency=0.5,
                )
                db.add(existing)
            targets.append(existing)
        else:
            targets.extend(profile.skill_profiles or [])

        for sp in targets:
            sp.nlp_embedding = embedding
            sp.nlp_ticket_count = (sp.nlp_ticket_count or 0)
        db.flush()
    except Exception:
        pass
