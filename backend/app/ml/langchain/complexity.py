"""Complexity classifier — full-sentence understanding incl. negation/qualifiers."""
from __future__ import annotations

from app.ml.langchain.llm import get_llm
from app.ml.langchain.output_schemas import ComplexityOutput

_TEMPLATE = """
You are a software complexity estimator for a Kanban task tracker used by software
development teams. Tickets represent engineering work: features, bug fixes, refactors,
integrations, documentation, DevOps tasks, etc.

Rate the complexity of the ticket on a scale of 1 to 5:
  1 = Trivial   — a few minutes, no thinking required (e.g. fix a typo, rename a field)
  2 = Simple    — under an hour, well-understood task (e.g. small UI tweak, config change)
  3 = Moderate  — a few hours, some investigation needed (e.g. new form, API endpoint)
  4 = Complex   — days of work, significant unknowns or coordination (e.g. new feature with DB changes)
  5 = Very complex — weeks, high uncertainty or architectural impact (e.g. system redesign, new service)

IMPORTANT rules:
- Read the FULL title and description, including qualifiers.
- Qualifiers like "minor", "just", "simple", "quick", "nothing special" LOWER the score.
- Qualifiers like "completely", "refactor", "redesign", "integrate", "migrate" RAISE the score.
- Negations ("not a big change", "should be straightforward") override base complexity.
- A long title alone does not mean high complexity — read the actual intent.
- "sync up", "make sure", "verify", "double-check" tasks are usually 1–2.
- Vague tickets with no description default to 2–3.

Ticket title and description:
{text}

Respond with JSON matching: {format_instructions}
""".strip()


async def classify_complexity(text: str) -> ComplexityOutput | None:
    """Return ComplexityOutput, or None if Ollama is unavailable."""
    try:
        from langchain_core.output_parsers import PydanticOutputParser
        from langchain_core.prompts import ChatPromptTemplate

        parser = PydanticOutputParser(pydantic_object=ComplexityOutput)
        prompt = ChatPromptTemplate.from_template(_TEMPLATE)
        chain = prompt | get_llm() | parser
        return await chain.ainvoke(
            {"text": text, "format_instructions": parser.get_format_instructions()}
        )
    except Exception:
        return None
