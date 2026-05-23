"""Lazy singleton ChatGroq factory.

Not instantiated at import time — only when a suggestion endpoint is first hit.
Raises if the API key is missing or invalid; callers must wrap in try/except.
"""
from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def get_llm():
    from langchain_groq import ChatGroq  # local import keeps app boot light

    from app.core.config import settings

    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.GROQ_MODEL,
        temperature=0,
    )
