import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.permissions import Permission
from app.models.user import User
from app.repositories.category_repository import CategoryRepository
from app.repositories.member_repository import MemberRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.stage_repository import StageRepository
from app.repositories.tag_repository import TagRepository
from app.repositories.ticket_repository import TicketRepository
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.schemas.task_generation import GenerateTasksRequest
from app.services.project_service import ProjectService
from app.services.task_generation_service import TaskGenerationService

router = APIRouter(prefix="/projects", tags=["projects"])


def _service(db: Session) -> ProjectService:
    return ProjectService(
        ProjectRepository(db), MemberRepository(db), RoleRepository(db)
    )


def _gen_service(db: Session) -> TaskGenerationService:
    return TaskGenerationService(
        CategoryRepository(db),
        StageRepository(db),
        TagRepository(db),
        TicketRepository(db),
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


@router.post("/{project_id}/generate-tasks")
async def generate_tasks_for_project(
    project_id: int,
    req: GenerateTasksRequest,
    current_user: Annotated[
        User, Depends(require_permission(Permission.SIMULATION_RUN, project_id_param=None))
    ],
) -> StreamingResponse:
    """Stream AI-generated tickets as SSE.

    Phases (events):
      - "diffusion" → category diffusion plan
      - "batch"     → one persisted batch of tickets (repeats)
      - "done"      → completion
      - "error"     → terminal failure
    """
    # Resolve project name/description up-front in a short-lived session.
    with SessionLocal() as ro_db:
        project = ProjectRepository(ro_db).get_by_id(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        project_name = project.name
        project_description = project.description

    config = req.generation_config.model_dump()

    async def event_stream():
        # Use a fresh session for the streaming task — request session lifetime
        # is too short to outlive an async loop.
        db = SessionLocal()
        try:
            svc = _gen_service(db)
            async for event in svc.stream_generation(
                project_id=project_id,
                project_name=project_name,
                project_description=project_description,
                config=config,
                db=db,
            ):
                payload = json.dumps(event)
                yield f"event: {event['type']}\ndata: {payload}\n\n"
        except Exception as exc:
            payload = json.dumps({"type": "error", "data": {"message": str(exc)}})
            yield f"event: error\ndata: {payload}\n\n"
        finally:
            db.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
