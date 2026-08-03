"""P39: limiter 두 채널 분리 계측의 무결성 (docs/46).

분리의 근거는 **공통난수(CRN)** 하나다: 같은 상태에서 `limiters=L` 과 `limiters=None`
을 **같은 seed** 로 부르면 가속 표본이 동일하므로, 두 v_shot 의 차이는
`_feasible_limiter` 의 기여 그것 하나다. 이 파일은 그 전제를 강제한다.

CRN 이 깨지면 채널 (i) 의 측정치가 표본잡음이 되고, 그러면 docs/46 의 결론
("유리한 채널은 선언 반경에서 수치적으로 0") 이 근거를 잃는다.
"""
from __future__ import annotations

import numpy as np

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import RewardSpec, SystemSpec
from shepherd.m4_config import m4_config
from shepherd.m4_env import build_m4_env
from shepherd.scripts.channel_split import split_episode, summarize_split
from shepherd.spawn_rand import SpawnSpec


def _stack(ep=0):
    return build_m4_env(1234, ep, system=SystemSpec(), reward=RewardSpec(),
                        attacker=AttackerSpec(), spawn=SpawnSpec())


def test_p39_free_call_has_no_limiter_cut():
    """`limiters=None` 호출은 정의상 아무 방향도 자르지 않는다 (p_feasible == 1)."""
    st = _stack()
    st.env.reset(seed=1234)
    lims, fin, att = st.env._states()
    p, v = st.env._p(att), st.env._v(att)
    free = st.env._vshot(p, v, None, fin, seed=7)
    assert free.p_feasible == 1.0
    assert free.boxed_in is False


def test_p39b_same_seed_is_bit_identical():
    """CRN: 같은 상태 · 같은 seed 는 비트 동일. (채널 분리의 전제)"""
    st = _stack()
    st.env.reset(seed=1234)
    lims, fin, att = st.env._states()
    p, v = st.env._p(att), st.env._v(att)
    L = [st.env._p(s) for s in lims]
    a1, a2 = st.env._vshot(p, v, L, fin, seed=11), st.env._vshot(p, v, L, fin, seed=11)
    assert a1.v_shot_soft == a2.v_shot_soft
    assert a1.p_feasible == a2.p_feasible


def test_p39c_cut_is_monotone_in_limiters():
    """limiter 를 주면 가용 방향이 줄기만 한다 (p_feasible 단조 감소)."""
    st = _stack()
    st.env.reset(seed=1234)
    for _ in range(4):
        lims, fin, att = st.env._states()
        p, v = st.env._p(att), st.env._v(att)
        L = [st.env._p(s) for s in lims]
        with_L = st.env._vshot(p, v, L, fin, seed=3)
        free = st.env._vshot(p, v, None, fin, seed=3)
        assert with_L.p_feasible <= free.p_feasible + 1e-12
        acts = {a: np.zeros(sp.shape, np.float32)
                for a, sp in ((k, st.env.action_space(k)) for k in st.env.agents)}
        st.env.step(acts)


def test_p39d_split_episode_records_both_channels():
    """계측이 두 채널의 원자료를 실제로 남긴다 (선언만 하고 안 재는 사고 방지)."""
    cfg = m4_config()
    st = _stack()
    rows = split_episode(st.env, st.scn, st.lay, seed=1234, limiter_mode="ring",
                         tau=float(cfg["physics"]["tau_deploy"]),
                         range_max=float(cfg["viability"]["cone"]["range_max"]),
                         max_steps=12)
    assert rows, "밴드 진입 전에 끝나면 계측이 성립하지 않는다"
    keys = set(rows[0])
    assert {"vs_with", "vs_free", "p_feas"} <= keys      # 채널 (i)
    assert {"psi", "omega_req", "v_perp"} <= keys        # 채널 (ii)
    assert all(0.0 <= r["p_feas"] <= 1.0 for r in rows)
    assert all(0.0 <= r["psi"] <= np.pi + 1e-9 for r in rows)


def test_p39e_summary_reports_both_channels():
    """요약이 두 채널을 **따로** 낸다 -- 하나로 합치면 분리의 의미가 사라진다."""
    cfg = m4_config()
    per_mode = {}
    for mode in ("hold", "ring"):
        st = _stack()
        per_mode[mode] = [split_episode(
            st.env, st.scn, st.lay, seed=1234, limiter_mode=mode,
            tau=float(cfg["physics"]["tau_deploy"]),
            range_max=float(cfg["viability"]["cone"]["range_max"]), max_steps=40)]
    s = summarize_split({"per_mode": per_mode, "regimes": [], "episodes": 1},
                        omega_max=float(cfg["attitude"]["omega_max"]))
    for mode in ("hold", "ring"):
        if s[mode].get("n_steps_in_band"):
            assert any(k.startswith("ch_i_") for k in s[mode])
            assert any(k.startswith("ch_ii_") for k in s[mode])
