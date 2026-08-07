"""P85/P86 — 스케일 계약 v2 (docs/59 §3).

  P85  overlay 미적용 -> 기본 config 가 legacy 값 그대로 (비트)      강제
  P86  v2 스모크: 300 m 스폰이 실제로 비행·정상 종료·A2 조향 정상    강제
"""
from __future__ import annotations

import numpy as np

from shepherd.params import as_config
from shepherd.scale_v2 import SCALE_V2_CFG, SCALE_V2_SPAWN


def test_p85_default_config_unchanged():
    cfg = as_config()
    assert cfg["train"]["episode_len"] == 80
    assert float(cfg["train"]["layout"]["adversary_start_x"]) == 24.0
    assert tuple(cfg["train"]["layout"]["ring_center"]) == (8.0, 0.0, 0.0)
    # overlay 는 명시 전달로만 작동한다
    cfg2 = as_config(dict(SCALE_V2_CFG))
    assert cfg2["train"]["episode_len"] == 480
    assert float(cfg2["train"]["layout"]["adversary_start_x"]) == 300.0


def test_p86_v2_smoke():
    """300 m 스폰 1판: 실비행·정상 종료. (~20-30 s 소요, full env)"""
    from shepherd.agents.attacker_ladder import AttackerSpec
    from shepherd.env_sys import RewardSpec, SystemSpec
    from shepherd.m4_env import build_m4_env
    from shepherd.scripts.mission_rollout import LABELS, run_episode

    st = build_m4_env(
        0, 0,
        system=SystemSpec(enabled=True, contact_resolver=True,
                          miss_terminates=False, p_kill=1.0),
        reward=RewardSpec(w_kill=0.5, enabled=True),
        attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
        spawn=SCALE_V2_SPAWN, extra_cfg=dict(SCALE_V2_CFG))
    env, scn, lay = st.env, st.scn, st.lay
    assert int(lay.episode_len) == 480
    env.reset(seed=0)
    p0 = env._p(env._states()[2])
    d0 = float(np.linalg.norm(p0 - np.asarray(lay.target, float)))
    assert d0 > 250.0, f"스폰이 가깝다: {d0:.1f} m"
    r = run_episode(env, scn, lay, seed=0, limiter_mode="hold", fire_mode="clean")
    assert r.label in LABELS, r.label
    # 300 m 비행에는 물리적 하한 시간이 있다 (cone 도달 ~270 m / v_max)
    assert r.steps >= 150, f"비정상 조기 종료: {r.steps} 스텝, {r.label}"
    assert r.min_target_dist < 50.0, \
        f"공격자가 접근하지 않았다: min_d={r.min_target_dist:.1f}"
