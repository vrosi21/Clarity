from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.repositories.member_repository import MemberRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.role_repository import RoleRepository
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


def _service(db: Session) -> ProjectService:
    return ProjectService(
        ProjectRepository(db), MemberRepository(db), RoleRepository(db)
    )


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ProjectResponse]:
    projects = _service(db).list_projects(current_user, db)
    return [ProjectResponse.model_validate(p) for p in projects]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    req: ProjectCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProjectResponse:
    project = _service(db).create_project(req, current_user, db)
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProjectResponse:
    return ProjectResponse.model_validate(
        _service(db).get_project(project_id, current_user, db)
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    req: ProjectUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProjectResponse:
    return ProjectResponse.model_validate(
        _service(db).update_project(project_id, req, current_user, db)
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    _service(db).delete_project(project_id, current_user, db)
