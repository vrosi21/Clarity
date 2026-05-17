"""Worker and task generators for the synthetic data simulator.

Each generator has a single responsibility (Single Responsibility Principle):
WorkerGenerator builds plausible team rosters; TaskGenerator builds plausible
sprint backlogs. Both accept either a seed or an explicit
`np.random.Generator` so the surrounding simulator can thread one rng through
the whole pipeline for reproducibility.

Both generators support two modes:
- Legacy (use_nlp=False, default): existing behaviour unchanged.
- NLP (use_nlp=True): tasks get real text + pre-computed embeddings sampled
  from the story-points dataset; workers get generated text + live embeddings.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

import numpy as np

from app.ml.simulation.task import SimTask
from app.ml.simulation.worker import (
    CANONICAL_CATEGORIES,
    SENIORITY_RANK,
    SimWorker,
    Seniority,
)

if TYPE_CHECKING:
    import pandas as pd


def _resolve_rng(
    seed: int | None,
    rng: np.random.Generator | None,
) -> np.random.Generator:
    """Return the rng to use, preferring an explicit one over the seed."""
    if rng is not None:
        return rng
    return np.random.default_rng(seed)


def _sp_to_complexity(sp: float) -> int:
    """Map story points to a 1–5 complexity bucket (same mapping as notebook 00)."""
    if sp <= 1:    return 1
    elif sp <= 3:  return 2
    elif sp <= 5:  return 3
    elif sp <= 13: return 4
    else:          return 5


# --- Worker generation -------------------------------------------------------

# Roster mix: roughly 40% junior, 35% mid, 20% senior, 5% lead.
_SENIORITY_LEVELS: tuple[Seniority, ...] = ("junior", "mid", "senior", "lead")
_SENIORITY_PROBS: tuple[float, ...] = (0.40, 0.35, 0.20, 0.05)

# Inclusive years-experience ranges per seniority level.
_YEARS_RANGE: dict[Seniority, tuple[int, int]] = {
    "junior": (0, 3),
    "mid": (2, 7),
    "senior": (5, 13),
    "lead": (10, 20),
}

# Burnout threshold (minutes of in-flight work) per seniority level.
_BURNOUT_RANGE: dict[Seniority, tuple[int, int]] = {
    "junior": (1800, 2050),
    "mid": (2000, 2300),
    "senior": (2300, 2600),
    "lead": (2500, 2800),
}


class WorkerGenerator:
    """Generates realistic SimWorker rosters."""

    def generate(
        self,
        n: int,
        seed: int | None = None,
        rng: np.random.Generator | None = None,
        use_nlp: bool = False,
        encoder=None,
    ) -> list[SimWorker]:
        if use_nlp and encoder is None:
            raise ValueError("encoder required when use_nlp=True")

        rng = _resolve_rng(seed, rng)
        workers: list[SimWorker] = []

        for i in range(n):
            seniority = cast(
                Seniority,
                _SENIORITY_LEVELS[
                    int(rng.choice(len(_SENIORITY_LEVELS), p=_SENIORITY_PROBS))
                ],
            )

            years_lo, years_hi = _YEARS_RANGE[seniority]
            years = int(rng.integers(years_lo, years_hi + 1))

            primary = str(rng.choice(CANONICAL_CATEGORIES))
            proficiency = self._build_proficiency(primary, rng)

            base_productivity = float(rng.lognormal(mean=0.0, sigma=0.15))

            burn_lo, burn_hi = _BURNOUT_RANGE[seniority]
            burnout_threshold = int(rng.integers(burn_lo, burn_hi + 1))

            worker = SimWorker(
                id=i,
                seniority=seniority,
                years_experience=years,
                primary_category=primary,
                category_proficiency=proficiency,
                base_productivity=base_productivity,
                burnout_threshold=burnout_threshold,
                current_load=0,
                is_available=True,
            )

            if use_nlp:
                # Lazy import — never loads sentence-transformers in legacy mode.
                from app.ml.nlp import sim_worker_to_text
                text = sim_worker_to_text(worker)
                worker.embedding = encoder.encode_one(text)

            workers.append(worker)

        return workers

    @staticmethod
    def _build_proficiency(
        primary: str,
        rng: np.random.Generator,
    ) -> dict[str, float]:
        """Primary 0.6–1.0; 1–3 secondaries 0.35–0.65; remainder 0.15–0.35.

        Floors raised from earlier (0.2 / 0.05) so that the eligibility filter
        and the softened skill multiplier stay in a realistic range — a real
        PM would not assign work to someone with effectively zero exposure.
        """
        others = [c for c in CANONICAL_CATEGORIES if c != primary]
        rng.shuffle(others)

        n_secondary = int(rng.integers(1, 4))  # 1, 2, or 3
        secondary = others[:n_secondary]
        tertiary = others[n_secondary:]

        prof: dict[str, float] = {primary: float(rng.uniform(0.6, 1.0))}
        for c in secondary:
            prof[c] = float(rng.uniform(0.35, 0.65))
        for c in tertiary:
            prof[c] = float(rng.uniform(0.15, 0.35))

        # Guarantee every canonical category has an entry (defensive).
        for c in CANONICAL_CATEGORIES:
            prof.setdefault(c, 0.15)
        return prof


# --- Task generation ---------------------------------------------------------

# Complexity distribution: right-skewed (more 2–3 than 4–5).
_COMPLEXITY_PROBS: tuple[float, ...] = (0.20, 0.30, 0.30, 0.15, 0.05)

# Priority distribution: P3 most common, P1/P5 rare.
_PRIORITY_PROBS: tuple[float, ...] = (0.05, 0.20, 0.50, 0.20, 0.05)

# Median estimated_minutes by complexity (lognormal mean = log of these).
_ESTIMATE_MEDIAN: dict[int, float] = {
    1: 30,
    2: 90,
    3: 180,
    4: 480,
    5: 1200,
}
_ESTIMATE_SIGMA: float = 0.30

# Probability table over requires_min_seniority for each complexity level.
# Rows: complexity 1..5, columns: requires_min_seniority 0..3.
_REQ_SENIORITY_PROBS: dict[int, tuple[float, float, float, float]] = {
    1: (0.95, 0.05, 0.00, 0.00),
    2: (0.85, 0.15, 0.00, 0.00),
    3: (0.50, 0.40, 0.10, 0.00),
    4: (0.10, 0.40, 0.40, 0.10),
    5: (0.00, 0.10, 0.50, 0.40),
}


class TaskGenerator:
    """Generates realistic SimTask backlogs.

    In NLP mode (use_nlp=True), tasks are populated with real titles,
    descriptions, and pre-computed embeddings sampled from the
    Choetkiertikul story-points dataset, grouped by complexity bucket.
    """

    # Paths resolved relative to this file's location inside
    # backend/app/ml/simulation/ — parents[1] = backend/app/ml/
    _STORY_POINTS_PATH: Path = (
        Path(__file__).resolve().parents[1]
        / "data" / "external" / "story_points.csv"
    )
    _EMBEDDINGS_CACHE_PATH: Path = (
        Path(__file__).resolve().parents[1]
        / "data" / "nlp" / "task_embeddings_cache.npy"
    )

    def __init__(self) -> None:
        # NLP data is loaded lazily on the first use_nlp=True call.
        self._nlp_df: pd.DataFrame | None = None
        self._nlp_embeddings: np.ndarray | None = None
        self._nlp_index_groups: dict[int, list[int]] | None = None

    def _load_nlp_data(self) -> None:
        """Load story-points CSV + embedding cache. Called once per instance."""
        import pandas as pd

        df = pd.read_csv(self._STORY_POINTS_PATH)

        # Normalise column names (handles summary/title, sp/story_points, etc.)
        col_map: dict[str, str] = {}
        for col in df.columns:
            lo = col.lower().strip().replace(" ", "_")
            if lo in ("title", "summary") and "title" not in col_map.values():
                col_map[col] = "title"
            elif lo in ("description", "body") and "description" not in col_map.values():
                col_map[col] = "description"
            elif lo in ("storypoint", "storypoints", "story_point", "story_points", "sp") \
                    and "story_points" not in col_map.values():
                col_map[col] = "story_points"
        df = df.rename(columns=col_map)

        # Apply same cleaning as notebook 00 so index aligns with the cache.
        df = df.dropna(subset=["title", "story_points"])
        df = df[df["story_points"].apply(lambda x: str(x).replace(".", "", 1).isdigit())]
        df["story_points"] = df["story_points"].astype(float)
        df = df[df["story_points"] > 0]
        df["description"] = df["description"].fillna("") if "description" in df.columns else ""
        df = df.reset_index(drop=True)

        embeddings = np.load(self._EMBEDDINGS_CACHE_PATH).astype(np.float32)

        if len(df) != len(embeddings):
            raise ValueError(
                f"Story-points CSV has {len(df)} rows after cleaning but "
                f"embedding cache has {len(embeddings)} rows. "
                "Re-run notebook 00 to rebuild the cache from the same CSV."
            )

        df["complexity"] = df["story_points"].apply(_sp_to_complexity)

        index_groups: dict[int, list[int]] = {c: [] for c in range(1, 6)}
        for idx, row in df.iterrows():
            index_groups[int(row["complexity"])].append(int(idx))

        self._nlp_df = df
        self._nlp_embeddings = embeddings
        self._nlp_index_groups = index_groups

    def generate(
        self,
        n: int,
        seed: int | None = None,
        rng: np.random.Generator | None = None,
        use_nlp: bool = False,
    ) -> list[SimTask]:
        rng = _resolve_rng(seed, rng)

        if use_nlp and self._nlp_index_groups is None:
            self._load_nlp_data()

        tasks: list[SimTask] = []

        for i in range(n):
            # Category stays as a soft label even in NLP mode.
            category = str(rng.choice(CANONICAL_CATEGORIES))

            complexity = int(rng.choice(np.arange(1, 6), p=_COMPLEXITY_PROBS))
            priority = int(rng.choice(np.arange(1, 6), p=_PRIORITY_PROBS))

            median = _ESTIMATE_MEDIAN[complexity]
            estimated_minutes = max(
                5,
                int(round(rng.lognormal(mean=np.log(median), sigma=_ESTIMATE_SIGMA))),
            )

            req_probs = _REQ_SENIORITY_PROBS[complexity]
            requires_min_seniority = int(rng.choice(np.arange(0, 4), p=req_probs))
            requires_min_seniority = min(requires_min_seniority, max(SENIORITY_RANK.values()))

            if use_nlp:
                assert self._nlp_df is not None
                assert self._nlp_embeddings is not None
                assert self._nlp_index_groups is not None

                bucket = self._nlp_index_groups[complexity]
                row_idx = int(rng.choice(bucket))
                row = self._nlp_df.iloc[row_idx]
                title = str(row["title"])
                description = str(row["description"]) if row.get("description", "") else ""
                embedding = self._nlp_embeddings[row_idx].copy()
            else:
                title = ""
                description = ""
                embedding = None

            tasks.append(
                SimTask(
                    id=i,
                    category=category,
                    complexity=complexity,
                    priority=priority,
                    estimated_minutes=estimated_minutes,
                    requires_min_seniority=requires_min_seniority,
                    title=title,
                    description=description,
                    embedding=embedding,
                )
            )

        return tasks
