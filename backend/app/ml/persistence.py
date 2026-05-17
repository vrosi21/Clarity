"""Save/load helpers for trained ML artefacts.

Both LinearQNetwork and MLPQNetwork are handled. The saved .npz file includes
a `network_type` field so load_q_network can reconstruct the correct class
without the caller needing to know which was used.

Drop trained files into `app/ml/data/models/`:
  - regressor.joblib
  - q_network.npz

Checkpoints are written to `app/ml/data/checkpoints/` during training so that
a run interrupted by a crash or shutdown can be resumed from the last saved
episode rather than restarting from scratch.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import joblib
import numpy as np

from app.ml.agent.q_network import LinearQNetwork, MLPQNetwork
from app.ml.base.predictor import BaseEfficiencyPredictor

if TYPE_CHECKING:
    from app.ml.agent.replay_buffer import ReplayBuffer

QNetwork = LinearQNetwork | MLPQNetwork


def save_regressor(predictor: BaseEfficiencyPredictor, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(predictor, path)


def load_regressor(path: str | Path) -> BaseEfficiencyPredictor:
    return joblib.load(Path(path))


def save_q_network(network: QNetwork, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    weights = network.get_weights()
    if "network_type" not in weights:
        # LinearQNetwork doesn't tag itself — add the tag.
        weights["network_type"] = np.array(["linear"])
    np.savez(path, **weights)


def save_checkpoint(
    checkpoint_dir: str | Path,
    q_network: QNetwork,
    replay_buffer: "ReplayBuffer",
    episode: int,
    trainer_steps: int,
    train_losses: list[float],
    train_eff: list[float],
) -> None:
    """Persist training state so a run can be resumed after interruption.

    Writes two files to `checkpoint_dir`:
      checkpoint.npz  — Q-network weights + training metadata
      buffer.joblib   — full replay buffer (experiences)
    """
    ckpt_dir = Path(checkpoint_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    weights = q_network.get_weights()
    np.savez(
        ckpt_dir / "checkpoint.npz",
        **weights,
        ckpt_episode=np.array([episode]),
        ckpt_steps=np.array([trainer_steps]),
        ckpt_losses=np.array(train_losses, dtype=float) if train_losses else np.array([], dtype=float),
        ckpt_eff=np.array(train_eff, dtype=float) if train_eff else np.array([], dtype=float),
    )
    joblib.dump(replay_buffer, ckpt_dir / "buffer.joblib", compress=3)


def load_checkpoint(checkpoint_dir: str | Path) -> dict[str, Any] | None:
    """Load a training checkpoint.

    Returns None if no checkpoint exists, otherwise returns a dict with keys:
      q_network, replay_buffer, episode, trainer_steps, train_losses, train_eff
    """
    ckpt_dir = Path(checkpoint_dir)
    ckpt_file = ckpt_dir / "checkpoint.npz"
    buf_file = ckpt_dir / "buffer.joblib"

    if not ckpt_file.exists():
        return None

    data = np.load(ckpt_file, allow_pickle=False)
    ntype = str(data["network_type"].flat[0]) if "network_type" in data else "linear"

    if ntype == "mlp":
        state_dim = int(data["meta_state_dim"][0])
        hidden1 = int(data["meta_hidden1"][0])
        hidden2 = int(data["meta_hidden2"][0])
        net = MLPQNetwork(state_dim=state_dim, hidden1=hidden1, hidden2=hidden2)
        net.set_weights({
            k: data[k] for k in data.files
            if not k.startswith("meta_") and not k.startswith("ckpt_") and k != "network_type"
        })
    else:
        net = LinearQNetwork(state_dim=len(data["w"]))
        net.set_weights({"w": data["w"], "b": data["b"]})

    buf = joblib.load(buf_file) if buf_file.exists() else None

    return {
        "q_network": net,
        "replay_buffer": buf,
        "episode": int(data["ckpt_episode"][0]),
        "trainer_steps": int(data["ckpt_steps"][0]),
        "train_losses": data["ckpt_losses"].tolist(),
        "train_eff": data["ckpt_eff"].tolist(),
    }


def load_q_network(path: str | Path) -> QNetwork:
    data = np.load(Path(path), allow_pickle=False)
    ntype = str(data["network_type"].flat[0]) if "network_type" in data else "linear"

    if ntype == "mlp":
        state_dim = int(data["meta_state_dim"][0])
        hidden1 = int(data["meta_hidden1"][0])
        hidden2 = int(data["meta_hidden2"][0])
        net = MLPQNetwork(state_dim=state_dim, hidden1=hidden1, hidden2=hidden2)
        net.set_weights({k: data[k] for k in data.files if not k.startswith("meta_") and k != "network_type"})
        return net
    else:
        w = data["w"]
        state_dim = int(data.get("state_dim", [len(w)])[0]) if "state_dim" in data else len(w)
        net = LinearQNetwork(state_dim=state_dim)
        net.set_weights({"w": data["w"], "b": data["b"]})
        return net
