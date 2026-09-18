"""B2 계약 테스트 — manifest 불변식 · partition 단일 정의원 · arm pairing (docs/102).

실행 결과가 아니라 **계약**을 지킨다. 무거운 캠페인은 여기서 돌리지 않는다
(paired 배선 확인용 1 scenario 만 실제로 굴린다).
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shepherd.scripts.b2_manifest import MANIFEST, build, load          # noqa: E402
from shepherd.scripts.mission_rollout import (BINS, MissionResult,      # noqa: E402
                                              partition_bin)


@pytest.fixture(scope="module")
def m():
    if not MANIFEST.exists():
        build()
    return load()


# ── manifest 불변식 ─────────────────────────────────────────────────────────
def test_grid_is_b0_v3_verbatim(m):
    """격자는 재선택되지 않는다 — B0 v3 rows 를 글자 그대로 전개한 것이어야 한다."""
    b0 = json.loads((ROOT / "artifacts/b0/b0_v3_world_contract.json")
                    .read_text(encoding="utf-8"))
    assert m["b0_v3_hash"] == b0["b0_hash"] == "5e7b5b486b9d8a4a"
    want = [(ri, ci, chi) for ri, row in enumerate(b0["grid"]["rows"])
            for ci, chi in enumerate(row["chi_base"])]
    got = [(c["row"], int(c["cell_id"][-1]), c["chi"]) for c in m["cells"]]
    assert got == want
    assert len(m["cells"]) == 56


def test_budget_and_units(m):
    """56 cell x 300 x 2 arm x 3 seed = 100,800 ep · 블록은 연속·중복 없음."""
    assert m["budget"]["episodes_primary"] == 100_800
    assert len(m["units"]) == 56 * 3
    s = 0
    for u in m["units"]:
        assert u["s_lo"] == s and u["s_hi"] - u["s_lo"] == 300
        s = u["s_hi"]
    assert s == m["scenario_ids"]["n"] == 50_400


def test_arms_are_limiter_control_only(m):
    """arm 축은 2 개이고 차이는 limiter controller 뿐이다 (docs/102 §1)."""
    assert set(m["arms"]) == {"SOLO", "RULE_COOP"}
    assert m["arms"]["SOLO"]["limiter_mode"] == "hold"
    assert m["arms"]["SOLO"]["limiter_kw"] is None
    rc = m["arms"]["RULE_COOP"]
    assert rc["limiter_mode"] == "arc"
    assert rc["limiter_kw"]["r_d"] == 9.0
    assert rc["limiter_kw"]["dphi"] == pytest.approx(3.141592653589793 / 6)
    # fallback 은 arm 이 아니다
    assert "fallback" not in m["arms"] and m["fallback"]["status"].startswith("NOT an arm")


def test_boundary_band_is_28_cells(m):
    """forced-fire 대상은 base_rule 의 안쪽 두 점 = 14 x 2 (docs/102 §5.3)."""
    assert sum(1 for c in m["cells"] if c["boundary_band"]) == 28


def test_seed_namespace_is_separate(m):
    """B2 평가 CRN 은 R2a/R2b/MARL training seed 와 섞이지 않는다 (docs/102 §3)."""
    assert m["crn"]["seed_ns"] not in ("r2a_s1", "r2b_p1_v2", "m4_hardkill")
    assert m["crn"]["seed0"] not in (0, 7000)
    assert m["crn"]["seeds"] == [0, 1, 2]


def test_manifest_hash_detects_hand_edit(tmp_path, m):
    h = m["manifest_hash"]
    tampered = dict(m)
    tampered["cells"] = m["cells"][:-1]
    import hashlib
    t = dict(tampered)
    t.pop("manifest_hash")
    assert hashlib.sha256(json.dumps(t, sort_keys=True, default=str).encode()
                          ).hexdigest()[:16] != h


# ── partition 단일 정의원 ───────────────────────────────────────────────────
def _res(label, steps=30, n_contact=0, **meta):
    base = {"first_contact_t": None, "first_engage_t": None, "n_engage": 0,
            "net_spent_step": None, "hard_kill": False, "veto_events": 0}
    return MissionResult(label=label, outcome=label, seed=0, steps=steps,
                         n_contact=n_contact, meta={**base, **meta})


def test_bin_clean_capture():
    assert partition_bin(_res("NET_CAPTURE")) == "N"


def test_bin_capture_with_contact_is_illegal():
    """same_tick_precedence ① — 도달가능성 논증이 아니라 코드로 박아둔다."""
    assert partition_bin(_res("CAPTURE_WITH_CONTACT", n_contact=1)) == "H_illegal"


def test_bin_contact_before_net_spent_is_illegal():
    r = _res("HARD_KILL", steps=20, n_contact=1, first_contact_t=9,
             net_spent_step=15, hard_kill=True)
    assert partition_bin(r) == "H_illegal"


def test_bin_contact_on_net_spent_tick_is_illegal():
    """KINETIC 은 NET_SPENT **다음** tick 부터 (off-by-one guard)."""
    r = _res("HARD_KILL", steps=16, n_contact=1, first_contact_t=14,   # -> _step_i 15
             net_spent_step=15, hard_kill=True)
    assert partition_bin(r) == "H_illegal"


def test_bin_contact_after_net_spent_is_fallback():
    r = _res("HARD_KILL", steps=30, n_contact=1, first_contact_t=15,   # -> _step_i 16
             net_spent_step=15, hard_kill=True)
    assert partition_bin(r) == "H_fb"


def test_bin_engagement_only_kill_is_illegal():
    """이동 전 스캔이 놓치고 env resolver 만 본 접촉 (실측 s=901) 도 latch 된다."""
    r = _res("HARD_KILL", steps=24, n_contact=0, first_engage_t=23, hard_kill=True)
    assert partition_bin(r) == "H_illegal"


def test_bin_kill_without_net_spent_is_illegal():
    """event 기록이 없어도 네트가 소진되지 않은 kill 은 legitimate 일 수 없다."""
    r = _res("HARD_KILL", steps=24, hard_kill=True)
    assert partition_bin(r) == "H_illegal"


def test_bin_other():
    assert partition_bin(_res("PENETRATED")) == "F_other"
    assert partition_bin(_res("TRUNCATED")) == "F_other"
    assert partition_bin(_res("SPENT_FAIL", net_spent_step=20)) == "F_other"


def test_bins_are_exhaustive_and_exclusive():
    for lab in ("NET_CAPTURE", "CAPTURE_WITH_CONTACT", "HARD_KILL", "PENETRATED",
                "SPENT_FAIL", "TRUNCATED"):
        assert partition_bin(_res(lab, net_spent_step=10)) in BINS


# ── 실제 배선: arm pairing (1 scenario) ─────────────────────────────────────
def test_paired_scenario_shares_world_and_initial_state(m):
    """두 arm 이 같은 contract · 같은 초기 world-state 를 소비한다 (docs/102 §7-2/3)."""
    from shepherd.scripts.b2_run import _index, run_scenario
    _cells, blocks = _index(m)
    recs = run_scenario(m, blocks, m["units"][0]["s_lo"])    # 내부 assert 가 본검사
    assert [r["arm"] for r in recs] == ["SOLO", "RULE_COOP"]
    assert recs[0]["s"] == recs[1]["s"]
    assert recs[0]["chi"] == recs[1]["chi"] and recs[0]["eta"] == recs[1]["eta"]
    assert all(r["bin"] in BINS for r in recs)
