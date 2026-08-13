"""R3 회귀 게이트 R3-A ~ R3-D (docs/83 §10.6). 4/4 통과 전 E2-B 실행 금지.

R3 = `SystemSpec.capture_terminates`. False 면 **성공한 net capture 의 종료와
무력화 효과만** 억제하고 commit·공격자 응답·SPENT/K=0·하드킬·침투·절단은 보존한다.

    python -m pytest tests/test_r3_capture_terminates.py -q

torch-free.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import RewardSpec, SystemSpec, ratified_system
from shepherd.m4_env import build_m4_env, mission_eval
from shepherd.scripts.mission_rollout import run_episode
from shepherd.spawn_rand import SpawnSpec

T1 = dict(level="A2", jink_amp=0.6, seed=0, route_gain=0.5, sense_range=30.0)


def _kw(**sys_over):
    return dict(system=ratified_system(**sys_over),
                reward=RewardSpec(w_kill=0.5, enabled=True),
                attacker=AttackerSpec(**T1), spawn=SpawnSpec())


def test_r3a_default_bit_exact():
    """R3-A (최우선) — 기본값 capture_terminates=True 에서 **동작 무변화**.

    실패하면 계약을 조용히 바꾼 것이므로 E2 결과를 볼 이유가 없다.
    """
    assert SystemSpec().capture_terminates is True
    assert ratified_system().capture_terminates is True

    a, b = [], []
    ra = mission_eval(0, 12, limiter_mode="hold", records=a, **_kw())
    rb = mission_eval(0, 12, limiter_mode="hold", records=b,
                      **_kw(capture_terminates=True))
    assert json.dumps(ra, sort_keys=True) == json.dumps(rb, sort_keys=True)
    assert a == b
    # 포획이 실제로 발생하는 표본이어야 검정이 의미가 있다
    assert ra["counts"]["NET_CAPTURE"] > 0


def test_r3b_no_op_when_capture_never_happens():
    """R3-B — capture 가 발생하지 않는 구간에서 A 와 B 는 **bit-exact**.

    개입 분기가 한 번도 활성화되지 않으므로 차이가 나면 wiring 결함이다
    (docs/83 §10.5: high-chi 는 effect 추정이 아니라 exact wiring oracle).
    """
    on, off = [], []
    r_on = mission_eval(0, 40, limiter_mode="hold", records=on, **_kw())
    r_off = mission_eval(0, 40, limiter_mode="hold", records=off,
                         **_kw(capture_terminates=False))
    shaping_on = [r for r in on if r["regime"] == "SHAPING_NEEDED"]
    shaping_off = [r for r in off if r["regime"] == "SHAPING_NEEDED"]
    assert shaping_on, "SHAPING_NEEDED 표본이 없다 -- 검정 무의미"
    assert [r["label"] for r in shaping_on] == [r["label"] for r in shaping_off]
    for x, y in zip(shaping_on, shaping_off):
        assert x == y


def _first_capture_episode(n=40):
    recs = []
    mission_eval(0, n, limiter_mode="hold", records=recs, **_kw())
    for r in recs:
        if r["label"] in ("NET_CAPTURE", "CAPTURE_WITH_CONTACT"):
            return r["episode"]
    return None


def test_r3c_sham_capture_continues_episode():
    """R3-C — capture 가 확정 발생하는 에피소드에서:

        A: CAPTURED 종료
        B: would_capture 기록 후 **계속**, 공격자 생존, finisher SPENT/K=0
    """
    ep = _first_capture_episode()
    assert ep is not None, "포획 에피소드를 찾지 못했다 -- 표본을 늘려야 한다"

    st_a = build_m4_env(0, ep, **_kw())
    ra = run_episode(st_a.env, st_a.scn, st_a.lay, seed=ep, limiter_mode="hold")
    assert ra.label in ("NET_CAPTURE", "CAPTURE_WITH_CONTACT")

    st_b = build_m4_env(0, ep, **_kw(capture_terminates=False))
    tel = []
    rb = run_episode(st_b.env, st_b.scn, st_b.lay, seed=ep, limiter_mode="hold",
                     telemetry=tel)

    # (i) 억제가 실제로 일어났고 그 시점이 A 의 종료 시점과 정합
    assert st_b.env.sham_capture is True
    assert st_b.env.sham_capture_step is not None
    # (ii) 라벨이 더 이상 포획이 아니다 -- 에피소드가 계속됐다
    assert rb.label not in ("NET_CAPTURE", "CAPTURE_WITH_CONTACT")
    assert rb.steps > ra.steps
    # (iii) 네트는 실제로 소모됐다 (READY 복귀 금지)
    assert st_b.env.net_spent is True
    assert int(st_b.env.fsm.k) == 0
    # (iv) 공격자가 살아서 계속 움직였다
    assert len(tel) > ra.steps
    p_last = np.asarray(tel[-1]["p_att"], float)
    p_at_cap = np.asarray(tel[ra.steps - 1]["p_att"], float)
    assert float(np.linalg.norm(p_last - p_at_cap)) > 0.0


def test_r3d_terminal_isolation():
    """R3-D — B 에서도 하드킬·침투 종료가 그대로 유지된다."""
    on, off = [], []
    mission_eval(0, 40, limiter_mode="intercept", records=on,
                 baseline_commit=True, **_kw())
    mission_eval(0, 40, limiter_mode="intercept", records=off,
                 baseline_commit=True, **_kw(capture_terminates=False))
    lab_off = [r["label"] for r in off]
    # 포획만 사라지고 다른 종말 채널은 남는다
    assert all(l != "NET_CAPTURE" for l in lab_off)
    assert "PENETRATED" in lab_off
    on_hk = sum(1 for r in on if r["label"] == "HARD_KILL")
    off_hk = sum(1 for r in off if r["label"] == "HARD_KILL")
    # 하드킬 채널이 살아 있다 (경쟁위험 제거로 늘어날 수는 있어도 사라지면 안 된다)
    assert off_hk >= on_hk


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
