"""
Complexity suggestion from keyword heuristics and per-category priors.
No training data required — works on day one.
Confidence is intentionally modest to signal it is a suggestion, not a prediction.
"""
from __future__ import annotations

import re

from app.ml.base.recommender import BaseComplexityRecommender, ComplexityScore

_SIGNALS: list[tuple[list[str], int]] = [
    (
        ["refactor", "migrate", "redesign", "rewrite", "architect", "overhaul",
         "integrate", "replace", "rebuild"],
        +2,
    ),
    (
        ["implement", "build", "develop", "create feature", "add support",
         "optimise", "optimize", "performance", "security", "authentication"],
        +1,
    ),
    (
        ["fix", "patch", "adjust", "tweak", "change", "update text",
         "rename", "move", "copy", "minor"],
        -1,
    ),
    (
        ["typo", "label", "color", "colour", "icon", "tooltip",
         "placeholder", "copy change", "wording"],
        -2,
    ),
]

_CATEGORY_PRIORS: dict[str, float] = {
    "devops":    3.8,
    "security":  3.7,
    "data":      3.5,
    "backend":   3.2,
    "mobile":    3.0,
    "frontend":  2.8,
    "qa":        2.5,
    "design":    2.4,
}


class HeuristicComplexityRecommender(BaseComplexityRecommender):
    def recommend(
        self,
        text: str,
        category_names: list[str] | None = None,
    ) -> ComplexityScore:
        # Average priors across all selected categories; default to 3.0.
        if category_names:
            values = [_CATEGORY_PRIORS.get(n, 3.0) for n in category_names]
            prior = sum(values) / len(values)
        else:
            prior = 3.0
        if not text.strip():
            return ComplexityScore(value=round(prior), confidence=0.3, basis="heuristic")

        lower = text.lower()
        score: float = prior
        total_matches = 0

        for keywords, delta in _SIGNALS:
            for kw in keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", lower):
                    score += delta * 0.4
                    total_matches += 1
                    break

        word_count = len(lower.split())
        if word_count > 80:
            score += 0.5
        elif word_count > 40:
            score += 0.25

        clamped = max(1, min(5, round(score)))
        confidence = min(0.75, 0.35 + total_matches * 0.1)
        return ComplexityScore(value=clamped, confidence=round(confidence, 2), basis="heuristic")
