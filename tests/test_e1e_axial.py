"""E1e 회귀 게이트 E-A ~ E-D (docs/83 §32.6). 4/4 통과 전 E1e 실행 금지.

    python -m pytest tests/test_e1e_axial.py -q

torch-free.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pytest

from shepherd.env_sys import SystemSpec, ratified_system
from shepherd.m4_config import m4_config
from shepherd.m4_env import mission_eval
from shepherd.scripts.e1d_commit_geom import _build, _select_step, reference_pass
from shepherd.scripts.e1e_axial_optimum import ARMS, EP0, a_star, margin, s_of_ax
from shepherd.scripts.recoverability_probe import _Driver

_CFG = m4_config()
TAU = float(_CFG["physics"]["tau_deploy"])
RMAX = float(_CFG["viability"]["cone"]["range_max"])
TH = float(_CFG["viability"]["cone"]["half_angle"])
TAN = math.tan(TH)
# ★ 이 파일은 **동결 사전등록**(docs/83 §32)의 상수 게이트다. 2026-08-28 에
#   정본 규약이 "inscribed"(sin) 로 정정됐지만, 여기서 고정하는 것은 사전등록
#   당시의 예측이므로 규약을 "tan" 으로 **명시**한다 (정정 노트 2026-08-28).
KW = dict(theta=TH, rmax=RMAX, tau=TAU, convention="tan")


def _kw(**sys_over):
    from shepherd.agents.attacker_ladder import AttackerSpec
    from shepherd.env_sys import RewardSpec
    from shepherd.spawn_rand import SpawnSpec
    return dict(system=ratified_system(**sys_over),
                reward=RewardSpec(w_kill=0.5, enabled=True),
                attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0,
                                      route_gain=0.5, sense_range=30.0),
                spawn=SpawnSpec())


# --- E-A (최우선) ----------------------------------------------------------
def test_ea_default_bit_exact():
    """E-A — force-commit 계약 기본값에서 **동작 무변화**. 실패 시 즉시 중단."""
    assert SystemSpec().force_commit_step is None
    assert SystemSpec().perfect_aim_at_commit is False
    a, b = [], []
    ra = mission_eval(0, 12, limiter_mode="hold", records=a, **_kw())
    rb = mission_eval(0, 12, limiter_mode="hold", records=b,
                      **_kw(force_commit_step=None, perfect_aim_at_commit=False))
    assert json.dumps(ra, sort_keys=True) == json.dumps(rb, sort_keys=True)
    assert a == b


# --- E-B -------------------------------------------------------------------
def test_eb_seed_block_disjoint():
    """E-B — fresh seed 대역이 기존 캠페인과 미교차 (§32.2)."""
    used = [(0, 1598),        # 초기 캠페인 / curve_sweep 계열
            (10000, 10999),   # E2 계열
            (30000, 30299)]   # E4-1c
    lo, hi = EP0, EP0 + 299
    for a0, b0 in used:
        assert hi < a0 or lo > b0, f"seed 대역 [{lo},{hi}] 가 [{a0},{b0}] 와 교차"


# --- E-C -------------------------------------------------------------------
def test_ec_pass1_shared_and_deterministic():
    """E-C — Pass 1 이 arm 과 무관하고 재호출에 완전 동일 (4 arm 공유의 전제)."""
    for ep in (EP0, EP0 + 1, EP0 + 2):
        r1 = reference_pass(ep, TAU, RMAX)
        r2 = reference_pass(ep, TAU, RMAX)
        assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True), \
            f"ep{ep} Pass 1 이 결정론적이지 않다"
        # arm 선택은 같은 Pass 1 에서 target 만 달리 읽는다
        picks = {nm: _select_step(r1, tgt) for nm, tgt in ARMS}
        assert set(picks) == {nm for nm, _ in ARMS}


# --- E-D -------------------------------------------------------------------
def test_ed_exactly_one_forced_shot():
    """E-D — 강제 커밋이 에피소드당 **정확히 1 발**, 탄 미소모."""
    ep = None
    for cand in range(EP0, EP0 + 20):
        r = reference_pass(cand, TAU, RMAX)
        s = _select_step(r, 6.75)
        if s is not None and s > 2:
            ep, step = cand, s
            break
    assert ep is not None, "밴드 안 후보 에피소드를 찾지 못했다"

    st = _build(ep, force_step=step + 1, ideal=True, omega=None)   # 1-based 규약
    env, scn, lay = st.env, st.scn, st.lay
    d = _Driver(env, scn, lay, ep)
    d.fire_mode = "never"
    n_forced = 0
    for _ in range(int(lay.episode_len)):
        fi = d.step(limiter_mode="hold", baseline_commit=False)
        if fi.get("forced_commit"):
            n_forced += 1
        if d.done:
            break
    assert n_forced == 1, f"강제 커밋 {n_forced} 회 (정확히 1 이어야)"
    assert int(env.fsm.k) == 0, "탄이 소모되지 않았다"


# --- 동결 상수 (§32.1/32.2) 가 코드와 일치하는지 --------------------------
def test_frozen_law_constants_match_prereg():
    """사전등록에 적은 예측 a* 가 현행 config 에서 재현되는지 고정."""
    assert abs(RMAX / (1.0 + TAN) - 6.763546) < 1e-5
    expect = {"E-1": 26.32, "E-2": 32.30, "E-3": 22.67, "E-4": 7.11}
    for nm, tgt in ARMS:
        got = float(a_star(tgt, **KW))
        assert abs(got - expect[nm]) < 0.01, f"{nm}: {got:.4f} != {expect[nm]}"
    # 지배 제약 전환: 6.75 는 lateral, 7.20 은 far-edge
    assert 6.75 * TAN < RMAX - 6.75
    assert 7.20 * TAN > RMAX - 7.20
    # 판별 방향: 기존 lateral-only 는 증가, 보정 법칙은 감소
    assert 2 * (7.20 * TAN) / TAU ** 2 > 2 * (6.75 * TAN) / TAU ** 2      # old: 증가
    assert float(a_star(7.20, **KW)) < float(a_star(6.75, **KW))          # new: 감소
    # 마진 정의
    assert abs(float(margin(6.75, 10.0, **KW)) - (float(a_star(6.75, **KW)) - 10.0)) < 1e-9
    got = float(s_of_ax(7.90, theta=TH, rmax=RMAX, convention="tan"))
    assert got == pytest.approx(RMAX - 7.90)
    # far-edge 가 binding 인 arm 은 규약과 무관해야 한다 (정정 불변량)
    got = float(s_of_ax(7.90, theta=TH, rmax=RMAX, convention="inscribed"))
    assert got == pytest.approx(RMAX - 7.90)


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
