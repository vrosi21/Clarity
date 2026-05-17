"""Synthetic data simulation package.

Exposes the simulation building blocks that notebooks 01 and 02 import:
worker/task dataclasses, generators, the LogNormal noise strategy, and the
core Simulator engine.
"""

from app.ml.simulation.generator import TaskGenerator, WorkerGenerator
from app.ml.simulation.noise import BaseNoiseStrategy, LogNormalNoise
from app.ml.simulation.simulator import Simulator
from app.ml.simulation.task import SimTask
from app.ml.simulation.worker import (
    CANONICAL_CATEGORIES,
    SimWorker,
)

__all__ = [
    "BaseNoiseStrategy",
    "CANONICAL_CATEGORIES",
    "LogNormalNoise",
    "SimTask",
    "SimWorker",
    "Simulator",
    "TaskGenerator",
    "WorkerGenerator",
]
