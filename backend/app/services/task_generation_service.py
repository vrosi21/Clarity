"""TaskGenerationService — orchestrates LLM-driven project task generation.

Two phases:
  1. Compute category diffusion (LLM phase 1)
  2. Stream batches of tickets (LLM phase 2 in a loop)

Persists real Ticket rows in the project's BACKLOG/start stage. Auto-creates
categories that don't exist yet.
"""
from __future__ import annotations

import logging
import math
import random
from typing import Any, AsyncIterator

from sqlalchemy.orm import Session

_log = logging.getLogger(__name__)

from app.ml.langchain.task_generator import (
    generate_category_diffusion,
    generate_tasks,
)
from app.models.enums import StageType, TicketPriority
from app.models.stage import Stage
from app.repositories.category_repository import CategoryRepository
from app.repositories.stage_repository import StageRepository
from app.repositories.tag_repository import TagRepository
from app.repositories.ticket_repository import TicketRepository

_BATCH_SIZE = 8

# Fallback color palette for newly-invented categories.
_FALLBACK_COLORS = [
    "#3b82f6", "#a855f7", "#f59e0b", "#ec4899",
    "#10b981", "#06b6d4", "#eab308", "#ef4444",
    "#8b5cf6", "#14b8a6",
]


class TaskGenerationService:
    def __init__(
        self,
        category_repo: CategoryRepository,
        stage_repo: StageRepository,
        tag_repo: TagRepository,
        ticket_repo: TicketRepository,
    ) -> None:
        self.category_repo = category_repo
        self.stage_repo = stage_repo
        self.tag_repo = tag_repo
        self.ticket_repo = ticket_repo

    # ──────────────────────────────────── public API ───────────────────────────

    async def stream_generation(
        self,
        project_id: int,
        project_name: str,
        project_description: str | None,
        config: dict[str, Any],
        db: Session,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield event dicts: {type, data}. Caller serialises to SSE."""

        # Locate the BACKLOG/start stage.
        backlog = self._find_backlog_stage(project_id)
        if backlog is None:
            yield {"type": "error", "data": {"message": "Project has no start stage"}}
            return

        # Phase 1: diffusion plan.
        existing_cats = [
            {"id": c.id, "name": c.name, "description": c.description}
            for c in self.category_repo.list_all()
        ]

        diffusion, diffusion_err = await generate_category_diffusion(
            project_name=project_name,
            project_description=project_description or "",
            config=config,
            existing_categories=existing_cats,
        )

        # If the LLM call hard-failed (exception), surface the cause and stop.
        if diffusion is None:
            yield {
                "type": "error",
                "data": {"message": f"Diffusion plan failed: {diffusion_err or 'unknown error'}"},
            }
            return

        # If the LLM returned a valid response but with an empty plan, fall back
        # to a deterministic 3-category default so the run can still proceed.
        plan_items = list(diffusion.plan)
        if not plan_items:
            _log.warning("LLM returned empty diffusion plan; using fallback")
            plan_items = self._build_fallback_plan(existing_cats)

        diffusion_entries = self._materialise_diffusion(plan_items)
        db.commit()  # persist any newly-created categories

        yield {
            "type": "diffusion",
            "data": {"plan": diffusion_entries},
        }

        # Phase 2: tickets in batches.
        task_count = int(config.get("task_count", 15))
        batch_total = math.ceil(task_count / _BATCH_SIZE)
        existing_tags = [t.name for t in self.tag_repo.list_all()]

        prior_titles: list[str] = []
        diffusion_dicts = [
            {"category_name": e["category_name"], "weight": e["weight"], "description": e["description"]}
            for e in diffusion_entries
        ]
        cat_by_name = {e["category_name"]: e for e in diffusion_entries}

        remaining = task_count
        for batch_index in range(batch_total):
            batch_size = min(_BATCH_SIZE, remaining)
            if batch_size <= 0:
                break

            batch, batch_err = await generate_tasks(
                project_name=project_name,
                project_description=project_description or "",
                category_diffusion=diffusion_dicts,
                config=config,
                existing_tags=existing_tags,
                batch_index=batch_index,
                batch_total=batch_total,
                batch_size=batch_size,
                prior_titles=prior_titles,
            )

            if batch is None or not batch.tasks:
                _log.warning(
                    "Task generation batch %s/%s returned no tasks: %s — using fallback",
                    batch_index, batch_total, batch_err or "empty output",
                )
                fallback_tasks = self._build_fallback_tasks(
                    diffusion_entries, batch_size, batch_index, config
                )
                persisted: list[dict[str, Any]] = []
                for task in fallback_tasks:
                    ticket_dict = self._persist_ticket(
                        project_id=project_id,
                        stage_id=backlog.id,
                        task=task,
                        cat_by_name=cat_by_name,
                    )
                    if ticket_dict is not None:
                        persisted.append(ticket_dict)
                        prior_titles.append(task.title)
                db.commit()
                yield {
                    "type": "batch",
                    "data": {"batch_index": batch_index, "tickets": persisted},
                }
                remaining -= batch_size
                continue

            persisted = []
            for task in batch.tasks[:batch_size]:
                ticket_dict = self._persist_ticket(
                    project_id=project_id,
                    stage_id=backlog.id,
                    task=task,
                    cat_by_name=cat_by_name,
                )
                if ticket_dict is not None:
                    persisted.append(ticket_dict)
                    prior_titles.append(task.title)
            db.commit()

            yield {
                "type": "batch",
                "data": {"batch_index": batch_index, "tickets": persisted},
            }
            remaining -= batch_size

        total_persisted = len(prior_titles)
        if total_persisted == 0:
            yield {
                "type": "error",
                "data": {
                    "message": (
                        "LLM returned no usable tickets. Check backend logs for the "
                        "underlying parser/API error (often a malformed JSON response "
                        "from the model — try a stronger GROQ_MODEL)."
                    )
                },
            }
            return
        yield {"type": "done", "data": {"total": total_persisted}}

    # ──────────────────────────── helpers ─────────────────────────────────────

    @staticmethod
    def _build_fallback_tasks(
        diffusion_entries: list[dict[str, Any]],
        batch_size: int,
        batch_index: int,
        config: dict[str, Any],
    ):
        """Deterministic ticket stubs when the LLM bails on a batch.

        Generates generic-but-sensible tickets weighted by the diffusion plan
        so the user at least gets a usable backlog rather than a half-empty one.
        """
        from app.ml.langchain.output_schemas import GeneratedTaskItem

        profile = str(config.get("complexity_profile", "medium"))
        base_complexity = {"simple": 2, "medium": 3, "complex": 4}.get(profile, 3)
        hours_avg = (
            (int(config.get("total_hours_min", 80)) + int(config.get("total_hours_max", 200))) / 2
        )
        task_count = max(int(config.get("task_count", 15)), 1)
        avg_minutes = max(int(hours_avg * 60 / task_count), 30)

        # Round-robin tickets across categories proportional to weight.
        if not diffusion_entries:
            cats = ["backend"]
            weights = [1.0]
        else:
            cats = [c["category_name"] for c in diffusion_entries]
            weights = [max(float(c.get("weight", 1.0)), 0.01) for c in diffusion_entries]
        weight_sum = sum(weights)
        per_cat = [max(1, round(batch_size * w / weight_sum)) for w in weights]

        # Generic action verbs per category — readable placeholder titles.
        verbs = ["Implement", "Refactor", "Add tests for", "Document", "Investigate", "Polish", "Optimise", "Wire up"]
        nouns_by_cat = {
            "backend": ["API endpoint", "service layer", "background job", "data migration", "auth check"],
            "frontend": ["UI component", "page layout", "form validation", "error state", "loading state"],
            "devops": ["CI pipeline", "deployment config", "monitoring alert", "container image", "secret rotation"],
            "design": ["wireframe", "icon set", "colour token", "type scale", "user flow"],
            "mobile": ["screen", "navigation flow", "push notification", "offline cache", "permission prompt"],
            "data": ["ETL job", "dashboard", "schema change", "query optimisation", "data export"],
            "qa": ["test plan", "regression suite", "smoke test", "edge case", "test harness"],
            "security": ["auth flow", "input validation", "audit log", "dependency scan", "key rotation"],
        }
        default_nouns = ["task", "feature", "fix", "improvement", "follow-up"]

        out: list[GeneratedTaskItem] = []
        idx = 0
        for cat, count in zip(cats, per_cat):
            nouns = nouns_by_cat.get(cat, default_nouns)
            for _ in range(count):
                if len(out) >= batch_size:
                    break
                verb = verbs[(idx + batch_index) % len(verbs)]
                noun = nouns[idx % len(nouns)]
                idx += 1
                out.append(GeneratedTaskItem(
                    title=f"{verb} {noun}",
                    description=f"{verb} a {cat} {noun} for the project. Auto-generated placeholder ticket.",
                    category_name=cat,
                    complexity=base_complexity,
                    estimated_minutes=avg_minutes,
                    priority="p3",
                    tag_names=[],
                ))
            if len(out) >= batch_size:
                break
        # Top up if rounding came up short.
        while len(out) < batch_size:
            out.append(GeneratedTaskItem(
                title=f"Follow-up task {len(out) + 1}",
                description="Placeholder ticket. Edit or remove as needed.",
                category_name=cats[0],
                complexity=base_complexity,
                estimated_minutes=avg_minutes,
                priority="p3",
                tag_names=[],
            ))
        return out

    @staticmethod
    def _build_fallback_plan(existing_cats: list[dict[str, Any]]):
        """Build a 3-category fallback plan when the LLM emits an empty list.

        Prefers existing canonical names; otherwise invents safe defaults.
        Returns objects with the same shape as CategoryDiffusionItem so
        _materialise_diffusion can consume them without changes.
        """
        from app.ml.langchain.output_schemas import CategoryDiffusionItem

        preferred = ["backend", "frontend", "qa"]
        existing_names = {c["name"] for c in existing_cats}
        picks: list[str] = [n for n in preferred if n in existing_names]
        # Top up to 3 from any other existing categories.
        for c in existing_cats:
            if len(picks) >= 3:
                break
            if c["name"] not in picks:
                picks.append(c["name"])
        # If we still don't have 3, invent the missing preferred ones.
        for n in preferred:
            if len(picks) >= 3:
                break
            if n not in picks:
                picks.append(n)

        weights = [0.5, 0.3, 0.2][: len(picks)]
        return [
            CategoryDiffusionItem(
                category_name=name,
                weight=w,
                description=f"Fallback diffusion — {name} included as default.",
            )
            for name, w in zip(picks, weights)
        ]

    def _find_backlog_stage(self, project_id: int) -> Stage | None:
        stages = self.stage_repo.list_for_project(project_id)
        for s in stages:
            if s.type == StageType.START:
                return s
        return stages[0] if stages else None

    def _materialise_diffusion(self, items: list) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for idx, item in enumerate(items):
            slug = item.category_name.lower().strip().replace(" ", "-")
            cat = self.category_repo.get_by_name(slug)
            is_new = False
            if cat is None:
                color = _FALLBACK_COLORS[idx % len(_FALLBACK_COLORS)]
                cat = self.category_repo.create(
                    name=slug, description=item.description, color=color
                )
                is_new = True
            out.append({
                "category_id": cat.id,
                "category_name": cat.name,
                "weight": float(item.weight),
                "description": item.description,
                "is_new": is_new,
                "color": cat.color,
            })
        return out

    def _persist_ticket(
        self,
        project_id: int,
        stage_id: int,
        task,
        cat_by_name: dict[str, dict[str, Any]],
    ) -> dict[str, Any] | None:
        cat_entry = cat_by_name.get(task.category_name.lower().strip())
        if cat_entry is None:
            # Pick the highest-weight category as fallback.
            cat_entry = max(cat_by_name.values(), key=lambda e: e["weight"])

        priority_value = task.priority.lower().strip()
        try:
            priority = TicketPriority(priority_value)
        except ValueError:
            priority = TicketPriority.P3

        ticket = self.ticket_repo.create(
            project_id=project_id,
            stage_id=stage_id,
            title=task.title[:255],
            description=task.description,
            priority=priority,
            complexity=max(1, min(5, int(task.complexity))),
            estimated_minutes=int(task.estimated_minutes),
            category_id=cat_entry["category_id"],
        )

        # Attach tags (best-effort, create if missing).
        for tag_name in task.tag_names or []:
            slug = tag_name.strip().lower()
            if not slug:
                continue
            tag = self.tag_repo.get_by_name(slug)
            if tag is None:
                try:
                    tag = self.tag_repo.create(slug)
                except Exception:
                    continue
            from app.models.ticket_tag import TicketTag
            self.ticket_repo.db.add(TicketTag(ticket_id=ticket.id, tag_id=tag.id))

        self.ticket_repo.db.flush()

        return {
            "id": ticket.id,
            "project_id": ticket.project_id,
            "stage_id": ticket.stage_id,
            "title": ticket.title,
            "description": ticket.description,
            "priority": ticket.priority.value if hasattr(ticket.priority, "value") else str(ticket.priority),
            "complexity": ticket.complexity,
            "category_id": ticket.category_id,
            "category_name": cat_entry["category_name"],
            "category_color": cat_entry["color"],
            "estimated_minutes": ticket.estimated_minutes,
        }
