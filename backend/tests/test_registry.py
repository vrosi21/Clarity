"""Model registry — fallback when files are missing + roundtrip when present."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from app.ml.agent.q_network import LinearQNetwork
from app.ml.persistence import (
    load_q_network,
    load_regressor,
    save_q_network,
    save_regressor,
)
from app.ml.registry import ModelRegistry
from app.ml.regressors.knn import KNNPredictor


def test_registry_returns_none_when_files_missing(tmp_path: Path):
    reg = ModelRegistry(model_dir=tmp_path)
    assert reg.regressor is None
    assert reg.q_network is None
    assert reg.has_regressor is False
    assert reg.has_q_network is False


def test_q_network_roundtrip(tmp_path: Path):
    net = LinearQNetwork(state_dim=17)
    # Mutate weights so we know we're not just re-creating defaults.
    net.w[:] = np.arange(17, dtype=float)
    net.b = 0.5
    save_q_network(net, tmp_path / "q_network.npz")

    loaded = load_q_network(tmp_path / "q_network.npz")
    assert loaded.state_dim == 17
    np.testing.assert_array_equal(loaded.w, net.w)
    assert loaded.b == 0.5


def test_regressor_roundtrip(tmp_path: Path):
    rng = np.random.default_rng(0)
    X = rng.normal(size=(50, 18))
    y = rng.normal(size=50)
    reg = KNNPredictor(n_neighbors=3)
    reg.fit(X, y)

    save_regressor(reg, tmp_path / "regressor.joblib")
    loaded = load_regressor(tmp_path / "regressor.joblib")

    pred_a = reg.predict(X[:5])
    pred_b = loaded.predict(X[:5])
    np.testing.assert_array_almost_equal(pred_a, pred_b)


def test_registry_picks_up_loaded_files(tmp_path: Path):
    net = LinearQNetwork(state_dim=17)
    save_q_network(net, tmp_path / "q_network.npz")
    rng = np.random.default_rng(0)
    reg = KNNPredictor(n_neighbors=3)
    reg.fit(rng.normal(size=(20, 18)), rng.normal(size=20))
    save_regressor(reg, tmp_path / "regressor.joblib")

    registry = ModelRegistry(model_dir=tmp_path)
    assert registry.has_regressor
    assert registry.has_q_network
