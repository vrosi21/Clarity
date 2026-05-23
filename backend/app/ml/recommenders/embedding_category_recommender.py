"""
Finds nearest categories by cosine similarity + keyword matching.

Two scoring layers are combined:

  1. Embedding (canonical categories only) -- SemanticEncoder singleton,
     loaded once on first use.  Handles paraphrases and domain synonyms.

  2. Keyword (ALL categories, canonical + custom) -- if a category name
     (or its component words) appears in the ticket text it gets a boosted
     score regardless of whether it's in the embedding vocabulary.  This
     ensures user-created categories like "review dashboard" are surfaced
     when the title literally says "REVIEW DASHBOARD".

Per-request cat_id_map is always taken from the constructor argument so
newly created categories are immediately visible -- only the encoder and the
canonical embeddings are cached class-level.
"""
from __future__ import annotations

import numpy as np

from app.ml.base.recommender import BaseCategoryRecommender, CategoryScore

CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "backend": (
        "server-side API development, REST and GraphQL endpoints, business logic, "
        "database queries, ORM, PostgreSQL, Redis, microservices, background jobs, "
        "webhooks, data validation, server performance, caching, rate limiting"
    ),
    "frontend": (
        "user interface, web forms, form fields, form validation, page layout, "
        "UI components, React components, HTML, CSS, responsive design, "
        "browser rendering, client-side logic, accessibility, UX interactions, "
        "DOM manipulation, frontend routing, visual design, buttons, modals, "
        "tables, dashboards, data display, user-facing screens, typography, spacing"
    ),
    "devops": (
        "CI/CD pipelines, Docker, Kubernetes, deployment, infrastructure as code, "
        "cloud services, AWS, GCP, Azure, monitoring, logging, alerting, "
        "server provisioning, environment configuration, build automation, "
        "release management, uptime, SLAs, container orchestration"
    ),
    "design": (
        "UI/UX design, wireframes, mockups, Figma, visual identity, brand, "
        "user research, prototyping, design system, colour palette, icons, "
        "typography, information architecture, interaction design, style guide"
    ),
    "mobile": (
        "iOS, Android, React Native, Flutter, mobile app, phone, tablet, "
        "push notifications, offline support, app store, native performance, "
        "mobile UI, touch gestures, deep links, mobile-first"
    ),
    "data": (
        "data engineering, ETL pipelines, analytics, machine learning, SQL, "
        "data science, reporting, metrics, dashboards, charts, data models, "
        "data warehouse, data quality, aggregation, data export, CSV, "
        "business intelligence, data pipeline, batch processing"
    ),
    "qa": (
        "testing, quality assurance, bug hunting, test automation, unit tests, "
        "integration tests, end-to-end tests, selenium, pytest, flaky tests, "
        "regression testing, test coverage, manual testing, QA review, "
        "bug report, reproduce, test plan, acceptance criteria"
    ),
    "security": (
        "authentication, authorisation, permissions, role-based access, "
        "penetration testing, vulnerability, encryption, OAuth, JWT, "
        "CSRF, XSS, SQL injection, secrets management, audit log, "
        "compliance, data privacy, GDPR, 2FA, zero-trust"
    ),
}

NEW_CATEGORY_THRESHOLD = 0.30


