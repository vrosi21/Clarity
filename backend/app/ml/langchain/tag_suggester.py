"""LLM-driven UX-tag selector. Tags are NOT used by the RL model or state vector."""
from __future__ import annotations

from app.ml.langchain.llm import get_llm
from app.ml.langchain.output_schemas import TagOutput

# Fallback vocabulary used when the DB has no tags yet, so the LLM always has
# a meaningful set to pick from even before an admin seeds the tags table.
_DEFAULT_TAGS = [
    "bug", "feature", "enhancement", "clarification needed", "blocked",
    "urgent", "tech-debt", "refactor", "question", "duplicate",
    "wont-fix", "good first issue",
]

_TEMPLATE = """
You are a software project ticket tagger for a Kanban task tracker.
Your job is to apply short UX labels that help the team at a glance.

Select applicable labels from the existing tags list for this ticket.
You may also suggest NEW tags if clearly relevant and not already covered —
but only propose tag names that are concise (1–3 words) and human-readable.

Tag guidelines:
- "bug" = something is broken or incorrect
- "feature" = new functionality being added
- "enhancement" = improving existing functionality
- "clarification needed" = requirements are unclear
- "blocked" = waiting on something external
- "urgent" = needs to be done very soon
- "tech-debt" = addressing accumulated shortcuts
- "refactor" = restructuring code without changing behaviour
- "question" = needs discussion or a decision
- "duplicate" = same as another ticket
- "good first issue" = suitable for a new team member

Existing tags (use these names exactly if applicable):
{tags}

Ticket title and description:
{text}

Respond with JSON matching: {format_instructions}
""".strip()


async def suggest_tags(
    text: str,
    existing_tags: list[str],
) -> TagOutput | None:
    try:
        from langchain_core.output_parsers import PydanticOutputParser
        from langchain_core.prompts import ChatPromptTemplate

        parser = PydanticOutputParser(pydantic_object=TagOutput)
        prompt = ChatPromptTemplate.from_template(_TEMPLATE)
        # If DB has no tags yet, use the default vocabulary so the LLM still
        # has something to suggest from.
        vocab = existing_tags if existing_tags else _DEFAULT_TAGS
        chain = prompt | get_llm() | parser
        return await chain.ainvoke(
            {
                "text": text,
                "tags": ", ".join(vocab),
                "format_instructions": parser.get_format_instructions(),
            }
        )
    except Exception:
        return None
