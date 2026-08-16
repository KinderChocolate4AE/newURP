"""R-011 회귀 게이트 — `run_curve` ↔ `mission_eval` 를 **판별력 있는 셀**에서 고정.

WHY (감사 Session 2 X-014)
--------------------------
기존 `test_curve_sweep.test_p44g_run_curve_matches_mission_eval_episode_for_episode`
는 두 계측 경로가 같은 판을 돈다는 것을 확인한다. 그런데 고른 셀이

    n=4 · mode="hold" · route_gain=0 (AttackerSpec 기본값)

인데, 실제 캠페인은

    n=2700 · mode="intercept" · route_gain=0.5 / sense_range=30 · baseline_commit=True

이다. 그리고 **hold 팔은 계약 축을 구분하지 못한다** -- 실측(2026-08-17):

    intercept  ep 0..24 에서 reactive vs legacy 라벨 차이 5 건 (13·17·18·19·20)
    hold       ep 0..24 에서 차이 **0 건**

즉 기존 셀은 n 을 6 배로 늘려도 reactive/legacy 를 구분할 수 없다. 두 경로가
계약을 다르게 해석해도 그 셀에서는 드러나지 않는다 -- 통과해도 계약 축에 대한
parity 증거가 아니다.

★ 판정 계약 (Stage 2 규율)
--------------------------
    No parity without discriminating coverage.
    No configured knob without resolved-value verification.

    discrimination == 0                    -> 테스트 무효 (fail). parity 증거 아님
    discrimination > 0 & mismatch == 0     -> PASS
    mismatch > 0                           -> 새 execution-path finding

seed window 를 계약으로 고정하는 이유
-------------------------------------
"n 을 크게 잡으면 확률적으로 판별 사례가 섞이겠지" 에 기대지 않는다. `run_curve` 와
`mission_eval` 은 둘 다 ep 를 0 부터 도는 구조라 window 를 옮길 수 없으므로,
판별 에피소드(13·17·18·19·20)를 포함하는 **최소 구간 ep 0..20** 을 고정한다.
그 구간에서 판별이 사라지면 그건 통과가 아니라 실패다.

torch-free.
"""
from __future__ import annotations

import pytest

from shepherd.m4_env import build_m4_env, mission_eval
from shepherd.scripts.curve_sweep import _default_kw, run_curve

#: 캠페인이 실제로 쓴 T1 reactive 값
CURVE_KW = dict(w_kill=0.5, level="A2", jink=0.6,
                route_gain=0.5, sense_range=30.0, capture_terminates=True)
LEGACY_KW = dict(CURVE_KW, route_gain=0.0, sense_range=float("inf"))

SEED0 = 0
#: ★ 판별 에피소드 13·17·18·19·20 을 포함하는 최소 구간 (실측으로 고정)
N_INTERCEPT = 21
#: 보조 coverage. 판별력이 0 인 셀임을 **기록**하기 위해 최소로만 돈다
N_HOLD = 3


def _labels(records):
    return [r["label"] for r in records]


@pytest.fixture(scope="module")
def cells():
    """셀마다 (reactive run_curve, legacy run_curve, reactive mission_eval)."""
    out = {}
    for name, mode, commit, n in (("intercept", "intercept", True, N_INTERCEPT),
                                  ("hold", "hold", False, N_HOLD)):
        react = _labels(run_curve(SEED0, n, mode=mode, **CURVE_KW)["records"])
        legacy = _labels(run_curve(SEED0, n, mode=mode, **LEGACY_KW)["records"])
        ref: list = []
        mission_eval(SEED0, n, limiter_mode=mode, baseline_commit=commit,
                     records=ref, **_default_kw(**CURVE_KW))
        out[name] = {"reactive": react, "legacy": legacy,
                     "mission_eval": _labels(ref), "n": n, "mode": mode,
                     "commit": commit}
    return out


def _discriminating(cell):
    return [i for i in range(cell["n"]) if cell["reactive"][i] != cell["legacy"][i]]


def _mismatches(cell):
    return [i for i in range(cell["n"])
            if cell["reactive"][i] != cell["mission_eval"][i]]


