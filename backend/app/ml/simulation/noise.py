"""Noise strategies for actual-time simulation.

The Open/Closed principle in action: the simulator depends on the
`BaseNoiseStrategy` interface, so swapping in a different noise model
(Weibull, mixture, heavy-tailed, etc.) is a one-line change in notebook
configuration — no edits to the simulator itself.

`sample` takes the deterministic per-run `np.random.Generator` so that the
whole simulation is reproducible from a single seed.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class BaseNoiseStrategy(ABC):
    """Maps a deterministic base time to a noisy actual time."""

    @abstractmethod
    def sample(
        self,
        base_time: float,
        complexity: int,
        rng: np.random.Generator,
    ) -> float:
        """Return a noisy actual time given the deterministic base time."""
        ...


class LogNormalNoise(BaseNoiseStrategy):
    """Right-skewed multiplicative noise — simple tasks predictable, complex tasks noisy.

    sigma = (0.08 + complexity * 0.04) * sigma_multiplier

    The skill and load multipliers in the simulator already produce most of
    the spread; the noise on top doesn't need to be wide. sigma now ranges
    from 0.12 (complexity 1) to 0.28 (complexity 5).

    `sigma_multiplier` is exposed for sensitivity analysis (notebook 02
    section C scans it across {0.5, 1.0, 2.0}).
    """

    def __init__(
        self,
        sigma_multiplier: float = 1.0,
        max_multiplier: float | None = None,
    ) -> None:
        self.sigma_multiplier = sigma_multiplier
        # Hard cap on the lognormal draw so a single task never blows up to
        # 10×–20× its estimate in a UI simulation. None = no cap (training mode).
        self.max_multiplier = max_multiplier

    def sample(
        self,
        base_time: float,
        complexity: int,
        rng: np.random.Generator,
    ) -> float:
        sigma = (0.08 + complexity * 0.04) * self.sigma_multiplier
        mult = float(rng.lognormal(mean=0.0, sigma=sigma))
        if self.max_multiplier is not None:
            mult = min(mult, self.max_multiplier)
        return float(base_time * mult)
