"""Convert worker attributes into natural-language text for embedding.

Single Responsibility: worker data → text string.

Two public functions:
- worker_to_text: generic, works with real WorkerProfile fields or any dict.
- sim_worker_to_text: bridge from SimWorker (reads category_proficiency dict
  to produce a skill-description list, then delegates to worker_to_text).

This bridge is the only place that touches category_proficiency in this module.
Once the simulation is updated (notebook 01), sim_worker_to_text is either
retired or replaced — the rest of the NLP layer is unaffected.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ml.simulation.worker import SimWorker


def worker_to_text(
    seniority: str,
    years_experience: int,
    primary_skill: str | None = None,
    skill_descriptions: list[str] | None = None,
    role_title: str | None = None,
) -> str:
    """Produce a text representation of a worker's skill profile for embedding.

    Args:
        seniority:          "junior" | "mid" | "senior" | "lead"
        years_experience:   0–20
        primary_skill:      Main area of expertise (e.g. "backend").
        skill_descriptions: Free-form skill phrases, e.g.
                            ["strong in backend", "some frontend"].
        role_title:         Optional explicit job title.
    """
    parts: list[str] = []
    if role_title:
        parts.append(f"Role: {role_title}.")
    parts.append(
        f"{seniority.capitalize()} level developer "
        f"with {years_experience} years of experience."
    )
    if primary_skill:
        parts.append(f"Primary specialisation: {primary_skill}.")
    if skill_descriptions:
        parts.append("Skills: " + "; ".join(skill_descriptions) + ".")
    return " ".join(parts)


def sim_worker_to_text(worker: "SimWorker") -> str:
    """Convert a SimWorker to embeddable text.

    Reads category_proficiency to produce a human-readable skill description.
    This is the bridge between the legacy category-lookup simulation and the
    NLP embedding layer. The simulation itself is NOT modified.

    Proficiency thresholds (tuned to match the simulation's generator range):
        >= 0.7 → "strong in X"
        >= 0.4 → "proficient in X"
        >= 0.2 → "some experience with X"
        <  0.2 → omitted (below meaningful signal threshold)
    """
    skill_descriptions: list[str] = []
    for cat, prof in sorted(
        worker.category_proficiency.items(), key=lambda x: x[1], reverse=True
    ):
        if prof >= 0.7:
            skill_descriptions.append(f"strong in {cat}")
        elif prof >= 0.4:
            skill_descriptions.append(f"proficient in {cat}")
        elif prof >= 0.2:
            skill_descriptions.append(f"some experience with {cat}")

    return worker_to_text(
        seniority=worker.seniority,
        years_experience=worker.years_experience,
        primary_skill=worker.primary_category,
        skill_descriptions=skill_descriptions,
    )
