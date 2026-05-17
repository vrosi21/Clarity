from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.permission_service import PermissionService, get_permission_service
from app.core.permissions import Permission
from app.models.project import Project
from app.models.user import User
from app.repositories.member_repository import MemberRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.role_repository import RoleRepository
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.bootstrap import ensure_default_rl_config, ensure_default_stages


class ProjectService:
    def __init__(
        self,
        project_repo: ProjectRepository,
        member_repo: MemberRepository,
        role_repo: RoleRepository,
        perm_svc: PermissionService | None = None,
    ) -> None:
        self.project_repo = project_repo
        self.member_repo = member_repo
        self.role_repo = role_repo
        self.perm_svc = perm_svc or get_permission_service()

    def create_project(
        self, req: ProjectCreate, current_user: User, db: Session
    ) -> Project:
        # Org-level permission gate.
        self.perm_svc.require(
            current_user.id, Permission.PROJECTS_CREATE, None, db
        )
        project = self.project_repo.create(
            name=req.name, description=req.description, created_by_id=current_user.id
        )
        pm_role = self.role_repo.get_by_name("project_pm")
        if pm_role is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Built-in 'project_pm' role missing; bootstrap not run",
            )
        self.member_repo.add_member(project.id, current_user.id, pm_role.id)
        ensure_default_stages(db, project.id)
        ensure_default_rl_config(db, project.id)
        db.commit()
        db.refresh(project)
        return project

    def list_projects(self, current_user: User, db: Session) -> list[Project]:
        # Admins / org_pm see all; everyone else sees their memberships.
        if self.perm_svc.has(current_user.id, Permission.ORG_READ_USERS, None, db):
            return self.project_repo.list_all()
        return self.project_repo.list_for_user(current_user.id)

    def get_project(self, project_id: int, current_user: User, db: Session) -> Project:
        self.perm_svc.require(
            current_user.id, Permission.PROJECTS_READ, project_id, db
        )
        project = self.project_repo.get_by_id(project_id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project

    def update_project(
        self, project_id: int, req: ProjectUpdate, current_user: User, db: Session
    ) -> Project:
        self.perm_svc.require(
            current_user.id, Permission.PROJECTS_UPDATE, project_id, db
        )
        project = self.project_repo.get_by_id(project_id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        self.project_repo.update(project, **req.model_dump(exclude_unset=True))
        db.commit()
        db.refresh(project)
        return project

    def delete_project(self, project_id: int, current_user: User, db: Session) -> None:
        self.perm_svc.require(
            current_user.id, Permission.PROJECTS_DELETE, project_id, db
        )
        project = self.project_repo.get_by_id(project_id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        self.project_repo.delete(project)
        db.commit()
