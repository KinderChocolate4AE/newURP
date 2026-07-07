"""Torch-required tests for the M3a trainer stack (docs/11 SS3).

Same policy as the 2B/2C tests: structural invariants; importorskip keeps the
torch-free CI green; the lab venv runs the lot. Uses a REDUCED env config
(single-segment viability, short episodes) -- these are wiring tests, not
learning tests.
"""
from __future__ import annotations

import copy
import json
import pathlib

import numpy as np
import pytest
import yaml

torch = pytest.importorskip("torch")

from shepherd.scripts.train_ippo import hold_bundle, make_scripted_ctx
from shepherd.scripts.train_m3a import (M3ARunner, load_warm, m3_eval_bundle,
                                        ntfy)
from shepherd.scripts.analyze_m3a_playin import decide_playin
from shepherd.train.mappo import MAPPOConfig, MAPPOTrainer

pytestmark = pytest.mark.torch

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _env_cfg():
    cfg = yaml.safe_load(open(ROOT / "configs" / "m2_l2_train.yaml"))
    cfg["viability"]["n_samples"] = 120
    cfg["viability"]["n_segments"] = 1
    cfg["train"]["episode_len"] = 10
    return cfg


def _run_cfg():
    cfg = yaml.safe_load(open(ROOT / "configs" / "m3a_s1_scratch.yaml"))
    cfg["loop"].update(total_env_steps=64, rollout_env_steps=32,
                       eval_interval_updates=1, eval_episodes=1)
    cfg["mappo"].update(epochs=2, minibatch_size=16)
    cfg["randomize"]["enabled"] = False
    cfg["wandb"]["enabled"] = False
    return cfg


def test_runner_rollout_update_eval_smoke(tmp_path):
    run_cfg, env_cfg = _run_cfg(), _env_cfg()
    r = M3ARunner(env_cfg, run_cfg, seed=0, device="cpu")
    assert r.obs_dim == 63 and r.n == 4
    r.collect_rollout()
    stats = r.update()
    assert np.isfinite(stats["limiter/approx_kl"])
    roll = r.rolling()
    assert "train/clean_cross_rate" in roll and "train/boxed_frac" in roll
    frozen_ev, train_ev = r.evaluate(episodes=1)
    for key in ("sel_score", "clean_cross_rate", "boxed_fire_rate", "fire_rate",
                "capture_count", "boxed_dwell_frac_mean", "o_near_rate_mean",
                "release_before_fire_rate", "headline_m3_sum_mean",
                "fire_chains"):
        assert key in frozen_ev, key
    # s1_only mode -> train-eval is a DISTINCT S1-constants bundle
    assert train_ev is not frozen_ev
    r.save(tmp_path, tag="best")
    assert (tmp_path / "ckpt_mappo_best.pt").exists()
    state = json.loads((tmp_path / "run_state_best.json").read_text())
    assert state["stage"] == "s1" and state["capture_count_train"] >= 0


def test_eval_bundle_frozen_vs_stage_constants():
    env_cfg = _env_cfg()
    run_cfg = _run_cfg()
    from shepherd.train.make_env_m3 import m3_params_from_cfg
    m3 = m3_params_from_cfg(run_cfg["m3"], env_cfg)
    ctx = make_scripted_ctx(env_cfg)
    lim_fn, fin_fn = hold_bundle(ctx)
    ev = m3_eval_bundle(env_cfg, m3, lim_fn, fin_fn, episodes=1, seed0=11,
                        stage=None)
    s1 = run_cfg["curriculum"]["s1"]
    ev1 = m3_eval_bundle(env_cfg, m3, lim_fn, fin_fn, episodes=1, seed0=11,
                         stage=s1)
    assert ev["episodes"] == ev1["episodes"] == 1
    assert np.isfinite(ev["return_mean"]) and np.isfinite(ev1["return_mean"])
    assert isinstance(ev["fire_chains"], list)


def test_warm_start_loads_weights_and_norm(tmp_path):
    run_cfg, env_cfg = _run_cfg(), _env_cfg()
    src = M3ARunner(env_cfg, run_cfg, seed=1, device="cpu")
    src.norm.normalize(np.random.default_rng(0).normal(size=src.obs_dim),
                       update=True)
    src.save(tmp_path, tag="best")

    dst = M3ARunner(env_cfg, run_cfg, seed=2, device="cpu")

    def _w(runner):
        # first WEIGHT matrix -- next(parameters()) is log_std, which is
        # 0-initialized for every seed (server-caught test defect 2026-07-07)
        return next(p for p in runner.tr.lim_actor.parameters()
                    if p.dim() >= 2).detach().clone()

    w_src = _w(src)
    assert not torch.allclose(w_src, _w(dst))           # different init draws
    meta = load_warm(dst, tmp_path, "best", "cpu")
    assert torch.allclose(w_src, _w(dst))
    assert meta["optimizer"] == "fresh" and len(meta["warm_ckpt_sha256_12"]) == 12
    assert dst.norm.state_dict() == src.norm.state_dict()


def test_warm_start_shape_mismatch_raises(tmp_path):
    run_cfg, env_cfg = _run_cfg(), _env_cfg()
    bad = MAPPOTrainer(17, 2, MAPPOConfig(rollout_steps=8, total_timesteps=8))
    bad.save(tmp_path / "ckpt_mappo_best.pt")
    (tmp_path / "obs_norm_best.json").write_text(json.dumps(
        {"mean": [0.0] * 17, "var": [1.0] * 17, "count": 1.0}))
    r = M3ARunner(env_cfg, run_cfg, seed=0, device="cpu")
    with pytest.raises(ValueError, match="shape mismatch"):
        load_warm(r, tmp_path, "best", "cpu")


def test_ntfy_noop_without_topic(monkeypatch):
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    ntfy("should be a no-op")                            # must not raise


def test_decide_playin_preregistered_rule():
    W = {"clean_cross_rate_last3": 0.30, "boxed_fire_rate_last3": 0.40,
         "heldout_clean": 0.10}
    S = {"clean_cross_rate_last3": 0.10, "boxed_fire_rate_last3": 0.10,
         "heldout_clean": 0.10}
    assert decide_playin(W, S, 0.02)[0:2] == ("warm", 1)   # rule 1 dominant
    W2 = dict(W, clean_cross_rate_last3=0.11)
    assert decide_playin(W2, S, 0.02)[0:2] == ("scratch", 2)  # lower boxed_fire wins
    W3 = dict(W2, boxed_fire_rate_last3=0.10, heldout_clean=0.20)
    assert decide_playin(W3, S, 0.02)[0:2] == ("warm", 3)
    W4 = dict(W3, heldout_clean=0.11)
    assert decide_playin(W4, S, 0.02)[0:2] == ("scratch", 4)  # ratified tie-break
    Wn = dict(W2, boxed_fire_rate_last3=0.10, heldout_clean=float("nan"))
    assert decide_playin(Wn, S, 0.02)[0:2] == ("scratch", 4)  # nan -> rule 4
