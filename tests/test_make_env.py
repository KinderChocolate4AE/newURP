"""Composition-root pins + reserved-dim pads (2026-07-03 sweep; torch-free).

Guards the two traps this sweep closed:
  1) episode_len 70-vs-80: the demo root (rollout_gif.build_env) defaults 70;
     the env contract truncates at 80. make_train_env must take 80 from the
     config `train:` block and REFUSE to guess when pins are missing.
  2) reserved action dims: limiter pressure (idx 3) / finisher slew (idx 3)
     are accepted-but-ignored by the frozen env. Policies output LIVE dims
     only; pad_env_action re-inserts zeros at the reserved indices
     (finisher fire must land at env idx 4).
"""
import pathlib

import numpy as np
import pytest
import yaml

from shepherd.train.make_env import (LIVE_DIMS, live_action_dim, make_train_env,
                                     pad_env_action, pad_env_actions)

CFG_PATH = pathlib.Path(__file__).resolve().parents[1] / "configs" / "m2_l2_train.yaml"


def _cfg():
    with open(CFG_PATH) as f:
        return yaml.safe_load(f)


# --------------------------------------------------------------------- pins
def test_train_env_pins_contract_episode_len_and_cone():
    env, scn, lay = make_train_env(_cfg())
    assert lay.episode_len == 80                     # env-contract horizon (docs/09 SS2)
    assert env.cone_half_angle == pytest.approx(0.067)
    assert env.cone_range_min == pytest.approx(0.0)
    assert env.cone_range_max == pytest.approx(29.847)
    assert env.n_segments == 4                       # S14 conservative signal
    assert env.judge == "se3_cone"


def test_missing_train_block_raises():
    cfg = _cfg()
    cfg.pop("train")
    with pytest.raises(KeyError, match="train"):
        make_train_env(cfg)


def test_missing_episode_len_raises():
    cfg = _cfg()
    cfg["train"].pop("episode_len")
    with pytest.raises(KeyError, match="episode_len"):
        make_train_env(cfg)


def test_missing_cone_raises():
    cfg = _cfg()
    cfg["viability"].pop("cone")
    with pytest.raises(KeyError, match="cone"):
        make_train_env(cfg)


# ----------------------------------------------------------- reserved dims
def test_pad_limiter_pressure_reserved():
    a = pad_env_action("limiter_0", [1.0, 2.0, 3.0])
    assert a.shape == (4,)
    assert a[3] == 0.0                               # pressure RESERVED -> 0
    assert np.allclose(a[:3], [1.0, 2.0, 3.0])


def test_pad_finisher_fire_lands_at_idx4():
    f = pad_env_action("finisher_0", [0.1, 0.2, 0.3, 1.0])
    assert f.shape == (5,)
    assert f[3] == 0.0                               # slew RESERVED -> 0
    assert f[4] == 1.0                               # fire at env idx 4 (env reads fin_act[4])
    assert np.allclose(f[:3], [0.1, 0.2, 0.3])


def test_live_dims_and_bad_inputs():
    assert live_action_dim("limiter_2") == 3
    assert live_action_dim("finisher_0") == 4
    assert live_action_dim("adversary_0") == 3
    with pytest.raises(ValueError):
        pad_env_action("limiter_0", [1.0, 2.0, 3.0, 4.0])    # live dim mismatch
    with pytest.raises(KeyError):
        pad_env_action("mystery_7", [0.0])


# ------------------------------------------------------------- integration
def test_env_steps_with_padded_actions():
    env, scn, lay = make_train_env(_cfg())
    obs, infos = env.reset(seed=0)
    assert set(obs) == set(env.possible_agents)
    live = {aid: np.zeros(live_action_dim(aid), np.float32) for aid in env.agents}
    live["limiter_0"][:] = [5.0, -3.0, 0.0]
    acts = pad_env_actions(live)
    for aid, a in acts.items():
        assert env.action_space(aid).shape == a.shape
    obs, rew, term, trunc, info = env.step(acts)
    v = next(iter(obs.values()))
    assert np.isfinite(v).all()
    assert "coma_D" in info["limiter_0"]
    assert "delta_v_shot_headline" in info["finisher_0"]
