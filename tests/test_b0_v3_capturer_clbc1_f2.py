"""CLBC1-F2 sealed design, gate, and smoke regression tests."""
from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np

import pytest

from scripts.b0_v3_capturer_clbc1_f2 import (F2, INVALID, PASS, STOP, FireAuditEnv,
                                              apply_gate, pair_keys, run_seed)
from scripts.b0_v3_capturer_clbc1_f2_manifest import ARMS, MANIFEST, build


def _block(n=10, robust=10, spent=5, crossing=20, angle=10.0, h=0):
    return {"N": n, "robust_ready_FIRE": robust, "SPENT_FAIL": spent,
            "clean_crossing_episodes": crossing,
            "sampled_to_mean_deg_median": angle, "H_illegal": h}


OK = {"lineage": True, "pairing": True, "finite": True,
      "completion": True, "exact_parent": True, "single_factor": True,
      "authoritative_fire_logging": True, "budget": True}


def test_manifest_is_sealed_fresh_and_budgeted():
    saved = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert saved == build()
    assert saved["manifest_hash"] == "567f134a862335ce"
    assert saved["evaluation"]["namespace"] == "b0v3_capturer_clbc1_f2_eval_v1"
    assert saved["evaluation"]["seed0"] == 121000
    assert saved["evaluation"]["episodes_total"] == 1120
    assert saved["parent"]["new_training_steps"] == 0
    assert saved["scope"]["rl_updates"] == 0


def test_gate_is_strict_per_seed_and_fail_closed():
    good = {
        0: {"control": _block(),
            "f2_low_std": _block(n=11, robust=11, spent=5, crossing=20, angle=4)},
        1: {"control": _block(),
            "f2_low_std": _block(n=12, robust=12, spent=4, crossing=22, angle=3)},
    }
    assert apply_gate(good, OK)["decision"] == PASS
    tied = {seed: {arm: dict(block) for arm, block in arms.items()}
            for seed, arms in good.items()}
    tied[1][F2]["N"] = tied[1]["control"]["N"]
    assert apply_gate(tied, OK)["decision"] == STOP
    assert apply_gate(good, {**OK, "authoritative_fire_logging": False})["decision"] == INVALID


def test_fire_audit_records_env_step_judge_not_policy_input_observation():
    class FakeEnv:
        finisher_id = "finisher_0"
        tau_deploy = 0.3
        fsm = SimpleNamespace(state=SimpleNamespace(value="LOADED"))

        @staticmethod
        def _p(state):
            return np.asarray(state[:3], float)

        @staticmethod
        def _v(state):
            return np.asarray(state[3:6], float)

        @staticmethod
        def _e(state):
            return np.asarray(state[6:9], float)

        def _states(self):
            fin = np.array([0, 0, 0, 0, 0, 0, 1, 0, 0], float)
            att = np.array([10, 0, 0, -1, 0, 0, -1, 0, 0], float)
            return [], fin, att

        def step(self, actions):
            info = {self.finisher_id: {
                "fire_event": True, "v_shot_soft": .93, "v_shot_worst": 1.0,
                "p_feasible": .75, "boxed_in": False,
            }}
            return {}, {}, {}, {}, info

    env = FireAuditEnv(FakeEnv())
    env.step({"finisher_0": np.array([1, 0, 0, 0, 1], np.float32)})
    assert env.events == [{
        "t": 0, "net_phase_before": "LOADED", "v_shot_soft": .93,
        "v_shot_worst": 1.0, "p_feasible": .75, "boxed_in": False,
        "robust_ready": True, "fire_command": 1.0,
        "ang_att_teacher_deg": 0.0, "ang_cmd_teacher_deg": 0.0,
    }]


@pytest.mark.torch
def test_smoke_changes_only_aim_log_std_and_never_runs_ppo(tmp_path, monkeypatch):
    pytest.importorskip("torch")
    from shepherd.scripts.train_m4 import M4Runner
    from shepherd.train.mappo import MAPPOTrainer

    def boom(*args, **kwargs):
        raise AssertionError("PPO/RL path must not run in CLBC1-F2")

    monkeypatch.setattr(MAPPOTrainer, "update", boom)
    monkeypatch.setattr(M4Runner, "update", boom, raising=False)
    monkeypatch.setattr(M4Runner, "collect_rollout", boom, raising=False)
    summary = run_seed(0, "cpu", smoke=True, out_root=tmp_path)

    assert summary["provenance"]["rl_updates"] == 0
    assert summary["identity"]["common_parent"]
    assert summary["identity"]["single_factor"]
    assert not summary["identity"]["exact_sealed_parent"]
    assert all(summary["parents"][arm]["exact_parent"] is None for arm in ARMS)
    assert summary["interventions"]["control"]["log_std_values"] == [-1.0] * 3
    assert summary["interventions"][F2]["log_std_values"] == pytest.approx([-2.3] * 3)
    fixed = ("lim_actor", "fin_mean", "fin_fire_logit", "critic", "obs_norm")
    assert all(summary["interventions"]["control"]["after"][key]
               == summary["interventions"][F2]["after"][key] for key in fixed)
    assert summary["authoritative_fire_logging"]
    assert all(summary["evaluation"][arm]["n"] == 2 for arm in ARMS)
    assert pair_keys(summary["evaluation"]["control"]["records"]) == pair_keys(
        summary["evaluation"][F2]["records"])
    traces = list((tmp_path / "smoke" / "seed0" / "traces").glob("trace_*.json"))
    assert traces
    trace = json.loads(traces[0].read_text(encoding="utf-8"))
    assert trace["cone_half_angle_rad"] == pytest.approx(0.2121, abs=1e-4)
    assert "accepted_fire_judge" in trace
    assert not (tmp_path / "smoke" / "seed0" / ".done").exists()
