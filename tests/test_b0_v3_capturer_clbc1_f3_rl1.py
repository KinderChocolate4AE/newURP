"""RL1 manifest, gate, and partial-update wiring tests."""
from __future__ import annotations

from collections import Counter
import json
from types import SimpleNamespace

import numpy as np
import pytest

from scripts.b0_v3_capturer_clbc1_f3_rl1 import (
    CONTROL, INVALID, PASS, RL1, STOP, FrozenNorm, _configure_rl1, apply_gate,
)
from scripts.b0_v3_capturer_clbc1_f3_rl1_manifest import MANIFEST, build


def _block(n=50, robust=50, nonrobust=1, spent=1, crossing=100, ratio=.98, h=0):
    return {"N": n, "robust_ready_FIRE": robust, "nonrobust_FIRE": nonrobust,
            "SPENT_FAIL": spent, "clean_crossing_episodes": crossing,
            "FIRE_to_N": ratio, "H_illegal": h}


OK = {"lineage": True, "pairing": True, "finite": True, "completion": True,
      "exact_parent": True, "partial_optimizer": True, "frozen_identity": True,
      "authoritative_fire_logging": True, "budget": True}


def test_manifest_is_sealed_fresh_and_bounded():
    saved = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert saved == build()
    assert saved["manifest_hash"] == "8ea53634ec08e9d9"
    assert saved["training"]["seed0"] == 151000
    assert saved["evaluation"]["seed0"] == 161000
    assert saved["training"]["total_env_steps"] == 32768
    assert saved["evaluation"]["episodes_total"] == 1120
    assert saved["evaluation"]["sealed_pilot_280_reused"] is False
    assert saved["scope"]["depends_on_scripted_limiter"] is True
    assert "learned cooperation" in saved["scope"]["not_evidence_for"]
    f3 = json.loads((MANIFEST.parent.parent / "b0_v3_capturer_clbc1_f3" /
                     "manifest.json").read_text(encoding="utf-8"))
    assert saved["evaluation"]["seed0"] != f3["evaluation"]["seed0"]
    assert saved["evaluation"]["namespace"] != f3["evaluation"]["namespace"]
    assert saved["training"]["trainable"] == ["fin_actor.mean", "critic",
                                                "critic.value_norm"]
    assert "no forced FIRE" in saved["training"]["capturer"]


def test_gate_is_strict_per_seed_and_fail_closed():
    per_seed = {}
    for seed in (0, 1):
        per_seed[seed] = {
            CONTROL: _block(),
            RL1: _block(n=51, robust=51, crossing=101, ratio=.99),
        }
    assert apply_gate(per_seed, OK)["decision"] == PASS
    tied = {s: {a: dict(v) for a, v in arms.items()} for s, arms in per_seed.items()}
    tied[1][RL1]["N"] = tied[1][CONTROL]["N"]
    assert apply_gate(tied, OK)["decision"] == STOP
    assert apply_gate(per_seed, {**OK, "frozen_identity": False})["decision"] == INVALID


def test_frozen_norm_ignores_update_requests():
    from shepherd.train.obs_norm import RunningNorm
    base = RunningNorm(2)
    base.update([1.0, 2.0])
    before = base.state_dict()
    frozen = FrozenNorm(base)
    frozen.normalize([100.0, 200.0], update=True)
    assert frozen.state_dict() == before


@pytest.mark.torch
def test_partial_optimizer_contains_only_aim_mean_and_critic():
    torch = pytest.importorskip("torch")

    class Norm:
        def normalize(self, x, update=False):
            return np.asarray(x, np.float32)

        def state_dict(self):
            return {"dim": 3, "clip": 10.0, "count": 1.0,
                    "mean": [0.0] * 3, "var": [1.0] * 3}

        def load_state_dict(self, state):
            return None

    fin = SimpleNamespace(mean=torch.nn.Linear(3, 3),
                          fire_logit=torch.nn.Linear(3, 1),
                          log_std=torch.nn.Parameter(torch.zeros(3)))
    trainer = SimpleNamespace(
        lim_actor=torch.nn.Linear(3, 3), fin_actor=fin,
        critic=torch.nn.Linear(3, 1),
        cfg=SimpleNamespace(freeze_limiter=False, freeze_finisher=False,
                            total_timesteps=1, rollout_steps=1, lr=1e-3,
                            ent_coef_finisher=0.0),
        lim_dim=3, _rng=np.random.default_rng(0), device=torch.device("cpu"),
    )
    runner = SimpleNamespace(
        pilot_manifest={"training": {"seed0": 1, "seed_ns": "old"}},
        tr=trainer, obs_dim=3, n=1, norm=Norm(), cell_counts=Counter(),
        credit_outcomes=Counter(), ep_records=[],
    )
    m = build()
    setup = _configure_rl1(runner, m, 0, smoke=True)
    assert setup["optimizer_exact"]
    assert isinstance(runner.norm, FrozenNorm)
    assert runner.frozen_roles == ("limiter",)
    assert all(not p.requires_grad for p in runner.tr.lim_actor.parameters())
    assert all(not p.requires_grad for p in runner.tr.fin_actor.fire_logit.parameters())
    assert not runner.tr.fin_actor.log_std.requires_grad
    assert all(p.requires_grad for p in runner.tr.fin_actor.mean.parameters())
    assert all(p.requires_grad for p in runner.tr.critic.parameters())
