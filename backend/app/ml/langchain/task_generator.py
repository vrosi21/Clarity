"""LLM-driven task generation for new projects.

Two phases:
  1. `generate_category_diffusion` — given project metadata and a generation
     config, propose a weighted distribution across technical categories.
  2. `generate_tasks` — given the diffusion plan, propose concrete tickets
     in batches.

Both phases use Groq via the shared get_llm() singleton and structured output
via LangChain PydanticOutputParser. Both return (output, error) tuples so the
caller can surface the real failure cause to the user instead of silent None.
"""
from __future__ import annotations

import logging
import sys
import traceback

from app.ml.langchain.llm import get_llm
from app.ml.langchain.output_schemas import (
    CategoryDiffusionOutput,
    GeneratedTasksOutput,
)

_log = logging.getLogger(__name__)


def _format_error(exc: BaseException) -> str:
    msg = f"{type(exc).__name__}: {exc}"
    # Also print full traceback to stderr regardless of logging config.
    print(f"\n[task_generator] {msg}", file=sys.stderr, flush=True)
    traceback.print_exc(file=sys.stderr)
    sys.stderr.flush()
    return msg


_DIFFUSION_TEMPLATE = """
You are a software project planner. Given a new project, propose a weighted
diffusion across technical categories that best describes the work needed.

Project name: {project_name}
Project description: {project_description}

Generation config:
- complexity_profile: {complexity_profile}  (simple|medium|complex)
- total_hours_min: {total_hours_min}
- total_hours_max: {total_hours_max}
- task_count: {task_count}

Existing categories (prefer these when applicable, but propose new ones if the
project clearly needs a domain not covered):
{categories}

Rules:
- You MUST return AT LEAST 2 and AT MOST 6 categories. NEVER return an empty list.
- Use lowercase, hyphenated, slug-style names (e.g. "ml-ops", "data-pipeline").
- weights are relative (0.0-1.0); they do NOT need to sum to 1.
- For complex projects favour 4-6 categories; for simple, 2-3.
- description should be ONE sentence explaining why this category matters here.
- If you are unsure, fall back to "backend", "frontend", and "qa" — but never return zero items.

Respond with JSON matching: {format_instructions}
""".strip()


_TASKS_TEMPLATE = """
You are generating concrete engineering tickets for a Kanban board.

Project name: {project_name}
Project description: {project_description}

Category diffusion plan (weights guide how many tickets each category gets):
{diffusion}

Existing tag vocabulary (use these names exactly when applicable):
{tags}

Generation config:
- complexity_profile: {complexity_profile}
- total_hours_min: {total_hours_min}
- total_hours_max: {total_hours_max}
- target total tickets in project: {task_count}
- this batch: index {batch_index} of {batch_total}, size {batch_size}

Already-generated titles to avoid duplicating:
{prior_titles}

Rules:
- You MUST return EXACTLY {batch_size} tickets — never return an empty list.
- Each ticket MUST have a clear, action-oriented title (e.g. "Build login form").
- description should be 1-3 sentences of practical detail.
- category_name must come from the diffusion plan above (use the exact slug).
- complexity is 1-5 matching the profile:
    simple   -> mostly 1-2, occasional 3
    medium   -> mostly 2-3, occasional 4
    complex  -> mostly 3-4, some 5
- estimated_minutes should reflect the complexity (60-2400 typical range).
- priority is one of p1, p2, p3, p4, p5 (default p3, p1 only for true blockers).
- tag_names is a list of UX tags (e.g. "feature", "bug"); prefer from existing.
- If you are uncertain, output reasonable engineering tickets like "Set up CI",
  "Write unit tests", "Implement login flow" — but NEVER return an empty list.

Respond with JSON matching: {format_instructions}
""".strip()


async def generate_category_diffusion(
    project_name: str,
    project_description: str,
    config: dict,
    existing_categories: list[dict],
) -> tuple[CategoryDiffusionOutput | None, str | None]:
    """Phase 1: propose a weighted category distribution.

    Returns (output, error_message). On success error is None; on failure
    output is None and error is a concise string describing the cause.
    """
    try:
        from langchain_core.output_parsers import PydanticOutputParser
        from langchain_core.prompts import ChatPromptTemplate

        parser = PydanticOutputParser(pydantic_object=CategoryDiffusionOutput)
        prompt = ChatPromptTemplate.from_template(_DIFFUSION_TEMPLATE)

        lines = []
        for c in existing_categories:
            desc = c.get("description") or ""
            lines.append(f"- {c['name']}: {desc}".strip())
        cat_list = "\n".join(lines) if lines else "(none yet)"

        chain = prompt | get_llm() | parser
        out = await chain.ainvoke(
            {
                "project_name": project_name,
                "project_description": project_description or "(none provided)",
                "complexity_profile": config.get("complexity_profile", "medium"),
                "total_hours_min": config.get("total_hours_min", 40),
                "total_hours_max": config.get("total_hours_max", 200),
                "task_count": config.get("task_count", 15),
                "categories": cat_list,
                "format_instructions": parser.get_format_instructions(),
            }
        )
        return out, None
    except Exception as exc:
        msg = _format_error(exc)
        _log.exception("generate_category_diffusion failed: %s", msg)
        return None, msg


async def generate_tasks(
    project_name: str,
    project_description: str,
    category_diffusion: list[dict],
    config: dict,
    existing_tags: list[str],
    batch_index: int,
    batch_total: int,
    batch_size: int,
    prior_titles: list[str],
) -> tuple[GeneratedTasksOutput | None, str | None]:
    """Phase 2: generate `batch_size` concrete tickets for one batch.

    Returns (output, error_message). On success error is None.
    """
    try:
        from langchain_core.output_parsers import PydanticOutputParser
        from langchain_core.prompts import ChatPromptTemplate

        parser = PydanticOutputParser(pydantic_object=GeneratedTasksOutput)
        prompt = ChatPromptTemplate.from_template(_TASKS_TEMPLATE)

        diffusion_str = "\n".join(
            f"- {d['category_name']} (weight={d['weight']:.2f}): {d.get('description','')}"
            for d in category_diffusion
        )
        tags_str = ", ".join(existing_tags) if existing_tags else "(none)"
        prior_str = (
            "\n".join(f"- {t}" for t in prior_titles[-30:])
            if prior_titles
            else "(none)"
        )

        chain = prompt | get_llm() | parser
        out = await chain.ainvoke(
            {
                "project_name": project_name,
                "project_description": project_description or "(none provided)",
                "diffusion": diffusion_str,
                "tags": tags_str,
                "complexity_profile": config.get("complexity_profile", "medium"),
                "total_hours_min": config.get("total_hours_min", 40),
                "total_hours_max": config.get("total_hours_max", 200),
                "task_count": config.get("task_count", 15),
                "batch_index": batch_index,
                "batch_total": batch_total,
                "batch_size": batch_size,
                "prior_titles": prior_str,
                "format_instructions": parser.get_format_instructions(),
            }
        )
        return out, None
    except Exception as exc:
        msg = _format_error(exc)
        _log.exception("generate_tasks batch %s failed: %s", batch_index, msg)
        return None, msg
