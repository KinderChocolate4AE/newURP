"""CLBC1 result-blind contract, pairing, single-factor training, and gate tests."""
from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

from scripts.b0_v3_capturer_clbc1 import (INVALID, PASS, STOP, apply_gate,
                                           eligible_collection_state, pair_keys,
                                           run_seed, scenario_plan)
from scripts.b0_v3_capturer_clbc1_manifest import ARMS, MANIFEST, build
from shepherd.scripts.b2_manifest import load as load_b2

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_manifest_file_matches_builder_and_budget_is_sealed():
    m = build()
    assert json.loads(MANIFEST.read_text(encoding="utf-8")) == m == build()
    assert m["schema"] == "b0-v3-capturer-clbc1-manifest-v1"
    assert m["collection"]["episodes_total"] == 2 * 28
    assert m["evaluation"]["episodes_total"] == 2 * 2 * 28 * 10 == 1120
    assert m["training"]["arms"]["replay"].startswith("128 original")
    assert m["training"]["arms"]["clbc1"].startswith("128 original + 128 closed")
    assert m["promotion"].endswith("W6 remains closed")


def test_namespaces_are_new_and_plans_cover_the_sealed_grid():
    m, b2 = build(), load_b2()
    pilot = json.loads((ROOT / "artifacts/marl/b0_v3_pilot_manifest.json")
                       .read_text(encoding="utf-8"))
    b5 = json.loads((ROOT / "artifacts/marl/b5_limiter_only/manifest.json")
                    .read_text(encoding="utf-8"))
    f1 = json.loads((ROOT / "artifacts/marl/b0_v3_capturer_f1/manifest.json")
                    .read_text(encoding="utf-8"))
    old = {(pilot[k]["seed0"], pilot[k]["seed_ns"])
           for k in ("initialization", "training", "evaluation")}
    old |= {(b5[k]["seed0"], b5[k]["seed_ns"])
            for k in ("training", "evaluation")}
    old.add((f1["evaluation"]["seed0"], f1["evaluation"]["namespace"]))
    new = {(m["collection"]["seed0"], m["collection"]["namespace"]),
           (m["evaluation"]["seed0"], m["evaluation"]["namespace"])}
    assert not ({s for s, _ in old} & {s for s, _ in new})
    assert not ({n for _, n in old} & {n for _, n in new})
    assert len({s for s, _ in new}) == len({n for _, n in new}) == 2
    for seed in (0, 1):
        collect = scenario_plan(m["collection"], b2, seed)
        evaluate = scenario_plan(m["evaluation"], b2, seed)
        assert len(collect) == 28 and len(evaluate) == 280
        assert len({p["cell_id"] for p in collect}) == 28
        assert len({p["cell_id"] for p in evaluate}) == 28
        assert [p["scenario_id"] for p in evaluate] == list(range(280))
        assert pair_keys(evaluate) == pair_keys(
            scenario_plan(m["evaluation"], b2, seed))
    by_sid = {p["scenario_id"]: p["cell_id"]
              for p in scenario_plan(m["evaluation"], b2, 0)}
    assert all(by_sid[sid] == cell for cell, sid in m["traces"]["scenarios"])


def _block(n, crossing, angle, h=0):
    return {"N": n, "clean_crossing_episodes": crossing,
            "mean_to_teacher_deg_median": angle, "H_illegal": h}


OK = {"lineage": True, "pairing": True, "finite": True, "completion": True,
      "common_parent": True, "frozen_state": True, "budget": True}


def test_gate_is_strict_per_seed_and_hold_safety_is_zero():
    good = {
        0: {"replay": _block(5, 20, 40), "clbc1": _block(6, 21, 39)},
        1: {"replay": _block(4, 18, 42), "clbc1": _block(5, 19, 41)},
    }
    assert apply_gate(good, OK)["decision"] == PASS
    tied = json.loads(json.dumps(good)); tied["1"]["clbc1"]["N"] = 4
    tied = {int(k): v for k, v in tied.items()}
    assert apply_gate(tied, OK)["decision"] == STOP
    unsafe = json.loads(json.dumps(good)); unsafe["0"]["clbc1"]["H_illegal"] = 1
    unsafe = {int(k): v for k, v in unsafe.items()}
    assert apply_gate(unsafe, OK)["decision"] == STOP
    assert apply_gate(good, {**OK, "pairing": False})["decision"] == INVALID


