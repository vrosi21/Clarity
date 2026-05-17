from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.permission_service import PermissionService, get_permission_service
from app.core.permissions import Permission
from app.models.user import User
from app.repositories.member_repository import MemberRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.member import MemberAddRequest, MemberResponse, MemberUpdateRequest


class MemberService:
    def __init__(
        self,
        member_repo: MemberRepository,
        user_repo: UserRepository,
        role_repo: RoleRepository,
        perm_svc: PermissionService | None = None,
    ) -> None:
        self.member_repo = member_repo
        self.user_repo = user_repo
        self.role_repo = role_repo
        self.perm_svc = perm_svc or get_permission_service()

    # ------------------------------------------------------------------

    def _to_response(self, member, user: User) -> MemberResponse:
        role = member.role
        return MemberResponse(
            user_id=member.user_id,
            username=user.username,
            email=user.email,
            role_id=member.role_id,
            role_name=role.name if role else "",
            role_permissions=list(role.permissions or []) if role else [],
        )

    def _validate_assignable_project_role(self, role_id: int) -> None:
        role = self.role_repo.get_by_id(role_id)
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Role not found"
            )
        if role.scope.value not in ("project", "both"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role is not assignable at the project level",
            )

    # ------------------------------------------------------------------

    def list_members(
        self, project_id: int, current_user: User, db: Session
    ) -> list[MemberResponse]:
        self.perm_svc.require(
            current_user.id, Permission.PROJECTS_READ, project_id, db
        )
        members = self.member_repo.list_members(project_id)
        return [self._to_response(m, m.user) for m in members]

    def add_member(
        self,
        project_id: int,
        req: MemberAddRequest,
        current_user: User,
        db: Session,
    ) -> MemberResponse:
        self.perm_svc.require(
            current_user.id, Permission.PROJECTS_MANAGE_MEMBERS, project_id, db
        )
        self._validate_assignable_project_role(req.role_id)
        if self.user_repo.get_by_id(req.user_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if self.member_repo.get_membership(project_id, req.user_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="User is already a member"
            )
        member = self.member_repo.add_member(project_id, req.user_id, req.role_id)
        db.commit()
        db.refresh(member)
        user = self.user_repo.get_by_id(member.user_id)
        return self._to_response(member, user)

    def update_member_role(
        self,
        project_id: int,
        target_user_id: int,
        req: MemberUpdateRequest,
        current_user: User,
        db: Session,
    ) -> MemberResponse:
        self.perm_svc.require(
            current_user.id, Permission.PROJECTS_MANAGE_MEMBERS, project_id, db
        )
        if target_user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change your own role",
            )
        self._validate_assignable_project_role(req.role_id)
        member = self.member_repo.get_membership(project_id, target_user_id)
        if member is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
            )
        self.member_repo.update_role(member, req.role_id)
        db.commit()
        db.refresh(member)
        user = self.user_repo.get_by_id(member.user_id)
        return self._to_response(member, user)

    def remove_member(
        self, project_id: int, target_user_id: int, current_user: User, db: Session
    ) -> None:
        self.perm_svc.require(
            current_user.id, Permission.PROJECTS_MANAGE_MEMBERS, project_id, db
        )
        member = self.member_repo.get_membership(project_id, target_user_id)
        if member is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Member not found"
            )
        if target_user_id == current_user.id:
            # Prevent removing yourself if no other member has manage_members perm.
            other_managers = [
                m
                for m in self.member_repo.list_members_with_perm(
                    project_id, Permission.PROJECTS_MANAGE_MEMBERS
                )
                if m.user_id != current_user.id
            ]
            if not other_managers:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove yourself as the last manager",
                )
        self.member_repo.remove_member(member)
        db.commit()