class EmbeddingCategoryRecommender(BaseCategoryRecommender):
    # Class-level: encoder + canonical embeddings (loaded once, never change)
    _encoder = None
    _category_embeddings: np.ndarray | None = None
    _canonical_names: list[str] = []

    @classmethod
    def _load_encoder(cls) -> None:
        if cls._encoder is not None:
            return
        from app.ml.nlp.encoder import SemanticEncoder
        cls._encoder = SemanticEncoder()
        cls._canonical_names = list(CATEGORY_DESCRIPTIONS.keys())
        descriptions = [CATEGORY_DESCRIPTIONS[c] for c in cls._canonical_names]
        raw = cls._encoder.encode(descriptions)
        norms = np.linalg.norm(raw, axis=1, keepdims=True)
        cls._category_embeddings = raw / np.maximum(norms, 1e-8)

    def __init__(self, category_id_map: dict[str, int]) -> None:
        # Instance-level: always reflects the CURRENT state of the database
        # (including user-created categories).  Never cached class-level.
        self._cat_id_map: dict[str, int] = category_id_map
        self._load_encoder()

    # Public interface

    def recommend(self, text: str, top_k: int = 0) -> list[CategoryScore]:
        """Return all DB categories with confidence scores, sorted descending.

        top_k is retained for API compatibility but defaults to 0 (= no limit).
        Pass top_k > 0 to cap the result.
        """
        text_norm = text.strip()
        if not text_norm:
            return []

        scores: dict[str, float] = {}

        # 1. Embedding scores for canonical categories.
        if self._encoder is not None and self._category_embeddings is not None:
            raw = self._encoder.encode([text_norm])
            norm = np.linalg.norm(raw)
            text_emb = raw / max(norm, 1e-8)
            sims = (self._category_embeddings @ text_emb.T).flatten()
            exp_sims = np.exp(sims - sims.max())
            confs = (exp_sims / exp_sims.sum()).tolist()
            for name, conf in zip(self._canonical_names, confs):
                scores[name] = float(conf)

        # 2. Keyword scores for ALL categories (canonical + custom).
        text_lower = text_norm.lower()
        for name in self._cat_id_map:
            kw = _keyword_score(text_lower, name)
            if kw > 0:
                scores[name] = max(scores.get(name, 0.0), kw)

        # 3. Rank all DB categories (not capped by default).
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if top_k and top_k > 0:
            ranked = ranked[:top_k]

        return [
            CategoryScore(
                category_id=self._cat_id_map[name],
                category_name=name,
                confidence=round(conf, 3),
            )
            for name, conf in ranked
            if name in self._cat_id_map
        ]

    def suggest_new_name(self, text: str) -> str | None:
        """Candidate new-category name when no existing category fits well.

        Only fires when the top embedding confidence is below NEW_CATEGORY_THRESHOLD
        AND no keyword match found.  Returns None when a good match exists.
        """
        text_norm = text.strip()
        if not text_norm or self._encoder is None or self._category_embeddings is None:
            return None

        text_lower = text_norm.lower()

        # Don't suggest if any keyword match is strong enough.
        for name in self._cat_id_map:
            if _keyword_score(text_lower, name) >= 0.70:
                return None

        raw = self._encoder.encode([text_norm])
        norm = np.linalg.norm(raw)
        text_emb = raw / max(norm, 1e-8)
        sims = (self._category_embeddings @ text_emb.T).flatten()
        exp_sims = np.exp(sims - sims.max())
        top_conf = float((exp_sims / exp_sims.sum()).max())

        if top_conf >= NEW_CATEGORY_THRESHOLD:
            return None

        return _extract_candidate_name(text_norm)


# Keyword scoring

def _keyword_score(text_lower: str, category_name: str) -> float:
    """Score [0, 1] based on how well the category name appears in the ticket text.

    Tiers:
      0.95 - exact phrase present
      0.85 - all words present in any order
      0.60 - majority of words (>= 60%) present
      0.00 - no meaningful overlap
    """
    name_lower = category_name.lower()
    name_words = [w for w in name_lower.split() if len(w) > 1]
    if not name_words:
        return 0.0

    if name_lower in text_lower:
        return 0.95

    text_words = set(text_lower.split())
    matched = sum(1 for w in name_words if w in text_words)
    ratio = matched / len(name_words)

    if ratio == 1.0:
        return 0.85
    if ratio >= 0.6:
        return 0.60
    return 0.0


# Candidate name extractor (for new-category suggestion)

_STOPWORDS = frozenset({
    "fix", "add", "update", "create", "build", "implement", "make", "improve",
    "refactor", "migrate", "redesign", "change", "evaluate", "assess", "review",
    "check", "verify", "ensure", "test", "move", "rename", "remove", "delete",
    "convert", "replace", "integrate", "apply", "handle", "show", "hide",
    "allow", "enable", "disable", "support", "display", "render", "load",
    "the", "a", "an", "and", "or", "for", "in", "on", "at", "to", "with",
    "by", "from", "of", "is", "was", "be", "as", "that", "this", "it",
    "we", "our", "via", "into", "not", "no", "so", "up", "out",
    "please", "just", "simply", "also", "too", "now", "new", "old",
    "get", "set", "use", "page", "when", "how", "why",
})


def _extract_candidate_name(text: str) -> str | None:
    import re
    title = text.split("\n")[0].split(".")[0]
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_-]*\b", title.lower())
    meaningful = [w for w in words if len(w) > 2 and w not in _STOPWORDS]
    if not meaningful:
        return None
    if len(meaningful[0]) >= 6:
        return meaningful[0]
    candidate = " ".join(meaningful[:2])
    return candidate if len(candidate) > 2 else None
