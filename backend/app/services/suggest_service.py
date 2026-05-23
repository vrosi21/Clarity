"""Orchestrates LangChain-driven suggestions.

Four concurrent tasks: complexity, category, tags, workers.
Each is independently nullable — one failing does not affect the others.
Caller (router) always returns 200, never 5xx.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml.langchain.category_suggester import suggest_category
from app.ml.langchain.complexity import classify_complexity
from app.ml.langchain.output_schemas import (
    CategoryOutput,
    ComplexityOutput,
    SkillOutput,
    TagOutput,
)
from app.ml.langchain.skill_extractor import extract_skills
from app.ml.langchain.tag_suggester import suggest_tags
from app.models.category import Category
from app.models.tag import Tag


@dataclass
class TicketSuggestResult:
    complexity: ComplexityOutput | None
    category: CategoryOutput | None
    tags: TagOutput | None
    workers: list = field(default_factory=list)


@dataclass
class SkillSuggestResult:
    skills: SkillOutput | None


class SuggestService:
    async def suggest_for_ticket(
        self,
        title: str,
        description: str | None,
        project_id: int,
        category_ids: list[int],
        complexity: int | None,
        db: Session,
    ) -> TicketSuggestResult:
        text = f"{title}\n\n{description or ''}".strip()
        if not text:
            return TicketSuggestResult(complexity=None, category=None, tags=None)

        existing_categories = [
            {"id": c.id, "name": c.name, "description": c.description}
            for c in db.execute(select(Category)).scalars().all()
        ]
        existing_tags = [
            t.name for t in db.execute(select(Tag)).scalars().all()
        ]

        complexity_result, category, tags = await asyncio.gather(
            classify_complexity(text),
            suggest_category(text, existing_categories),
            suggest_tags(text, existing_tags),
            return_exceptions=False,
        )

        # Worker scoring — sync, runs after LLM tasks complete so we can use
        # the Grok-suggested category as a fallback when none are selected.
        workers = []
        try:
            from app.ml.recommenders.feature_worker_scorer import FeatureWorkerScorer
            from app.ml.nlp.task_text import task_to_text
            from app.core.permission_service import get_permission_service
            from sqlalchemy import select as sa_select

            # Resolve explicit category IDs → names
            cat_names: list[str] = []
            if category_ids:
                cats = db.execute(
                    sa_select(Category).where(Category.id.in_(category_ids))
                ).scalars().all()
                id_to_name = {c.id: c.name for c in cats}
                cat_names = [id_to_name[cid] for cid in category_ids if cid in id_to_name]

            # Fall back to LLM-suggested category when nothing is selected yet
            if not cat_names and category is not None and category.match_name:
                cat_names = [category.match_name]

            eff_complexity = complexity if complexity is not None else (
                complexity_result.score if complexity_result else 3
            )
            category_hint = ", ".join(cat_names) if cat_names else None
            scored_text = task_to_text(title, description, category_hint=category_hint)

            scorer = FeatureWorkerScorer(get_permission_service())
            workers = scorer.score(
                text=scored_text,
                category_names=cat_names,
                complexity=eff_complexity,
                project_id=project_id,
                db=db,
            )
        except Exception:
            pass

        return TicketSuggestResult(
            complexity=complexity_result,
            category=category,
            tags=tags,
            workers=workers,
        )

    async def suggest_skills_from_bio(self, bio: str, db: Session) -> SkillSuggestResult:
        if not bio.strip():
            return SkillSuggestResult(skills=None)
        # Pass all DB category names so custom categories receive proficiency ratings
        all_cats = [
            c.name for c in db.execute(select(Category)).scalars().all()
        ]
        result = await extract_skills(bio, canonical_categories=all_cats)
        return SkillSuggestResult(skills=result)
