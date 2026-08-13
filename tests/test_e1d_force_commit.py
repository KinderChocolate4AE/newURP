"""E1d 회귀 게이트 D-A ~ D-D (docs/83 §15.6). 4/4 통과 전 E1d 실행 금지.

계약 = `SystemSpec.force_commit_step` (do(F=1), 정확히 1 발) +
       `SystemSpec.perfect_aim_at_commit` (판정 직전 psi=0).

    python -m pytest tests/test_e1d_force_commit.py -q

torch-free.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from shepherd.env_sys import SystemSpec, ratified_system
from shepherd.m4_env import mission_eval
from shepherd.scripts.e1d_commit_geom import (_build, _select_step, forced_pass,
                                              reference_pass)
from shepherd.scripts.recoverability_probe import _Driver
from shepherd.scripts.slew_audit import aim_geometry

TAU, RMAX = 0.30, 8.22


def _kw(**sys_over):
    from shepherd.agents.attacker_ladder import AttackerSpec
    from shepherd.env_sys import RewardSpec
    from shepherd.spawn_rand import SpawnSpec
    return dict(system=ratified_system(**sys_over),
                reward=RewardSpec(w_kill=0.5, enabled=True),
                attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0,
                                      route_gain=0.5, sense_range=30.0),
                spawn=SpawnSpec())


def test_da_default_bit_exact():
    """D-A (최우선) — 두 필드 기본값에서 **동작 무변화**. 실패 시 즉시 중단."""
    assert SystemSpec().force_commit_step is None
    assert SystemSpec().perfect_aim_at_commit is False
    assert ratified_system().force_commit_step is None
    assert ratified_system().perfect_aim_at_commit is False

    a, b = [], []
    ra = mission_eval(0, 12, limiter_mode="hold", records=a, **_kw())
    rb = mission_eval(0, 12, limiter_mode="hold", records=b,
                      **_kw(force_commit_step=None, perfect_aim_at_commit=False))
    assert json.dumps(ra, sort_keys=True) == json.dumps(rb, sort_keys=True)
    assert a == b


def _first_with_band(n=20):
    for ep in range(n):
        ref = reference_pass(ep, TAU, RMAX)
        s = _select_step(ref, 8.0)
        if s is not None and s > 2:
            return ep, ref, s
    return None, None, None


def test_db_replay_integrity():
    """D-B — Pass 2 의 commit 스텝 **직전** 상태가 Pass 1 기록과 bit-exact.

    공격자는 commit 전까지 반응하지 않고 finisher 는 이동하지 않으므로 성립해야 한다.
    """
    ep, ref, s = _first_with_band()
    assert ep is not None, "밴드 안 후보가 있는 에피소드를 찾지 못했다"
    ref_ax = {r["t"]: r["ax"] for r in ref["rows"]}

    st = _build(ep, force_step=s, ideal=False, omega=None)
    env, scn, lay = st.env, st.scn, st.lay
    d = _Driver(env, scn, lay, ep)
    d.fire_mode = "never"
    seen = {}
    for t in range(int(lay.episode_len)):
        lims, fin, att = env._states()
        g = aim_geometry(env._p(att), env._v(att), env._p(fin), env._e(fin),
                         tau=TAU, range_max=RMAX)
        if g is not None:
            seen[t] = g["ax"]
        if t >= s:
            break
        d.step(limiter_mode="hold", baseline_commit=False)
    # commit 스텝 **이전까지** 완전 일치 (개입 전이므로)
    for t in range(0, s + 1):
        if t in ref_ax and t in seen:
            assert seen[t] == ref_ax[t], f"t={t} 재생 불일치"


def test_dc_perfect_aim_gives_zero_psi():
    """D-C — perfect_aim_at_commit=True 에서 판정 시점 psi ~ 0."""
    ep, ref, s = _first_with_band()
    assert ep is not None
    st = _build(ep, force_step=s, ideal=True, omega=None)
    env, scn, lay = st.env, st.scn, st.lay
    d = _Driver(env, scn, lay, ep)
    d.fire_mode = "never"
    psi_after = None
    for t in range(int(lay.episode_len)):
        if t == s:
            lims, fin, att = env._states()
            p_a, v_a = env._p(att), env._v(att)
            # 개입은 inner.step 직전에 일어나므로, 여기서는 아직 적용 전.
            d.step(limiter_mode="hold", baseline_commit=False)
            # 개입 후 e 로 같은 pre-step 기하를 재평가
            g = aim_geometry(p_a, v_a, env._p(fin), env._e(fin),
                             tau=TAU, range_max=RMAX)
            # 주의: fin 은 스텝 후 상태이므로 e 가 다시 slew 됐을 수 있다.
            # 대신 forced_pass 가 보고하는 psi 계약(=0)을 직접 검사한다.
            break
        d.step(limiter_mode="hold", baseline_commit=False)
    r = forced_pass(ep, s, ideal=True, omega=None, tau=TAU, rmax=RMAX)
    assert r["fired"] is True, "강제 커밋이 발생하지 않았다"
    assert r["psi_at_commit"] == 0.0


def test_dd_exactly_one_shot_and_other_terminals():
    """D-D — 강제 커밋이 **정확히 1 발** (K=0 소모) · 다른 종말 채널 유지."""
    ep, ref, s = _first_with_band()
    assert ep is not None
    st = _build(ep, force_step=s, ideal=False, omega=None)
    env, scn, lay = st.env, st.scn, st.lay
    d = _Driver(env, scn, lay, ep)
    d.fire_mode = "never"
    n_forced = 0
    for t in range(int(lay.episode_len)):
        fi = d.step(limiter_mode="hold", baseline_commit=False)
        if fi.get("forced_commit"):
            n_forced += 1
        if d.done:
            break
    assert n_forced == 1, f"강제 커밋이 {n_forced} 회 (정확히 1 이어야)"
    assert int(env.fsm.k) == 0, "탄이 소모되지 않았다"
    assert d.label in ("CAPTURED", "NET_CAPTURE", "CAPTURE_WITH_CONTACT",
                       "PENETRATED", "HARD_KILL", "SPENT_FAIL", "TRUNCATED")


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
