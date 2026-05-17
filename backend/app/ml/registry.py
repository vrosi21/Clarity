"""Lazy-loading registry for the trained ML artefacts.

Holds singleton instances of the regressor and Q-network. On first access,
attempts to load from disk; on failure (file missing / load error), returns
None for the missing piece so callers can fall back to a heuristic policy.

Thread-safety: not enforced; FastAPI's request handlers are async-safe via
the GIL for these read-mostly operations. If we move to multi-process
workers, joblib reads are independent per worker — no shared state issue.
"""
from __future__ import annotations

import logging
from pathlib import Path

from app.ml.agent.q_network import LinearQNetwork
from app.ml.base.predictor import BaseEfficiencyPredictor
from app.ml.persistence import load_q_network, load_regressor

log = logging.getLogger(__name__)


# Default location — notebook 03/04 should write here.
DEFAULT_MODEL_DIR: Path = Path(__file__).resolve().parent / "data" / "models"
REGRESSOR_FILENAME: str = "regressor.joblib"
Q_NETWORK_FILENAME: str = "q_network.npz"


class ModelRegistry:
    """Loads regressor + Q-network on demand from `model_dir`."""

    def __init__(self, model_dir: Path | str | None = None) -> None:
        self.model_dir = Path(model_dir) if model_dir else DEFAULT_MODEL_DIR
        self._regressor: BaseEfficiencyPredictor | None = None
        self._q_network: LinearQNetwork | None = None
        self._regressor_loaded: bool = False
        self._q_network_loaded: bool = False

    def reload(self) -> None:
        """Force the next access to re-read from disk."""
        self._regressor = None
        self._q_network = None
        self._regressor_loaded = False
        self._q_network_loaded = False

    @property
    def regressor(self) -> BaseEfficiencyPredictor | None:
        if not self._regressor_loaded:
            path = self.model_dir / REGRESSOR_FILENAME
            try:
                self._regressor = load_regressor(path) if path.exists() else None
            except Exception:  # noqa: BLE001 — we want a graceful degrade
                log.exception("Failed to load regressor from %s", path)
                self._regressor = None
            self._regressor_loaded = True
        return self._regressor

    @property
    def q_network(self) -> LinearQNetwork | None:
        if not self._q_network_loaded:
            path = self.model_dir / Q_NETWORK_FILENAME
            try:
                self._q_network = load_q_network(path) if path.exists() else None
            except Exception:  # noqa: BLE001
                log.exception("Failed to load q-network from %s", path)
                self._q_network = None
            self._q_network_loaded = True
        return self._q_network

    @property
    def has_regressor(self) -> bool:
        return self.regressor is not None

    @property
    def has_q_network(self) -> bool:
        return self.q_network is not None


# Process-wide registry. FastAPI dependency wraps this.
_registry = ModelRegistry()


def get_model_registry() -> ModelRegistry:
    return _registry
