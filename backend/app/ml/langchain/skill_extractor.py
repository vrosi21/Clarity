"""Extract structured skills + seniority hint + per-category proficiency from a free-text bio."""
from __future__ import annotations

from app.ml.langchain.llm import get_llm
from app.ml.langchain.output_schemas import SkillOutput

_TEMPLATE = """
You are a technical recruiter parsing a developer's bio or skills description.
Extract:
  - Individual skills and technologies mentioned (Python, FastAPI, React, Kubernetes, etc.)
  - The most fitting primary category from the available categories list
  - Seniority level if mentioned or clearly implied (junior/mid/senior/lead)
  - A proficiency estimate (0.0-1.0) for each category from the list that has
    clear evidence in the bio. Use this scale:
      0.9+ = expert, deep specialisation clearly stated
      0.7-0.9 = strong working knowledge, multiple years or explicit claim
      0.4-0.7 = solid but not specialised
      0.2-0.4 = some exposure, mentioned but not a focus
    Only include categories with real evidence. Do not guess or pad the list.

Available categories: {categories}

Bio text: {text}

Respond with JSON matching: {format_instructions}
""".strip()


async def extract_skills(
    text: str,
    canonical_categories: list[str],
) -> SkillOutput | None:
    try:
        from langchain_core.output_parsers import PydanticOutputParser
        from langchain_core.prompts import ChatPromptTemplate

        parser = PydanticOutputParser(pydantic_object=SkillOutput)
        prompt = ChatPromptTemplate.from_template(_TEMPLATE)
        chain = prompt | get_llm() | parser
        return await chain.ainvoke(
            {
                "text": text,
                "categories": ", ".join(canonical_categories),
                "format_instructions": parser.get_format_instructions(),
            }
        )
    except Exception:
        return None
