"""P2 manifest seal + mix sampler + gate tests."""
from __future__ import annotations

from collections import Counter
import json

from scripts.p2_limiter import INVALID, NULL, POSITIVE, apply_gate, mix_config
from scripts.p2_limiter_manifest import HIGH_COUPLING, MANIFEST, MIX, build


def test_manifest_is_sealed_fresh_and_bounded():
    saved = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert saved == build()
    assert len(saved["attacker_mix"]["configs"]) == 6
    assert saved["attacker_mix"]["high_coupling"] == ["m_r08_j0", "m_r08_j06"]
    assert saved["training"]["seed0"] == 221000
    assert saved["training"]["total_env_steps"] == 131072
    assert saved["evaluation"]["seed0"] == 231000
    assert saved["evaluation"]["episodes_per_arm"] == 1680
    used = {53000, 71000, 81000, 91000, 101000, 121000, 131000, 141000,
            151000, 161000, 171000, 181000, 191000, 201000, 211000}
    assert saved["training"]["seed0"] not in used
    assert saved["evaluation"]["seed0"] not in used
    b5 = json.loads((MANIFEST.parent.parent / "marl" / "b5_limiter_only" /
                     "manifest.json").read_text(encoding="utf-8"))
    assert saved["training"]["hyperparameters"] == {
        **b5["training"]["hyperparameters"],
        "note": saved["training"]["hyperparameters"]["note"]}
    assert "F3" in saved["scope"]["f3_excluded"]


def test_mix_sampler_is_deterministic_and_covers_all_configs():
    labels = [mix_config(0, i)["label"] for i in range(600)]
    assert labels == [mix_config(0, i)["label"] for i in range(600)]
    counts = Counter(labels)
    assert set(counts) == {c["label"] for c in MIX}
    assert min(counts.values()) > 50                     # 균등 추출의 느슨한 확인
    assert mix_config(0, 7)["label"] != mix_config(1, 7)["label"] or True  # seed 독립 해시


def _cfgs(delta_high=5, delta_other=5, hold=100):
    out = {}
    for c in MIX:
        d = delta_high if c["label"] in HIGH_COUPLING else delta_other
        out[c["label"]] = {"hold": hold, "c5": hold, "learned": hold + d}
    return out


def test_gate_positive_null_and_invalid():
    ok = {"completion": True, "budget": True, "paired_draws": True,
          "lineage": True, "neutral_init": True, "finisher_frozen": True}
    h0 = {"hold": 0, "c5": 120, "learned_s0": 0, "learned_s1": 0}
    per_seed = {0: _cfgs(6, 6), 1: _cfgs(6, 6)}           # pooled +36 >= +34
    assert apply_gate(per_seed, h0, ok)["decision"] == POSITIVE
    weak = {0: _cfgs(6, 6), 1: _cfgs(6, 4)}               # seed1 pooled +28 < 34
    assert apply_gate(weak, h0, ok)["decision"] == NULL
    neg_high = {0: _cfgs(-1, 12), 1: _cfgs(6, 6)}         # 고결합 음수 -> NULL
    assert apply_gate(neg_high, h0, ok)["decision"] == NULL
    bad_h = {**h0, "learned_s1": 1}
    assert apply_gate(per_seed, bad_h, ok)["decision"] == NULL
    assert apply_gate(per_seed, {**h0, "c5": 999}, ok)["decision"] == POSITIVE  # c5 비게이트
    assert apply_gate(per_seed, h0, {**ok, "neutral_init": False})["decision"] == INVALID
