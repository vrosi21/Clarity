from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.models.user_org_role import UserOrgRole
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, OrgRoleInfo, SelfUpdate, TokenResponse, UserResponse


class AuthService:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    def update_self(self, user: User, data: SelfUpdate, db: Session) -> User:
        # Password is required only when changing credentials (username/password).
        wants_credential_change = (
            data.username is not None and data.username != user.username
        ) or data.new_password is not None
        if wants_credential_change:
            if not data.current_password or not verify_password(
                data.current_password, user.hashed_password
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect",
                )
        if data.username is not None and data.username != user.username:
            existing = self.user_repo.get_by_username(data.username)
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Username already taken"
                )
            user.username = data.username
        if data.new_password is not None:
            user.hashed_password = hash_password(data.new_password)
        if data.bio is not None:
            self._upsert_bio(user, data.bio, db)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def _upsert_bio(user: User, bio: str, db: Session) -> None:
        wp = user.worker_profile
        if wp is None:
            return
        if wp.bio == bio:
            return
        wp.bio = bio
        db.flush()
        try:
            from app.services.worker_profile_service import _refresh_bio_embedding
            if bio:
                _refresh_bio_embedding(wp, db)
        except Exception:
            pass

    def login(self, req: LoginRequest, db: Session) -> TokenResponse:
        user = self.user_repo.get_by_email(req.email)
        if user is None or not verify_password(req.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated"
            )
        token = create_access_token({"sub": str(user.id)})
        return TokenResponse(access_token=token)

    def to_response(self, user: User, db: Session) -> UserResponse:
        org_role_row = db.execute(
            select(UserOrgRole)
            .options(joinedload(UserOrgRole.role))
            .where(UserOrgRole.user_id == user.id)
        ).scalar_one_or_none()
        org_role_info = None
        if org_role_row is not None and org_role_row.role is not None:
            org_role_info = OrgRoleInfo(
                role_id=org_role_row.role.id,
                role_name=org_role_row.role.name,
                permissions=list(org_role_row.role.permissions or []),
            )
        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            years_experience=user.years_experience,
            is_active=user.is_active,
            bio=user.worker_profile.bio if user.worker_profile else None,
            org_role=org_role_info,
        )
