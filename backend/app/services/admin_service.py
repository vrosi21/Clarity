from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.repositories.admin_repository import AdminRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin import (
    AdminUserCreate,
    AdminUserUpdate,
    DashboardStats,
    SkillProfileBulkSet,
    SkillProfileEntry,
    UserDetailOut,
)


class AdminService:
    def __init__(self, db: Session) -> None:
        self.repo = AdminRepository(db)
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.db = db

    # ------------------------------------------------------------------
    # Read

    def _to_detail(self, user: User) -> UserDetailOut:
        sps = self.repo.get_skill_profiles(user.id)
        skills = [
            SkillProfileEntry(category_id=sp.category_id, proficiency=sp.proficiency)
            for sp in sps
        ]
        org_role = self.role_repo.get_org_role_for_user(user.id)
        role_id = org_role.role_id if org_role else None
        role_name = org_role.role.name if (org_role and org_role.role) else None
        return UserDetailOut(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            years_experience=user.years_experience,
            is_active=user.is_active,
            org_role_id=role_id,
            org_role_name=role_name,
            skills=skills,
        )

    def list_users(self) -> list[UserDetailOut]:
        return [self._to_detail(u) for u in self.repo.get_all_users()]

    def get_user(self, user_id: int) -> UserDetailOut:
        user = self.repo.get_user_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return self._to_detail(user)

    # ------------------------------------------------------------------
    # Write

    def _default_member_role_id(self) -> int:
        member = self.role_repo.get_by_name("member")
        if member is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Built-in 'member' role missing; bootstrap not run",
            )
        return member.id

    def _validate_assignable_org_role(self, role_id: int) -> None:
        role = self.role_repo.get_by_id(role_id)
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Role not found"
            )
        if role.name == "root_user":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Root user role can only be set at deploy time",
            )
        if role.scope.value not in ("org", "both"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role is not assignable at the org level",
            )

    def create_user(
        self, data: AdminUserCreate, current_user: User
    ) -> UserDetailOut:
        if self.user_repo.exists_by_email(data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
            )
        user = self.repo.create_user(
            email=data.email,
            username=data.username,
            full_name=data.full_name,
            years_experience=max(0, min(20, data.years_experience)),
            hashed_password=hash_password(data.password),
        )
        role_id = data.org_role_id or self._default_member_role_id()
        if data.org_role_id is not None:
            self._validate_assignable_org_role(role_id)
        self.role_repo.assign_org_role(user.id, role_id, current_user.id)
        self.db.commit()
        self.db.refresh(user)
        return self._to_detail(user)

    def update_user(
        self, user_id: int, data: AdminUserUpdate, current_user: User
    ) -> UserDetailOut:
        updates = data.model_dump(exclude_none=True)
        org_role_id = updates.pop("org_role_id", None)
        if "years_experience" in updates:
            updates["years_experience"] = max(0, min(20, updates["years_experience"]))

        # Self-deactivation guard
        if (
            user_id == current_user.id
            and updates.get("is_active") is False
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account",
            )

        user = self.repo.update_user(user_id, **updates)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if org_role_id is not None:
            current_org_role = self.role_repo.get_org_role_for_user(current_user.id)
            if (
                user_id == current_user.id
                and current_org_role is not None
                and current_org_role.role is not None
                and current_org_role.role.name in ("root_user", "admin")
                and self.role_repo.get_by_id(org_role_id) is not None
                and self.role_repo.get_by_id(org_role_id).name not in ("root_user", "admin")
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot demote yourself",
                )
            self._validate_assignable_org_role(org_role_id)
            self.role_repo.assign_org_role(user.id, org_role_id, current_user.id)

        self.db.commit()
        self.db.refresh(user)
        return self._to_detail(user)

    def deactivate_user(self, user_id: int, current_user: User) -> None:
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account",
            )
        if not self.repo.deactivate_user(user_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        self.db.commit()

    def set_skill_profiles(
        self, user_id: int, data: SkillProfileBulkSet
    ) -> list[SkillProfileEntry]:
        if self.repo.get_user_by_id(user_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        sps = self.repo.set_skill_profiles(user_id, data.skills)
        self.db.commit()
        return [
            SkillProfileEntry(category_id=sp.category_id, proficiency=sp.proficiency)
            for sp in sps
        ]

    def get_dashboard_stats(self) -> DashboardStats:
        raw = self.repo.get_dashboard_stats()
        return DashboardStats(**raw)
