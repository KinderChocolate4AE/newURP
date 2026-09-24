"""CLBC1-F3 sealed design, gate, label, and smoke tests."""
from __future__ import annotations

import json

import numpy as np
import pytest

from scripts.b0_v3_capturer_clbc1_f3 import (
    CONTROL, F3, INVALID, PASS, STOP, apply_gate, robust_label_from_obs, run_seed,
)
from scripts.b0_v3_capturer_clbc1_f3_manifest import ARMS, MANIFEST, build


def _block(n=20, robust=20, nonrobust=10, spent=10, crossing=30, ratio=.66, h=0):
    return {"N": n, "robust_ready_FIRE": robust, "nonrobust_FIRE": nonrobust,
            "SPENT_FAIL": spent, "clean_crossing_episodes": crossing,
            "FIRE_to_N": ratio, "H_illegal": h}


def _fit(bal=.7, fpr=.5, tpr=.9):
    block = {"balanced_accuracy": bal, "fpr": fpr, "tpr": tpr}
    return {"validation": dict(block), "validation_soft_gate": block}


OK = {"lineage": True, "pairing": True, "finite": True, "completion": True,
      "exact_parent": True, "collection": True, "fire_head_only": True,
      "authoritative_fire_logging": True, "budget": True}


def test_manifest_is_sealed_fresh_and_budgeted():
    saved = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert saved == build()
    assert saved["manifest_hash"] == "00a9e45ff4b0506d"
    assert saved["collection"]["seed0"] == 131000
    assert saved["evaluation"]["seed0"] == 141000
    assert saved["collection"]["episodes_total"] == 224
    assert saved["evaluation"]["episodes_total"] == 1120
    assert saved["scope"]["rl_updates"] == 0


def test_robust_label_is_observable_and_excludes_boxed():
    obs = np.zeros(10, np.float32)
    obs[-4], obs[-3] = 1.0, 1.0
    assert robust_label_from_obs(obs)
    obs[-3] = 0.0
    assert not robust_label_from_obs(obs)
    obs[-4], obs[-3] = 0.0, 1.0
    assert not robust_label_from_obs(obs)


def test_gate_is_strict_per_seed_and_fail_closed():
    per_seed = {}
    fits = {}
    for seed in (0, 1):
        per_seed[seed] = {
            CONTROL: _block(),
            F3: _block(n=21, robust=21, nonrobust=4, spent=4, crossing=31, ratio=.84),
        }
        fits[seed] = {CONTROL: _fit(), F3: _fit(bal=.95, fpr=.05, tpr=.95)}
    assert apply_gate(per_seed, fits, OK)["decision"] == PASS
    tied = {s: {a: dict(v) for a, v in arms.items()} for s, arms in per_seed.items()}
    tied[1][F3]["N"] = tied[1][CONTROL]["N"]
    assert apply_gate(tied, fits, OK)["decision"] == STOP
    assert apply_gate(per_seed, fits, {**OK, "collection": False})["decision"] == INVALID


@pytest.mark.torch
def test_smoke_changes_only_fire_head_and_never_runs_ppo(tmp_path, monkeypatch):
    pytest.importorskip("torch")
    from shepherd.scripts.train_m4 import M4Runner
    from shepherd.train.mappo import MAPPOTrainer

    def boom(*args, **kwargs):
        raise AssertionError("PPO/RL path must not run in CLBC1-F3")

    monkeypatch.setattr(MAPPOTrainer, "update", boom)
    monkeypatch.setattr(M4Runner, "update", boom, raising=False)
    monkeypatch.setattr(M4Runner, "collect_rollout", boom, raising=False)
    summary = run_seed(0, "cpu", smoke=True, out_root=tmp_path)

    assert summary["provenance"]["rl_updates"] == 0
    assert summary["identity"]["common_parent"]
    assert summary["identity"]["exact_f2_parent"] is None
    assert summary["identity"]["fire_head_only"]
    fixed = ("lim_actor", "fin_mean", "fin_log_std", "critic", "obs_norm")
    assert all(summary["identity"]["after"][CONTROL][key]
               == summary["identity"]["after"][F3][key] for key in fixed)
    assert (summary["identity"]["after"][CONTROL]["fin_fire_logit"]
            != summary["identity"]["after"][F3]["fin_fire_logit"])
    assert summary["collection"]["rl_updates"] == 0
    assert summary["collection"]["fire_suppression"].startswith("collection only")
    assert summary["authoritative_fire_logging"]
    assert all(summary["evaluation"][arm]["n"] == 2 for arm in ARMS)
    assert not (tmp_path / "smoke" / "seed0" / ".done").exists()
