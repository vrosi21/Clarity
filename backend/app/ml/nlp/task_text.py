"""Convert structured task metadata into natural-language text for embedding.

Single Responsibility: task → text string. Does not encode, does not score.

The text is designed to be rich enough for the encoder to extract semantic
meaning from the title and description while optional fields add context.
Category hint is intentionally optional — the NLP layer should work without
hardcoded taxonomy labels so it can generalise to novel task types.
"""
from __future__ import annotations


def task_to_text(
    title: str,
    description: str | None = None,
    category_hint: str | None = None,
    complexity: int | None = None,
    priority: int | None = None,
) -> str:
    """Produce a text representation of a task suitable for embedding.

    Args:
        title:          Short task title / summary.
        description:    Optional longer description (truncated to 500 chars).
        category_hint:  Optional soft label (e.g. "backend"). Enriches the
                        embedding but is NOT required — the goal is to
                        eventually drop the fixed taxonomy.
        complexity:     1–5 numeric complexity, if known.
        priority:       1–5 numeric priority (1 = highest), if known.
    """
    parts = [f"Task: {title.strip()}"]
    if description:
        parts.append(f"Description: {description.strip()[:500]}")
    if category_hint:
        parts.append(f"Area: {category_hint}")
    if complexity is not None:
        parts.append(f"Complexity: {complexity} out of 5")
    if priority is not None:
        parts.append(f"Priority: P{priority}")
    return " | ".join(parts)
