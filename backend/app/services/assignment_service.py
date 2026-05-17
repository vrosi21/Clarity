"""RL-driven assignment service.

Bridges the DB world (User / WorkerProfile / Ticket) to the simulation world
(SimWorker / SimTask) so the same state-builder / policy code used in the
notebooks runs in production unchanged.

Policy fallback chain:
    1. RL policy if a Q-network and regressor are loaded.
    2. Greedy policy if only the regressor is loaded.
    3. Heuristic random-among-most-proficient if neither is loaded.

That fallback is deliberate — the backend has to be useful even before the
notebooks have produced any artefacts.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ml.agent.state_builder import build_state_vector
from app.ml.policies.greedy_policy import GreedyPolicy
from app.ml.policies.rl_policy import RLPolicy
from app.ml.registry import ModelRegistry
from app.ml.simulation.task import SimTask
from app.ml.simulation.worker import (
    CANONICAL_CATEGORIES,
    SENIORITY_RANK,
    SimWorker,
)
from app.core.permission_service import PermissionService, get_permission_service
from app.core.permissions import Permission
from app.models.assignment_record import AssignmentRecord
from app.models.category import Category
from app.models.enums import TicketPriority
from app.models.project_category_config import ProjectCategoryConfig
from app.models.project_member import ProjectMember
from app.models.rl_project_config import RLProjectConfig
from app.models.ticket import Ticket
from app.models.user import User
from app.models.worker_profile import WorkerProfile
from app.models.worker_skill_profile import WorkerSkillProfile
from app.repositories.member_repository import MemberRepository
from app.repositories.ticket_repository import TicketRepository


_PRIORITY_TO_INT = {
    TicketPriority.P1: 1,
    TicketPriority.P2: 2,
    TicketPriority.P3: 3,
    TicketPriority.P4: 4,
    TicketPriority.P5: 5,
}


@dataclass
class CandidateSuggestion:
    user_id: int
    username: str
    q_value: float | None
    probability: float | None
    proficiency: float
    load_ratio: float


@dataclass
class AssignmentResult:
    ticket_id: int
    assigned_user_id: int
    policy_used: str
    q_value: float | None
    suggestions: list[CandidateSuggestion]


class AssignmentService:
    def __init__(
        self,
        db: Session,
        ticket_repo: TicketRepository,
        member_repo: MemberRepository,
        registry: ModelRegistry,
        perm_svc: PermissionService | None = None,
    ) -> None:
        self.db = db
        self.ticket_repo = ticket_repo
        self.member_repo = member_repo
        self.registry = registry
        self.perm_svc = perm_svc or get_permission_service()

    def assign(
        self,
        project_id: int,
        ticket_id: int,
        current_user: User,
        commit: bool = True,
    ) -> AssignmentResult:
        self.perm_svc.require(
            current_user.id, Permission.TICKETS_ASSIGN, project_id, self.db
        )
        ticket = self.ticket_repo.get_by_id(ticket_id)
        if ticket is None or ticket.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
            )

        sim_task = self._ticket_to_sim_task(ticket)
        candidates, sim_workers = self._candidates(project_id, ticket)
        if not candidates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No eligible workers (need project members with worker profiles)",
            )

        config = self._rl_config(project_id)
        result = self._select(sim_task, sim_workers, candidates, config)

        # Persist assignment.
        ticket.assignee_id = result.assigned_user_id
        rec = AssignmentRecord(
            ticket_id=ticket.id,
            worker_id=self._worker_profile_id(result.assigned_user_id, candidates),
            estimated_minutes=ticket.estimated_minutes or 0,
            rl_q_value=result.q_value,
        )
        self.db.add(rec)
        if commit:
            self.db.commit()
        return result

    def suggestions(
        self, project_id: int, ticket_id: int, current_user: User
    ) -> list[CandidateSuggestion]:
        """Return ranked suggestions without persisting an assignment."""
        self.perm_svc.require(
            current_user.id, Permission.TICKETS_READ, project_id, self.db
        )
        ticket = self.ticket_repo.get_by_id(ticket_id)
        if ticket is None or ticket.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found"
            )
        sim_task = self._ticket_to_sim_task(ticket)
        candidates, sim_workers = self._candidates(project_id, ticket)
        if not candidates:
            return []

        config = self._rl_config(project_id)
        result = self._select(sim_task, sim_workers, candidates, config)
        # Sort by q_value desc (or by negative load if no q_value).
        return sorted(
            result.suggestions,
            key=lambda c: (c.q_value if c.q_value is not None else -c.load_ratio),
            reverse=True,
        )

    # ------------------------------------------------------------------

    def _candidates(
        self, project_id: int, ticket: Ticket
    ) -> tuple[list[tuple[User, WorkerProfile]], list[SimWorker]]:
        rows = (
            self.db.execute(
                select(User, WorkerProfile, ProjectMember)
                .join(ProjectMember, ProjectMember.user_id == User.id)
                .join(WorkerProfile, WorkerProfile.user_id == User.id)
                .options(selectinload(WorkerProfile.skill_profiles))
                .where(
                    ProjectMember.project_id == project_id,
                    WorkerProfile.is_available.is_(True),
                )
            )
            .unique()
            .all()
        )

        # Apply P5 eligibility gates in order.
        filtered = self._filter_by_be_assigned(rows, project_id)
        filtered = self._filter_by_category_min_proficiency(filtered, ticket, project_id)
        filtered = self._filter_by_allowed_roles(filtered, ticket, project_id)

        candidates = [(u, wp) for u, wp, _ in filtered]

        # Build category id → name lookup once.
        cat_rows = self.db.execute(select(Category)).scalars().all()
        cat_name = {c.id: c.name for c in cat_rows}

        sim_workers: list[SimWorker] = []
        for user, wp in candidates:
            proficiency = {c: 0.15 for c in CANONICAL_CATEGORIES}
            for sp in wp.skill_profiles:
                name = cat_name.get(sp.category_id)
                if name in proficiency:
                    proficiency[name] = float(sp.proficiency)
            primary = cat_name.get(wp.primary_category_id) if wp.primary_category_id else "backend"
            if primary not in CANONICAL_CATEGORIES:
                primary = "backend"
            sim_workers.append(
                SimWorker(
                    id=user.id,
                    seniority=wp.seniority.value,  # enum → str
                    years_experience=wp.years_experience,
                    primary_category=primary,
                    category_proficiency=proficiency,
                    base_productivity=float(wp.base_productivity),
                    burnout_threshold=int(wp.burnout_threshold),
                    current_load=self._current_load(user.id),
                    is_available=bool(wp.is_available),
                )
            )
        return candidates, sim_workers

    def _filter_by_be_assigned(
        self,
        rows: list[tuple[User, WorkerProfile, ProjectMember]],
        project_id: int,
    ) -> list[tuple[User, WorkerProfile, ProjectMember]]:
        return [
            (u, wp, pm)
            for u, wp, pm in rows
            if self.perm_svc.has(u.id, Permission.TICKETS_BE_ASSIGNED, project_id, self.db)
        ]

    def _filter_by_category_min_proficiency(
        self,
        rows: list[tuple[User, WorkerProfile, ProjectMember]],
        ticket: Ticket,
        project_id: int,
    ) -> list[tuple[User, WorkerProfile, ProjectMember]]:
        if not ticket.category_id:
            return rows
        config = self.db.execute(
            select(ProjectCategoryConfig).where(
                ProjectCategoryConfig.project_id == project_id,
                ProjectCategoryConfig.category_id == ticket.category_id,
            )
        ).scalar_one_or_none()
        min_prof = float(config.min_proficiency) if config else 0.0
        if min_prof <= 0.0:
            return rows

        def _proficiency(user: User) -> float:
            sp = self.db.execute(
                select(WorkerSkillProfile).where(
                    WorkerSkillProfile.user_id == user.id,
                    WorkerSkillProfile.category_id == ticket.category_id,
                )
            ).scalar_one_or_none()
            return float(sp.proficiency) if sp else 0.0

        return [(u, wp, pm) for u, wp, pm in rows if _proficiency(u) >= min_prof]

    def _filter_by_allowed_roles(
        self,
        rows: list[tuple[User, WorkerProfile, ProjectMember]],
        ticket: Ticket,
        project_id: int,
    ) -> list[tuple[User, WorkerProfile, ProjectMember]]:
        if not ticket.category_id:
            return rows
        config = self.db.execute(
            select(ProjectCategoryConfig).where(
                ProjectCategoryConfig.project_id == project_id,
                ProjectCategoryConfig.category_id == ticket.category_id,
            )
        ).scalar_one_or_none()
        allowed = config.allowed_role_ids if config else None
        if allowed is None:
            return rows
        allowed_set = set(allowed)
        return [(u, wp, pm) for u, wp, pm in rows if pm.role_id in allowed_set]

    def _ticket_to_sim_task(self, ticket: Ticket) -> SimTask:
        category_name = ticket.category.name if ticket.category else "backend"
        if category_name not in CANONICAL_CATEGORIES:
            category_name = "backend"
        return SimTask(
            id=ticket.id,
            category=category_name,
            complexity=int(ticket.complexity),
            priority=_PRIORITY_TO_INT.get(ticket.priority, 3),
            estimated_minutes=int(ticket.estimated_minutes or 60),
            requires_min_seniority=0,
        )

    def _current_load(self, user_id: int) -> int:
        rows = self.db.execute(
            select(Ticket.estimated_minutes).where(
                Ticket.assignee_id == user_id,
                Ticket.estimated_minutes.is_not(None),
            )
        ).all()
        return int(sum(r[0] for r in rows))

    def _rl_config(self, project_id: int) -> RLProjectConfig:
        cfg = self.db.execute(
            select(RLProjectConfig).where(RLProjectConfig.project_id == project_id)
        ).scalar_one_or_none()
        if cfg is not None:
            return cfg
        # Synthesise defaults if none exists.
        return RLProjectConfig(project_id=project_id)

    def _worker_profile_id(
        self, user_id: int, candidates: list[tuple[User, WorkerProfile]]
    ) -> int:
        for u, wp in candidates:
            if u.id == user_id:
                return wp.id
        raise RuntimeError("worker profile id lookup failed")

    def _select(
        self,
        sim_task: SimTask,
        sim_workers: list[SimWorker],
        candidates: list[tuple[User, WorkerProfile]],
        config: RLProjectConfig,
    ) -> AssignmentResult:
        regressor = self.registry.regressor
        q_network = self.registry.q_network

        # Build state vectors only when regressor exists (state vector embeds
        # regressor.predict at index 13).
        state_vectors = None
        if regressor is not None:
            state_vectors = [
                build_state_vector(sim_task, sw, regressor) for sw in sim_workers
            ]

        if state_vectors is not None and q_network is not None:
            policy_name = "rl"
            policy = RLPolicy(q_network)
            chosen_idx = policy.select_worker(state_vectors, tau=float(config.temperature))
            q_values = policy.q_values(state_vectors).tolist()
            probs = policy.probabilities(state_vectors, tau=float(config.temperature)).tolist()
        elif state_vectors is not None:
            policy_name = "greedy"
            policy = GreedyPolicy()
            chosen_idx = policy.select_worker(state_vectors)
            q_values = [None] * len(sim_workers)
            probs = [None] * len(sim_workers)
        else:
            policy_name = "heuristic-random"
            chosen_idx = self._heuristic_pick(sim_task, sim_workers)
            q_values = [None] * len(sim_workers)
            probs = [None] * len(sim_workers)

        chosen_user = candidates[chosen_idx][0]
        suggestions = [
            CandidateSuggestion(
                user_id=u.id,
                username=u.username,
                q_value=q_values[i],
                probability=probs[i],
                proficiency=sim_workers[i].category_proficiency.get(
                    sim_task.category, 0.15
                ),
                load_ratio=sim_workers[i].load_ratio(),
            )
            for i, (u, _) in enumerate(candidates)
        ]
        return AssignmentResult(
            ticket_id=sim_task.id,
            assigned_user_id=chosen_user.id,
            policy_used=policy_name,
            q_value=q_values[chosen_idx],
            suggestions=suggestions,
        )

    @staticmethod
    def _heuristic_pick(task: SimTask, workers: list[SimWorker]) -> int:
        """Pick among the top-3 most proficient workers, random tie-break."""
        ranked = sorted(
            range(len(workers)),
            key=lambda i: (
                -workers[i].category_proficiency.get(task.category, 0.0),
                workers[i].load_ratio(),
                # Lower rank = lower seniority = lower index priority for high complexity.
                -SENIORITY_RANK.get(workers[i].seniority, 0)
                if task.complexity >= 4
                else 0,
            ),
        )
        top = ranked[: min(3, len(ranked))]
        return random.choice(top)
