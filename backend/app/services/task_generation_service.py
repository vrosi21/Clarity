"""TaskGenerationService — orchestrates LLM-driven project task generation.

Two phases:
  1. Compute category diffusion (LLM phase 1)
  2. Stream batches of tickets (LLM phase 2 in a loop)

Persists real Ticket rows in the project's BACKLOG/start stage. Auto-creates
categories that don't exist yet.
"""
from __future__ import annotations

import math
import random
from typing import Any, AsyncIterator

from sqlalchemy.orm import Session

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

        diffusion = await generate_category_diffusion(
            project_name=project_name,
            project_description=project_description or "",
            config=config,
            existing_categories=existing_cats,
        )

        if diffusion is None or not diffusion.plan:
            yield {"type": "error", "data": {"message": "LLM failed to produce a category diffusion plan"}}
            return

        diffusion_entries = self._materialise_diffusion(diffusion.plan)
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

            batch = await generate_tasks(
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
                yield {
                    "type": "batch",
                    "data": {"batch_index": batch_index, "tickets": []},
                }
                remaining -= batch_size
                continue

            persisted: list[dict[str, Any]] = []
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

        yield {"type": "done", "data": {"total": len(prior_titles)}}

    # ──────────────────────────── helpers ─────────────────────────────────────

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
