from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rl_project_config import RLProjectConfig


class RLConfigRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_project(self, project_id: int) -> RLProjectConfig | None:
        stmt = select(RLProjectConfig).where(RLProjectConfig.project_id == project_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def upsert(self, project_id: int, **fields) -> RLProjectConfig:
        config = self.get_for_project(project_id)
        if config is None:
            config = RLProjectConfig(project_id=project_id)
            self.db.add(config)
        for k, v in fields.items():
            if v is not None:
                setattr(config, k, v)
        self.db.flush()
        return config
