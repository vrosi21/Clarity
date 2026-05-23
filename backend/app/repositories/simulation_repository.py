from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.simulation_run import SimulationRun
from app.models.synthetic_team import SyntheticTeam
from app.models.synthetic_worker import SyntheticWorker


class SimulationRepository:

    # ── Synthetic teams ────────────────────────────────────────────────────────

    def create_team(
        self,
        db: Session,
        name: str,
        description: str | None,
        created_by: int,
        workers_data: list[dict[str, Any]],
    ) -> SyntheticTeam:
        team = SyntheticTeam(name=name, description=description, created_by=created_by)
        db.add(team)
        db.flush()
        for w in workers_data:
            db.add(SyntheticWorker(team_id=team.id, **w))
        db.flush()
        db.refresh(team)
        return team

    def get_team(self, db: Session, team_id: int) -> SyntheticTeam | None:
        return db.execute(
            select(SyntheticTeam)
            .options(selectinload(SyntheticTeam.workers))
            .where(SyntheticTeam.id == team_id)
        ).scalar_one_or_none()

    def list_teams(self, db: Session) -> list[SyntheticTeam]:
        return list(
            db.execute(
                select(SyntheticTeam)
                .options(selectinload(SyntheticTeam.workers))
                .order_by(SyntheticTeam.created_at.desc())
            ).scalars().all()
        )

    def delete_team(self, db: Session, team: SyntheticTeam) -> None:
        db.delete(team)
        db.flush()

    # ── Simulation runs ────────────────────────────────────────────────────────

    def create_run(
        self,
        db: Session,
        project_id: int,
        created_by: int,
        team_source: str,
        synthetic_team_id: int | None,
        rl_config_snapshot: dict[str, Any],
        event_log: list[dict[str, Any]],
        summary: dict[str, Any],
        status: str,
    ) -> SimulationRun:
        run = SimulationRun(
            project_id=project_id,
            created_by=created_by,
            team_source=team_source,
            synthetic_team_id=synthetic_team_id,
            rl_config_snapshot=rl_config_snapshot,
            event_log=event_log,
            summary=summary,
            status=status,
        )
        db.add(run)
        db.flush()
        db.refresh(run)
        return run

    def get_run(self, db: Session, run_id: int) -> SimulationRun | None:
        return db.execute(
            select(SimulationRun).where(SimulationRun.id == run_id)
        ).scalar_one_or_none()

    def list_runs_for_project(
        self, db: Session, project_id: int
    ) -> list[SimulationRun]:
        return list(
            db.execute(
                select(SimulationRun)
                .where(SimulationRun.project_id == project_id)
                .order_by(SimulationRun.created_at.desc())
            ).scalars().all()
        )
