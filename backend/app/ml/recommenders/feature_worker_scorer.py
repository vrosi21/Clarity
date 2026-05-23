"""
Scores eligible project workers for a partial (unsaved) ticket.

Supports multi-category tickets: when multiple categories are selected, the
proficiency score is a weighted average — the primary category (first in list)
gets 60 % of the weight, remaining categories share the other 40 % equally.
This mirrors the multi-hot encoding used in the RL state vector.

Score = proficiency × 0.5  +  (1 − load_ratio) × 0.3  +  nlp_sim × 0.2

Note: WorkerSkillProfile.worker_id is FK to worker_profiles.id (not users.id).
"""
from __future__ import annotations

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.permission_service import PermissionService
from app.core.permissions import Permission
from app.ml.base.recommender import BaseWorkerScorer, WorkerScore
from app.models.project_category_config import ProjectCategoryConfig
from app.models.project_member import ProjectMember
from app.models.ticket import Ticket
from app.models.user import User
from app.models.worker_profile import WorkerProfile
from app.models.worker_skill_profile import WorkerSkillProfile

_W_PROFICIENCY = 0.50
_W_LOAD = 0.30
_W_NLP = 0.20


class FeatureWorkerScorer(BaseWorkerScorer):
    def __init__(self, perm_svc: PermissionService) -> None:
        self._perm_svc = perm_svc

    def score(
        self,
        text: str,
        category_names: list[str],
        complexity: int,
        project_id: int,
        db: Session,
    ) -> list[WorkerScore]:
        rows = self._eligible_rows(project_id, db)
        if not rows:
            return []

        from app.models.category import Category
        # Resolve all category names to IDs in one query.
        cat_ids: list[int] = []
        if category_names:
            cat_rows = db.execute(
                select(Category).where(Category.name.in_(category_names))
            ).scalars().all()
            name_to_id = {c.name: c.id for c in cat_rows}
            cat_ids = [name_to_id[n] for n in category_names if n in name_to_id]

        primary_cat_id = cat_ids[0] if cat_ids else None

        ticket_emb = self._embed(text) if text.strip() else None

        results: list[WorkerScore] = []
        for user, wp, pm in rows:
            if not self._perm_svc.has(
                user.id, Permission.TICKETS_BE_ASSIGNED, project_id, db
            ):
                continue

            # Eligibility gates run on the primary (first) category only.
            if primary_cat_id:
                cfg = db.execute(
                    select(ProjectCategoryConfig).where(
                        ProjectCategoryConfig.project_id == project_id,
                        ProjectCategoryConfig.category_id == primary_cat_id,
                    )
                ).scalar_one_or_none()
                primary_prof = self._proficiency_for(wp.id, primary_cat_id, db)
                if cfg and primary_prof < float(cfg.min_proficiency):
                    continue
                if cfg and cfg.allowed_role_ids and pm.role_id not in cfg.allowed_role_ids:
                    continue

            # Aggregate proficiency across all selected categories.
            # Primary category gets 60 % weight; remaining share 40 % equally.
            proficiency = self._aggregate_proficiency(wp.id, cat_ids, db)

            load_ratio = self._load_ratio(user.id, wp, db)
            nlp_sim = self._nlp_sim(ticket_emb, wp.id, primary_cat_id, db)

            w_nlp = _W_NLP if nlp_sim is not None else 0.0
            w_prof = _W_PROFICIENCY + (_W_NLP - w_nlp)
            final_score = (
                w_prof * proficiency
                + _W_LOAD * (1.0 - load_ratio)
                + w_nlp * (nlp_sim or 0.0)
            )

            reasons = self._reasons(proficiency, load_ratio, nlp_sim, complexity, wp)
            results.append(
                WorkerScore(
                    user_id=user.id,
                    username=user.username,
                    score=round(float(final_score), 3),
                    proficiency=round(proficiency, 2),
                    load_ratio=round(load_ratio, 2),
                    reasons=reasons,
                )
            )

        results.sort(key=lambda w: w.score, reverse=True)
        return results[:5]

    def _eligible_rows(
        self, project_id: int, db: Session
    ) -> list[tuple[User, WorkerProfile, ProjectMember]]:
        return (
            db.execute(
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

    @staticmethod
    def _proficiency_for(worker_profile_id: int, cat_id: int, db: Session) -> float:
        sp = db.execute(
            select(WorkerSkillProfile).where(
                WorkerSkillProfile.worker_id == worker_profile_id,
                WorkerSkillProfile.category_id == cat_id,
            )
        ).scalar_one_or_none()
        return float(sp.proficiency) if sp else 0.15

    @staticmethod
    def _aggregate_proficiency(
        worker_profile_id: int, cat_ids: list[int], db: Session
    ) -> float:
        """Weighted average: primary category 60 %, remainder split equally over 40 %."""
        if not cat_ids:
            return 0.5  # no category info — neutral score
        if len(cat_ids) == 1:
            sp = db.execute(
                select(WorkerSkillProfile).where(
                    WorkerSkillProfile.worker_id == worker_profile_id,
                    WorkerSkillProfile.category_id == cat_ids[0],
                )
            ).scalar_one_or_none()
            return float(sp.proficiency) if sp else 0.15

        primary_w = 0.60
        other_w = 0.40 / (len(cat_ids) - 1)
        total = 0.0
        for i, cid in enumerate(cat_ids):
            w = primary_w if i == 0 else other_w
            sp = db.execute(
                select(WorkerSkillProfile).where(
                    WorkerSkillProfile.worker_id == worker_profile_id,
                    WorkerSkillProfile.category_id == cid,
                )
            ).scalar_one_or_none()
            total += w * (float(sp.proficiency) if sp else 0.15)
        return total

    @staticmethod
    def _load_ratio(user_id: int, wp: WorkerProfile, db: Session) -> float:
        rows = db.execute(
            select(Ticket.estimated_minutes).where(
                Ticket.assignee_id == user_id,
                Ticket.estimated_minutes.is_not(None),
            )
        ).scalars().all()
        load = sum(rows)
        return min(1.0, load / max(wp.burnout_threshold, 1))

    @staticmethod
    def _embed(text: str) -> np.ndarray | None:
        try:
            from app.ml.recommenders.embedding_category_recommender import (
                EmbeddingCategoryRecommender,
            )
            enc = EmbeddingCategoryRecommender._encoder
            if enc is None:
                return None
            raw = enc.encode([text.strip()])
            norm = np.linalg.norm(raw[0])
            return raw[0] / max(norm, 1e-8)
        except Exception:
            return None

    @staticmethod
    def _nlp_sim(
        ticket_emb: np.ndarray | None,
        worker_profile_id: int,
        cat_id: int | None,
        db: Session,
    ) -> float | None:
        if ticket_emb is None or cat_id is None:
            return None
        sp = db.execute(
            select(WorkerSkillProfile).where(
                WorkerSkillProfile.worker_id == worker_profile_id,
                WorkerSkillProfile.category_id == cat_id,
            )
        ).scalar_one_or_none()
        if sp is None or sp.nlp_embedding is None:
            return None
        try:
            worker_emb = np.array(sp.nlp_embedding, dtype=np.float32)
            return float(np.dot(ticket_emb, worker_emb))
        except Exception:
            return None

    @staticmethod
    def _reasons(
        proficiency: float,
        load_ratio: float,
        nlp_sim: float | None,
        complexity: int,
        wp: WorkerProfile,
    ) -> list[str]:
        reasons: list[str] = []
        if proficiency >= 0.8:
            reasons.append(f"Expert proficiency ({proficiency:.0%})")
        elif proficiency >= 0.5:
            reasons.append(f"Good proficiency ({proficiency:.0%})")
        else:
            reasons.append(f"Low proficiency ({proficiency:.0%})")

        if load_ratio <= 0.3:
            reasons.append("Low current load")
        elif load_ratio >= 0.8:
            reasons.append("⚠ Near burnout threshold")

        if nlp_sim is not None and nlp_sim >= 0.6:
            reasons.append("Strong NLP match on past work")

        seniority_rank = {"junior": 0, "mid": 1, "senior": 2, "lead": 3}
        seniority_val = wp.seniority.value if hasattr(wp.seniority, "value") else wp.seniority
        rank = seniority_rank.get(str(seniority_val), 0)
        if complexity >= 4 and rank >= 2:
            reasons.append(f"Senior enough for complexity {complexity}")
        elif complexity >= 4 and rank < 2:
            reasons.append(f"⚠ May struggle with complexity {complexity}")

        return reasons