def test_collection_filter_depends_only_on_phase_and_teacher_validity():
    assert eligible_collection_state("LOADED", [1, 0, 0])
    assert not eligible_collection_state("DEPLOYING", [1, 0, 0])
    assert not eligible_collection_state("LOADED", [0, 0, 0])
    assert not eligible_collection_state("LOADED", [float("nan"), 0, 0])


def test_sealed_inputs_are_byte_identical():
    expected = {
        "artifacts/marl/b0_v3_pilot_manifest.json":
            "02119ec76672e660e58baf828c1cae03693932baa05b2329ddeb5328465572ba",
        "artifacts/marl/b0_v3_pilot/readout.json":
            "91ec12448660ca0ab122d557027b9c3c8967f7de6272f4037c7df5e0cd75e81c",
        "artifacts/marl/b0_v3_pilot/bc_dataset.json":
            "ec8b4704a61ba60fcb8890d010d119b47fa9c81023df65cbeb25ea9d388730cd",
        "artifacts/marl/b0_v3_pilot/bc_dataset.npz":
            "55ad438c762565a15a83f1c346c605936e2f8b22234e80c0da90428efd091af9",
        "artifacts/marl/b0_v3_capturer_f1/manifest.json":
            "ac3c2c8bcb848096539daea51fdda1465397712f519995516482a4b1795001fb",
        "artifacts/marl/b0_v3_capturer_f1/readout.json":
            "759bcecb9f6afd4f7e0f1b93adbe6e6b77974268e6d74e0c4c3849dac18abe1a",
    }
    for rel, want in expected.items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == want


@pytest.mark.torch
def test_smoke_uses_hold_limiter_and_never_runs_ppo(tmp_path, monkeypatch):
    pytest.importorskip("torch")
    from shepherd.scripts import mission_rollout
    from shepherd.scripts.train_m4 import M4Runner
    from shepherd.train.mappo import MAPPOTrainer

    def boom(*args, **kwargs):
        raise AssertionError("PPO/RL path must not run in CLBC1")

    monkeypatch.setattr(MAPPOTrainer, "update", boom)
    monkeypatch.setattr(M4Runner, "update", boom, raising=False)
    monkeypatch.setattr(M4Runner, "collect_rollout", boom, raising=False)
    original_run_episode = mission_rollout.run_episode
    calls = []

    def checked_run_episode(*args, **kwargs):
        calls.append((kwargs.get("scripted_roles"), kwargs.get("limiter_mode"),
                      kwargs.get("fire_mode")))
        assert kwargs.get("scripted_roles") == ("limiter",)
        assert kwargs.get("limiter_mode") == "hold"
        assert kwargs.get("fire_mode") == "clean"
        return original_run_episode(*args, **kwargs)

    monkeypatch.setattr(mission_rollout, "run_episode", checked_run_episode)
    summary = run_seed(0, "cpu", smoke=True, out_root=tmp_path)
    assert calls
    assert summary["provenance"]["rl_updates"] == 0
    assert summary["collection"]["n_episodes"] == 2
    assert summary["collection"]["n_rows"] > 0
    tr = summary["training"]
    assert tr["common_parent_equal"] and tr["optimizer_initial_state_equal"]
    assert all(tr["arms"][a]["frozen_state_bit_identical"] for a in ARMS)
    assert all(tr["arms"][a]["steps"] == 4 for a in ARMS)
    assert tr["arms"]["replay"]["closed_loop_rows_per_batch"] == 0
    assert tr["arms"]["clbc1"]["closed_loop_rows_per_batch"] == 128
    assert (tr["arms"]["replay"]["first_half_original_index_hash"]
            == tr["arms"]["clbc1"]["first_half_original_index_hash"])
    assert pair_keys(summary["evaluation"]["replay"]["records"]) == pair_keys(
        summary["evaluation"]["clbc1"]["records"])
    assert all(summary["evaluation"][a]["n"] == 2 for a in ARMS)
    trace = json.loads(next((tmp_path / "smoke" / "seed0" / "traces")
                            .glob("trace_*.json")).read_text(encoding="utf-8"))
    assert trace["cone_half_angle_rad"] == pytest.approx(0.2121, abs=1e-4)
    assert trace["cone_range_max"] == pytest.approx(8.22)
    assert not (tmp_path / "smoke" / "seed0" / ".done").exists()
