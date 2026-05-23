"""LLM-driven category match. Picks an existing category or proposes a new name."""
from __future__ import annotations

from app.ml.langchain.llm import get_llm
from app.ml.langchain.output_schemas import CategoryOutput

_TEMPLATE = """
You are a software project categorisation assistant for a Kanban task tracker.
Categories represent technical domains of software work.

Given the existing categories below, select the SINGLE best match for this ticket.
Choose based on the primary technical domain of the work described — not just keywords.

Guidelines:
- "frontend" = UI components, styling, forms, pages, user interactions
- "backend" = APIs, business logic, database queries, server-side processing
- "devops" = deployment, CI/CD, Docker, infrastructure, monitoring
- "data" = data pipelines, analytics, reporting, migrations
- "mobile" = iOS/Android/React Native/Flutter apps
- "qa" = testing, test automation, quality assurance
- "security" = authentication, authorisation, encryption, vulnerability fixes
- "design" = UX/UI design, wireframes, design systems

If none of the existing categories fit well (confidence < 0.5), propose a concise
new category name in slug format (lowercase, hyphenated, max 2 words,
e.g. "ml-ops", "data-pipeline", "notifications"). Do NOT propose sentence fragments.

Existing categories:
{categories}

Ticket title and description:
{text}

Respond with JSON matching: {format_instructions}
""".strip()


async def suggest_category(
    text: str,
    existing: list[dict],
) -> CategoryOutput | None:
    """existing: list of {id, name, description?}. Returns None on failure."""
    try:
        from langchain_core.output_parsers import PydanticOutputParser
        from langchain_core.prompts import ChatPromptTemplate

        parser = PydanticOutputParser(pydantic_object=CategoryOutput)
        prompt = ChatPromptTemplate.from_template(_TEMPLATE)
        lines = []
        for c in existing:
            desc = c.get("description")
            if desc:
                lines.append(f"- id={c['id']} name={c['name']} ({desc})")
            else:
                lines.append(f"- id={c['id']} name={c['name']}")
        category_list = "\n".join(lines) if lines else "(none yet)"
        chain = prompt | get_llm() | parser
        return await chain.ainvoke(
            {
                "text": text,
                "categories": category_list,
                "format_instructions": parser.get_format_instructions(),
            }
        )
    except Exception:
        return None
