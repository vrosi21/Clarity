"""SimulationService — orchestrates synthetic/real team simulation runs.

Follows strict layering: no HTTP here. All DB access via repositories.
The Simulator from app.ml.simulation.simulator is the only ML dependency.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ml.simulation.simulator import Simulator
from app.ml.simulation.task import SimTask
from app.ml.simulation.worker import SENIORITY_RANK, SimWorker
from app.models.project_member import ProjectMember
from app.models.rl_project_config import RLProjectConfig
from app.models.synthetic_team import SyntheticTeam
from app.models.ticket import Ticket
from app.models.worker_profile import WorkerProfile
from app.models.worker_skill_profile import WorkerSkillProfile
from app.repositories.simulation_repository import SimulationRepository

_PRIORITY_MAP = {"p1": 1, "p2": 2, "p3": 3, "p4": 4, "p5": 5}


class SimulationService:
    def __init__(self, repo: SimulationRepository) -> None:
        self._repo = repo

    # ──────────────────────────────────── public API ───────────────────────────

    def run_project_simulation(
        self,
        project_id: int,
        user_id: int,
        team_source: str,
        synthetic_team_id: int | None,
        rl_config_overrides: dict[str, Any] | None,
        db: Session,
    ) -> Any:
        rl_config = (
            db.execute(
                select(RLProjectConfig).where(RLProjectConfig.project_id == project_id)
            ).scalar_one_or_none()
        )
        snapshot = self._config_snapshot(rl_config, rl_config_overrides or {})

        status = "completed"
        event_log: list[dict[str, Any]] = []
        summary: dict[str, Any] = {}

        try:
            if team_source == "synthetic":
                if synthetic_team_id is None:
                    raise ValueError("synthetic_team_id required when team_source='synthetic'")
                workers, worker_meta = self._build_sim_workers_from_team(synthetic_team_id, db)
            else:
                workers, worker_meta = self._build_sim_workers_from_profiles(project_id, db)

            tasks, task_meta = self._build_sim_tasks_from_project(project_id, db)

            if not workers:
                raise ValueError("No eligible workers found for simulation")
            if not tasks:
                raise ValueError("No tickets found for simulation")

            event_log = self._execute_simulation(
                workers, tasks, worker_meta, task_meta,
                temperature=float(snapshot.get("temperature", 0.3)),
            )
            summary = self._compute_summary(event_log, workers, tasks)
        except Exception:
            status = "failed"

        return self._repo.create_run(
            db=db,
            project_id=project_id,
            created_by=user_id,
            team_source=team_source,
            synthetic_team_id=synthetic_team_id,
            rl_config_snapshot=snapshot,
            event_log=event_log,
            summary=summary,
            status=status,
        )

    def get_run(self, run_id: int, db: Session) -> Any:
        return self._repo.get_run(db, run_id)

    def list_runs(self, project_id: int, db: Session) -> list[Any]:
        return self._repo.list_runs_for_project(db, project_id)

    def create_team(
        self, user_id: int, name: str, description: str | None, workers_data: list[dict], db: Session
    ) -> Any:
        return self._repo.create_team(db, name, description, user_id, workers_data)

    def list_teams(self, db: Session) -> list[Any]:
        return self._repo.list_teams(db)

    def get_team(self, team_id: int, db: Session) -> Any:
        return self._repo.get_team(db, team_id)

    def delete_team(self, team: Any, db: Session) -> None:
        self._repo.delete_team(db, team)

    # ──────────────────────────── builder helpers ──────────────────────────────

    def _build_sim_workers_from_profiles(
        self, project_id: int, db: Session
    ) -> tuple[list[SimWorker], dict[int, dict]]:
        """Convert real WorkerProfile + WorkerSkillProfile rows into SimWorker objects."""
        from app.models.category import Category
        from app.models.user import User

        member_rows = db.execute(
            select(ProjectMember).where(ProjectMember.project_id == project_id)
        ).scalars().all()
        user_ids = [m.user_id for m in member_rows]

        profiles = db.execute(
            select(WorkerProfile)
            .options(selectinload(WorkerProfile.skill_profiles))
            .where(WorkerProfile.user_id.in_(user_ids))
        ).scalars().all()
        profile_by_user: dict[int, WorkerProfile] = {p.user_id: p for p in profiles}

        users = db.execute(select(User).where(User.id.in_(user_ids))).scalars().all()
        user_names: dict[int, str] = {u.id: (u.full_name or u.username) for u in users}

        # category id → name lookup
        cat_rows = db.execute(select(Category)).scalars().all()
        cat_names: dict[int, str] = {c.id: c.name for c in cat_rows}

        workers: list[SimWorker] = []
        meta: dict[int, dict] = {}

        for member in member_rows:
            profile = profile_by_user.get(member.user_id)
            if profile is None or not profile.is_available:
                continue

            cat_proficiency: dict[str, float] = {
                cat_names.get(sp.category_id, str(sp.category_id)): sp.proficiency
                for sp in profile.skill_profiles
            }
            if not cat_proficiency:
                cat_proficiency = {"backend": 0.5}

            primary_cat = (
                cat_names.get(profile.primary_category_id, "backend")
                if profile.primary_category_id
                else next(iter(cat_proficiency))
            )

            sim_w = SimWorker(
                id=profile.id,
                seniority=profile.seniority.value if hasattr(profile.seniority, "value") else str(profile.seniority),
                years_experience=int(profile.years_experience),
                primary_category=primary_cat,
                category_proficiency=cat_proficiency,
                base_productivity=profile.base_productivity,
                burnout_threshold=profile.burnout_threshold,
                current_load=0,
                is_available=True,
            )
            workers.append(sim_w)
            meta[sim_w.id] = {
                "name": user_names.get(member.user_id, f"Worker {profile.id}"),
                "db_id": profile.id,
            }

        return workers, meta

    def _build_sim_workers_from_team(
        self, team_id: int, db: Session
    ) -> tuple[list[SimWorker], dict[int, dict]]:
        """Convert SyntheticWorker rows into SimWorker objects."""
        team = db.execute(
            select(SyntheticTeam)
            .options(selectinload(SyntheticTeam.workers))
            .where(SyntheticTeam.id == team_id)
        ).scalar_one_or_none()

        if team is None:
            raise ValueError(f"SyntheticTeam {team_id} not found")

        workers: list[SimWorker] = []
        meta: dict[int, dict] = {}

        for sw in team.workers:
            sim_w = SimWorker(
                id=sw.id,
                seniority=sw.seniority,
                years_experience=int(sw.years_experience),
                primary_category=sw.primary_category,
                category_proficiency=dict(sw.category_proficiency or {}),
                base_productivity=sw.base_productivity,
                burnout_threshold=sw.burnout_threshold,
                current_load=0,
                is_available=True,
            )
            workers.append(sim_w)
            meta[sim_w.id] = {"name": sw.name, "db_id": sw.id}

        return workers, meta

    def _build_sim_tasks_from_project(
        self, project_id: int, db: Session
    ) -> tuple[list[SimTask], dict[int, dict]]:
        """Convert Ticket rows into SimTask objects."""
        tickets = db.execute(
            select(Ticket)
            .options(selectinload(Ticket.category))
            .where(Ticket.project_id == project_id)
        ).scalars().all()

        tasks: list[SimTask] = []
        meta: dict[int, dict] = {}

        for t in tickets:
            category = t.category.name if t.category else "backend"
            priority = _PRIORITY_MAP.get(t.priority.value if hasattr(t.priority, "value") else str(t.priority), 3)
            estimated = t.estimated_minutes or 120

            sim_t = SimTask(
                id=t.id,
                category=category,
                complexity=t.complexity,
                priority=priority,
                estimated_minutes=estimated,
                requires_min_seniority=0,
            )
            tasks.append(sim_t)
            meta[t.id] = {"title": t.title}

        return tasks, meta

    # ──────────────────────────── simulation core ──────────────────────────────

    def _execute_simulation(
        self,
        workers: list[SimWorker],
        tasks: list[SimTask],
        worker_meta: dict[int, dict],
        task_meta: dict[int, dict],
        temperature: float = 0.3,
    ) -> list[dict[str, Any]]:
        # τ scales noise: low τ → tight, deterministic-ish outcomes; high τ → wide spread.
        # Range 0.05–1.0 mapped to sigma_multiplier 0.4–2.5.
        from app.ml.simulation.noise import LogNormalNoise
        sigma_mult = 0.4 + (temperature - 0.05) * (2.5 - 0.4) / (1.0 - 0.05)
        sim = Simulator(noise_strategy=LogNormalNoise(sigma_multiplier=sigma_mult))
        # Fresh seed per call so identical configs still produce variance.
        seed = int(np.random.SeedSequence().entropy % (2**31 - 1))
        rng = np.random.default_rng(seed)
        sim._assign_arrival_times(tasks, rng)
        rows = sim._simulate(workers, tasks, rng, sprint_id=0)  # noqa: SLF001

        events: list[dict[str, Any]] = []
        for row in rows:
            task_id = int(row["task_id"])
            worker_id = int(row["worker_id"])
            t_arrive = float(row.get("arrival_time", 0.0))
            t_complete = float(row.get("completion_time", 0.0))
            was_blocked = bool(row.get("was_blocked", False))

            w_name = worker_meta.get(worker_id, {}).get("name", f"Worker {worker_id}")
            t_title = task_meta.get(task_id, {}).get("title", f"Ticket {task_id}")

            duration = max(t_complete - t_arrive, 1.0)

            # BACKLOG → ASSIGNED
            events.append({
                "t": round(t_arrive, 2),
                "type": "assigned",
                "ticket_id": task_id,
                "ticket_title": t_title,
                "worker_id": worker_id,
                "worker_name": w_name,
                "from_stage": "BACKLOG",
                "to_stage": "ASSIGNED",
                "q_value": None,
            })

            # ASSIGNED → IN_PROGRESS (worker picks it up shortly after)
            t_start = round(t_arrive + duration * 0.05, 2)
            events.append({
                "t": t_start,
                "type": "stage_changed",
                "ticket_id": task_id,
                "ticket_title": t_title,
                "worker_id": worker_id,
                "worker_name": w_name,
                "from_stage": "ASSIGNED",
                "to_stage": "IN_PROGRESS",
                "q_value": None,
            })

            if was_blocked:
                # IN_PROGRESS → BLOCKED → IN_PROGRESS (mid-work interruption)
                t_blocked = round(t_arrive + duration * 0.4, 2)
                events.append({
                    "t": t_blocked,
                    "type": "blocked",
                    "ticket_id": task_id,
                    "ticket_title": t_title,
                    "worker_id": worker_id,
                    "worker_name": w_name,
                    "from_stage": "IN_PROGRESS",
                    "to_stage": "BLOCKED",
                    "q_value": None,
                })
                events.append({
                    "t": round(t_blocked + (t_complete - t_blocked) * 0.3, 2),
                    "type": "stage_changed",
                    "ticket_id": task_id,
                    "ticket_title": t_title,
                    "worker_id": worker_id,
                    "worker_name": w_name,
                    "from_stage": "BLOCKED",
                    "to_stage": "IN_PROGRESS",
                    "q_value": None,
                })

            # IN_PROGRESS → IN_REVIEW (just before completion)
            t_review = round(t_complete - max(duration * 0.05, 1.0), 2)
            events.append({
                "t": t_review,
                "type": "stage_changed",
                "ticket_id": task_id,
                "ticket_title": t_title,
                "worker_id": worker_id,
                "worker_name": w_name,
                "from_stage": "IN_PROGRESS",
                "to_stage": "IN_REVIEW",
                "q_value": None,
            })

            # IN_REVIEW → DONE
            events.append({
                "t": round(t_complete, 2),
                "type": "completed",
                "ticket_id": task_id,
                "ticket_title": t_title,
                "worker_id": worker_id,
                "worker_name": w_name,
                "from_stage": "IN_REVIEW",
                "to_stage": "DONE",
                "q_value": None,
            })

        events.sort(key=lambda e: e["t"])
        return events

    # ──────────────────────────── summary ─────────────────────────────────────

    @staticmethod
    def _compute_summary(
        events: list[dict[str, Any]],
        workers: list[SimWorker],
        tasks: list[SimTask],
    ) -> dict[str, Any]:
        completed = [e for e in events if e["type"] == "completed"]
        total_time = max((e["t"] for e in completed), default=0.0)

        task_map = {t.id: t for t in tasks}
        efficiency_ratios: list[float] = []
        assigned_events = {e["ticket_id"]: e for e in events if e["type"] == "assigned"}
        for e in completed:
            tid = e["ticket_id"]
            task = task_map.get(tid)
            if task and tid in assigned_events:
                actual = e["t"] - assigned_events[tid]["t"]
                if task.estimated_minutes > 0 and actual > 0:
                    efficiency_ratios.append(actual / task.estimated_minutes)

        avg_eff = float(np.mean(efficiency_ratios)) if efficiency_ratios else 0.0
        n_blocked = sum(1 for e in events if e["type"] == "blocked")

        return {
            "total_time": round(total_time, 2),
            "avg_efficiency": round(avg_eff, 4),
            "n_tasks": len(tasks),
            "n_blocked": n_blocked,
            "n_workers": len(workers),
        }

    # ──────────────────────────── config snapshot ──────────────────────────────

    @staticmethod
    def _config_snapshot(
        config: RLProjectConfig | None, overrides: dict[str, Any]
    ) -> dict[str, Any]:
        base: dict[str, Any] = {
            "temperature": 0.3,
            "w_priority": 1.0,
            "w_efficiency": 1.0,
            "w_overload": 2.0,
            "w_throughput": 0.5,
            "gamma": 0.9,
        }
        if config:
            base.update({
                "temperature": config.temperature,
                "w_priority": config.w_priority,
                "w_efficiency": config.w_efficiency,
                "w_overload": config.w_overload,
                "w_throughput": config.w_throughput,
                "gamma": config.gamma,
            })
        for k, v in overrides.items():
            if v is not None:
                base[k] = v
        return base
