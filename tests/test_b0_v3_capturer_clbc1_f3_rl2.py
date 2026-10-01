"""RL2 manifest, corrected gate, and partial-update wiring tests."""
from __future__ import annotations

from collections import Counter
import json
from types import SimpleNamespace

import numpy as np
import pytest

from scripts.b0_v3_capturer_clbc1_f3_rl2 import (
    CONTROL, INVALID, PASS, RL2, STOP, FrozenNorm, _configure_rl2, apply_gate,
)
from scripts.b0_v3_capturer_clbc1_f3_rl2_manifest import MANIFEST, build


def _block(n=50, robust=50, nonrobust=1, spent=1, crossing=100, total=120,
           ratio=.98, h=0):
    return {"N": n, "robust_ready_FIRE": robust, "nonrobust_FIRE": nonrobust,
            "SPENT_FAIL": spent, "clean_crossing_episodes": crossing,
            "clean_crossings_total": total, "FIRE_to_N": ratio, "H_illegal": h}


OK = {"lineage": True, "pairing": True, "finite": True, "completion": True,
      "exact_parent": True, "partial_optimizer": True, "frozen_identity": True,
      "authoritative_fire_logging": True, "rl1_stop_acknowledged": True,
      "budget": True}


def test_manifest_is_sealed_fresh_and_bounded():
    saved = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert saved == build()
    assert saved["manifest_hash"] == "297d0e271393f388"
    assert saved["training"]["seed0"] == 171000
    assert saved["evaluation"]["seed0"] == 181000
    assert saved["training"]["total_env_steps"] == 32768
    assert saved["evaluation"]["episodes_total"] == 1120
    assert saved["evaluation"]["sealed_pilot_280_reused"] is False
    assert saved["evaluation"]["rl1_draws_reused"] is False
    assert saved["scope"]["depends_on_scripted_limiter"] is True
    assert "STOP_RL1" in saved["scope"]["prior_decisions_unchanged"]
    rl1 = json.loads((MANIFEST.parent.parent / "b0_v3_capturer_clbc1_f3_rl1" /
                      "manifest.json").read_text(encoding="utf-8"))
    assert saved["prerequisites"]["rl1_manifest_hash"] == rl1["manifest_hash"]
    assert saved["training"]["seed0"] != rl1["training"]["seed0"]
    assert saved["evaluation"]["seed0"] != rl1["evaluation"]["seed0"]
    assert saved["training"]["namespace"] != rl1["training"]["namespace"]
    assert saved["evaluation"]["namespace"] != rl1["evaluation"]["namespace"]
    assert saved["training"]["hyperparameters"] == rl1["training"]["hyperparameters"]
    assert saved["prerequisites"]["f3_parent_state"] == rl1["prerequisites"]["f3_parent_state"]
    assert "clean crossing episodes" not in str(saved["gate"]["evaluation_per_seed"])
    assert "clean crossing episodes" in saved["gate"]["diagnostics_reported_not_gated"]


def test_gate_does_not_gate_crossing_but_reports_it():
    per_seed = {}
    for seed in (0, 1):
        per_seed[seed] = {
            CONTROL: _block(),
            RL2: _block(n=51, robust=51, crossing=94, total=130, ratio=.99),
        }
    out = apply_gate(per_seed, OK)
    assert out["decision"] == PASS
    assert out["crossing_reported_not_gated"]["seed1"][RL2]["episodes"] == 94
    assert out["crossing_reported_not_gated"]["seed1"][CONTROL]["total"] == 120
    tied = {s: {a: dict(v) for a, v in arms.items()} for s, arms in per_seed.items()}
    tied[1][RL2]["N"] = tied[1][CONTROL]["N"]
    assert apply_gate(tied, OK)["decision"] == STOP
    worse = {s: {a: dict(v) for a, v in arms.items()} for s, arms in per_seed.items()}
    worse[0][RL2]["nonrobust_FIRE"] = worse[0][CONTROL]["nonrobust_FIRE"] + 1
    assert apply_gate(worse, OK)["decision"] == STOP
    assert apply_gate(per_seed, {**OK, "rl1_stop_acknowledged": False})["decision"] == INVALID


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
    setup = _configure_rl2(runner, m, 0, smoke=True)
    assert setup["optimizer_exact"]
    assert isinstance(runner.norm, FrozenNorm)
    assert runner.frozen_roles == ("limiter",)
    assert all(not p.requires_grad for p in runner.tr.lim_actor.parameters())
    assert all(not p.requires_grad for p in runner.tr.fin_actor.fire_logit.parameters())
    assert not runner.tr.fin_actor.log_std.requires_grad
    assert all(p.requires_grad for p in runner.tr.fin_actor.mean.parameters())
    assert all(p.requires_grad for p in runner.tr.critic.parameters())
