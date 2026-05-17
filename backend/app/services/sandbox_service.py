"""Sandbox seeding — generates bot workers + synthetic tickets for a project.

The sandbox lets users (or graders) populate a project with realistic
synthetic data in one click, exercising the assignment engine end-to-end.

Bot users are real `User` rows with hashed passwords and the email pattern
`bot+<n>@sandbox.<project_id>.local` so they can be cleanly removed by the
reset endpoint without touching real users.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permission_service import PermissionService, get_permission_service
from app.core.permissions import Permission
from app.core.security import hash_password
from app.ml.simulation.generator import TaskGenerator, WorkerGenerator
from app.ml.simulation.task import SimTask
from app.ml.simulation.worker import SENIORITY_RANK, SimWorker
from app.models.category import Category
from app.models.enums import (
    SeniorityLevel,
    StageType,
    TicketPriority,
)
from app.models.project_member import ProjectMember
from app.models.role import Role
from app.models.stage import Stage
from app.models.ticket import Ticket
from app.models.user import User
from app.models.worker_profile import WorkerProfile
from app.models.worker_skill_profile import WorkerSkillProfile
from app.repositories.member_repository import MemberRepository
from app.repositories.stage_repository import StageRepository
from app.schemas.sandbox import SandboxResetResponse, SandboxSeedResponse
from app.services.bootstrap import (
    ensure_canonical_categories,
    ensure_default_stages,
)

_PRIORITY_BY_INT = {
    1: TicketPriority.P1,
    2: TicketPriority.P2,
    3: TicketPriority.P3,
    4: TicketPriority.P4,
    5: TicketPriority.P5,
}

_SENIORITY_MAP = {
    "junior": SeniorityLevel.JUNIOR,
    "mid": SeniorityLevel.MID,
    "senior": SeniorityLevel.SENIOR,
    "lead": SeniorityLevel.LEAD,
}


def _bot_email(project_id: int, n: int) -> str:
    # Use a non-reserved TLD so EmailStr validates successfully when this
    # value is serialised in MemberResponse / UserResponse.
    return f"bot+{n}@p{project_id}.clarity-bot.dev"


@dataclass
class SandboxService:
    db: Session
    member_repo: MemberRepository
    stage_repo: StageRepository
    perm_svc: PermissionService = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.perm_svc is None:
            self.perm_svc = get_permission_service()

    def _worker_role_id(self) -> int:
        role = self.db.execute(
            select(Role).where(Role.name == "worker")
        ).scalar_one_or_none()
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Built-in 'worker' role missing; bootstrap not run",
            )
        return role.id

    def seed(
        self,
        project_id: int,
        current_user: User,
        n_workers: int,
        n_tickets: int,
        seed: int | None,
        reset_first: bool,
    ) -> SandboxSeedResponse:
        self.perm_svc.require(
            current_user.id, Permission.PROJECTS_MANAGE_SETTINGS, project_id, self.db
        )

        if reset_first:
            self._reset(project_id)

        # Ensure project has stages + categories — sandbox should work even on
        # a fresh project that was created before bootstrap was wired in.
        ensure_canonical_categories(self.db)
        stages = ensure_default_stages(self.db, project_id)

        start_stage = next(
            (s for s in stages if s.type == StageType.START),
            None,
        )
        if start_stage is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project has no START stage; cannot seed",
            )

        categories: list[Category] = list(self.db.execute(select(Category)).scalars().all())
        cat_by_name = {c.name: c for c in categories}

        sim_workers: list[SimWorker] = WorkerGenerator().generate(n_workers, seed=seed)
        sim_tasks: list[SimTask] = TaskGenerator().generate(
            n_tickets, seed=(seed + 1 if seed is not None else None)
        )

        worker_role_id = self._worker_role_id()
        bot_user_ids: list[int] = []
        for sw in sim_workers:
            user = self._create_bot_user(project_id, sw)
            bot_user_ids.append(user.id)
            self.db.add(
                ProjectMember(
                    project_id=project_id,
                    user_id=user.id,
                    role_id=worker_role_id,
                )
            )
            self.db.flush()
            primary_id = (
                cat_by_name[sw.primary_category].id
                if sw.primary_category in cat_by_name
                else None
            )
            profile = WorkerProfile(
                user_id=user.id,
                seniority=_SENIORITY_MAP[sw.seniority],
                years_experience=sw.years_experience,
                primary_category_id=primary_id,
                base_productivity=sw.base_productivity,
                burnout_threshold=sw.burnout_threshold,
                is_available=sw.is_available,
            )
            self.db.add(profile)
            self.db.flush()
            for cat_name, prof in sw.category_proficiency.items():
                cat = cat_by_name.get(cat_name)
                if cat is None:
                    continue
                self.db.add(
                    WorkerSkillProfile(
                        worker_id=profile.id,
                        category_id=cat.id,
                        proficiency=float(prof),
                    )
                )
        self.db.flush()

        for st in sim_tasks:
            cat = cat_by_name.get(st.category)
            self.db.add(
                Ticket(
                    project_id=project_id,
                    stage_id=start_stage.id,
                    title=f"[sandbox] {st.category} #{st.id}",
                    description=(
                        f"Synthetic task — complexity={st.complexity}, "
                        f"requires_min_seniority={st.requires_min_seniority}"
                    ),
                    priority=_PRIORITY_BY_INT[st.priority],
                    complexity=st.complexity,
                    category_id=cat.id if cat else None,
                    estimated_minutes=st.estimated_minutes,
                )
            )
        self.db.flush()
        self.db.commit()

        return SandboxSeedResponse(
            project_id=project_id,
            workers_created=len(sim_workers),
            tickets_created=len(sim_tasks),
            bot_user_ids=bot_user_ids,
        )

    def reset(
        self, project_id: int, current_user: User
    ) -> SandboxResetResponse:
        self.perm_svc.require(
            current_user.id, Permission.PROJECTS_MANAGE_SETTINGS, project_id, self.db
        )
        result = self._reset(project_id)
        self.db.commit()
        return result

    # --- internal -----------------------------------------------------------

    def _create_bot_user(self, project_id: int, sw: SimWorker) -> User:
        email = _bot_email(project_id, sw.id)
        existing = self.db.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        user = User(
            email=email,
            username=f"bot-{sw.primary_category}-{sw.id}",
            # Random password — bots are not meant to log in.
            hashed_password=hash_password(secrets.token_urlsafe(16)),
        )
        self.db.add(user)
        self.db.flush()
        return user

    def _reset(self, project_id: int) -> SandboxResetResponse:
        # Find sandbox-owned tickets (those with the [sandbox] prefix).
        sandbox_tickets = (
            self.db.execute(
                select(Ticket).where(
                    Ticket.project_id == project_id,
                    Ticket.title.like("[sandbox]%"),
                )
            )
            .scalars()
            .all()
        )
        for t in sandbox_tickets:
            self.db.delete(t)

        # Find bot users — by email pattern.
        bot_users = (
            self.db.execute(
                select(User).where(
                    User.email.like(f"bot+%@p{project_id}.clarity-bot.dev")
                )
            )
            .scalars()
            .all()
        )
        for u in bot_users:
            # Cascade-deletes will clean up: ProjectMember, WorkerProfile,
            # WorkerSkillProfile, AssignmentRecord, Ticket-as-assignee (SET NULL).
            self.db.delete(u)
        self.db.flush()

        return SandboxResetResponse(
            project_id=project_id,
            workers_removed=len(bot_users),
            tickets_removed=len(sandbox_tickets),
        )
