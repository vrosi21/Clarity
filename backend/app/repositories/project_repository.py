from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_member import ProjectMember


class ProjectRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, project_id: int) -> Project | None:
        return self.db.get(Project, project_id)

    def list_for_user(self, user_id: int) -> list[Project]:
        stmt = (
            select(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == user_id)
            .order_by(Project.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_all(self) -> list[Project]:
        return list(
            self.db.execute(
                select(Project).order_by(Project.created_at.desc())
            ).scalars().all()
        )

    def create(
        self,
        name: str,
        description: str | None,
        created_by_id: int | None = None,
    ) -> Project:
        project = Project(
            name=name, description=description, created_by_id=created_by_id
        )
        self.db.add(project)
        self.db.flush()
        return project

    def update(self, project: Project, **fields) -> Project:
        for k, v in fields.items():
            setattr(project, k, v)
        self.db.flush()
        return project

    def delete(self, project: Project) -> None:
        self.db.delete(project)
        self.db.flush()
