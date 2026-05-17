from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.stage import Stage


class StageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, stage_id: int) -> Stage | None:
        return self.db.get(Stage, stage_id)

    def list_for_project(self, project_id: int) -> list[Stage]:
        stmt = (
            select(Stage)
            .where(Stage.project_id == project_id)
            .order_by(Stage.order.asc(), Stage.id.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(self, project_id: int, **fields) -> Stage:
        stage = Stage(project_id=project_id, **fields)
        self.db.add(stage)
        self.db.flush()
        return stage

    def update(self, stage: Stage, **fields) -> Stage:
        for k, v in fields.items():
            setattr(stage, k, v)
        self.db.flush()
        return stage

    def delete(self, stage: Stage) -> None:
        self.db.delete(stage)
        self.db.flush()

    def reorder(self, project_id: int, ordered_ids: list[int]) -> list[Stage]:
        stages = self.list_for_project(project_id)
        by_id = {s.id: s for s in stages}
        for index, sid in enumerate(ordered_ids):
            if sid in by_id:
                by_id[sid].order = index
        self.db.flush()
        return self.list_for_project(project_id)