# ------------------------------------------- resolved-value verification ---
def test_r011_knobs_reach_the_resolved_contract():
    """★ 설정한 knob 이 **resolved contract** 까지 갔는지 먼저 못 박는다.

    Stage 1 교훈 -- 조용히 무시되는 키가 있으면 아래 parity 는 전부 공허해진다.
    """
    c_react = build_m4_env(SEED0, 0, **_default_kw(**CURVE_KW)).contract
    c_legacy = build_m4_env(SEED0, 0, **_default_kw(**LEGACY_KW)).contract

    assert c_react["attacker"]["route_gain"] == 0.5
    assert c_react["attacker"]["sense_range"] == 30.0
    assert c_legacy["attacker"]["route_gain"] == 0.0
    assert c_legacy["attacker"]["sense_range"] == float("inf")
    # 두 계약이 실제로 다른 세계여야 판별이 성립한다
    assert c_react["hash"] != c_legacy["hash"], \
        "reactive/legacy 가 같은 resolved contract 로 붕괴했다 -- 판별 불가"


def test_r011_run_curve_commit_flag_follows_mode():
    """`baseline_commit` 은 mode 에서 파생된다 (curve_sweep 정정 8).

    parity 비교에서 `mission_eval` 쪽에 넘기는 commit 플래그가 `run_curve` 의
    내부 규칙과 어긋나면 두 경로는 애초에 다른 팔을 도는 것이다.
    """
    assert run_curve(SEED0, 1, mode="intercept")["baseline_commit"] is True
    assert run_curve(SEED0, 1, mode="hold")["baseline_commit"] is False


# --------------------------------------------------- ★ discrimination gate ---
def test_r011_intercept_cell_discriminates_the_contract(cells):
    """★ 헤드라인 셀이 계약 축을 실제로 구분하는가. 0 이면 **테스트 무효**.

    이 assertion 이 없으면 parity 통과가 "두 경로가 같은 세계를 본다" 가 아니라
    "그 셀이 아무것도 구분 못 한다" 를 뜻할 수도 있다.
    """
    d = _discriminating(cells["intercept"])
    assert d, ("intercept 셀이 reactive/legacy 를 하나도 구분하지 못했다 -- "
               "이 셀은 parity 증거로 쓸 수 없다 (seed window 재선정 필요)")
    assert len(d) >= 3, f"판별 에피소드가 {len(d)} 건뿐 — window 가 약해졌다: {d}"


# ------------------------------------------------------------- parity gate ---
def test_r011_parity_on_the_discriminating_cell(cells):
    """★ 본 게이트 — 판별력 있는 셀에서 두 실행 경로가 판별로 일치한다."""
    cell = cells["intercept"]
    bad = _mismatches(cell)
    assert not bad, ("run_curve 와 mission_eval 이 갈라졌다 (intercept/reactive):\n"
                     + "\n".join(f"  ep{i}: run_curve {cell['reactive'][i]} != "
                                 f"mission_eval {cell['mission_eval'][i]}" for i in bad))
    # parity 가 판별 사례를 **실제로 지나갔는지** 확인 (지나치지 않았으면 증거가 약하다)
    d = set(_discriminating(cell))
    assert d, "판별 사례를 지나지 않은 parity 는 계약 축 증거가 아니다"


def test_r011_parity_on_the_auxiliary_hold_cell(cells):
    """보조 coverage. hold 팔의 parity 도 보되 **판별 증거로는 취급하지 않는다**."""
    cell = cells["hold"]
    bad = _mismatches(cell)
    assert not bad, ("run_curve 와 mission_eval 이 갈라졌다 (hold):\n"
                     + "\n".join(f"  ep{i}: {cell['reactive'][i]} != "
                                 f"{cell['mission_eval'][i]}" for i in bad))


# ---------------------------------------------------------- coverage 보고 ---
def test_r011_coverage_is_reported(cells, capsys):
    """판별 수와 parity mismatch 를 **분리해서** 기록한다.

    둘을 한 줄로 합치면 "0 mismatch" 가 무엇을 증명했는지 읽을 수 없다.
    """
    with capsys.disabled():
        print("\n[R-011] 계약 판별력 vs 경로 parity")
        for name in ("intercept", "hold"):
            c = cells[name]
            d, m = _discriminating(c), _mismatches(c)
            print(f"  {name} / reactive (n={c['n']}, commit={c['commit']}):")
            print(f"    contract-discriminating episodes : {len(d)}/{c['n']} {d}")
            print(f"    run_curve <-> mission_eval mismatches : {len(m)}/{c['n']}")
        print("    ※ hold 는 판별력 0 인 셀이다 — 기존 test_p44g 가 이 셀을 n=4 로 "
              "돌기 때문에 계약 축 증거가 되지 못한다 (R-011 의 존재 이유)")
    assert cells["intercept"]["n"] == N_INTERCEPT


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q", "-s"]))
