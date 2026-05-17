"""Semantic text encoder wrapping sentence-transformers.

Single Responsibility: text → embedding vector. Nothing else.
"""
from __future__ import annotations

import numpy as np


class SemanticEncoder:
    """Encodes text strings into fixed-dimension float32 embeddings.

    Uses all-MiniLM-L6-v2 (384-dim, MIT licence, ~80 MB).
    Weights are loaded from HuggingFace at runtime — never committed to the repo.

    sentence-transformers is imported lazily inside __init__ so that the rest of
    the NLP package (skill_match, task_to_text, etc.) can be imported in
    environments where the library is not yet installed.
    """

    MODEL_NAME = "all-MiniLM-L6-v2"

    def __init__(self, model_name: str = MODEL_NAME) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required to use SemanticEncoder. "
                "Install it with: pip install sentence-transformers>=2.2.0"
            ) from exc
        self._model = SentenceTransformer(model_name)
        # get_embedding_dimension() is the current name; fall back for older versions.
        _dim_fn = getattr(self._model, "get_embedding_dimension", None) or \
                  getattr(self._model, "get_sentence_embedding_dimension")
        self.dim: int = _dim_fn()

    def encode(self, texts: list[str], batch_size: int = 64) -> np.ndarray:
        """Return (N, dim) float32 array, one row per input string."""
        return self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
        ).astype(np.float32)

    def encode_one(self, text: str) -> np.ndarray:
        """Convenience wrapper for a single string."""
        return self.encode([text])[0]
