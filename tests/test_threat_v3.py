"""위협 계약 v3 배선 테스트 (docs/60 §5).

  P87   NESTING: v3 필드 전부 기본값 -> 배선 전 커밋과 bit 동일
        (golden = tests/golden/p87_prewiring.json, 배선 전 코드에서 1회 생성)
  단위  angular-gap 거동 정의 (docs/60 §3.2) · 속도 프로파일 (§2) ·
        standby (§4.2) · v3 spawn (§4.2)

P88(방향성 manipulation gate)·P90·P91 은 env-level gate 스크립트가 별도 수행.
여기의 mirror/sense 단위 검증은 그 kinematic core 다. torch-free.
"""
from __future__ import annotations

import json
import math
import pathlib

import numpy as np
import pytest

from shepherd.agents.attacker_ladder import (AttackerSpec, _general_action,
                                             _route_accel, is_a1_equivalent)
from shepherd.scale_v2 import (A2_V4, THREAT_V3_NOMINAL, THREAT_V3_SPAWN,
                               THREAT_V3_STANDBY, V3_ARMS)
from shepherd.spawn_rand import StandbySpec, sample_spawn

GOLDEN = pathlib.Path(__file__).parent / "golden" / "p87_prewiring.json"

FWD = np.array([-1.0, 0.0, 0.0])          # 표적(원점) 방향 진행
# _route_accel 의 횡단면 기저 (fwd=[-1,0,0] 일 때): u=[0,1,0], w=[0,0,-1]
ROUTE_KW = dict(kill_radius=0.75, repel_margin=1.0, a_lat_max=30.0, d_target=50.0)
V3_ROUTE = AttackerSpec(level="A2", route_gain=0.5, sense_range=30.0)


# ------------------------------------------------------------------ P87 ---
def test_p87_attacker_bit_identical_to_prewiring_golden():
    """v3 필드 기본값(A2_V4)의 general 경로 출력 == 배선 전 golden (bit)."""
    import make_golden_p87 as g
    ref = json.loads(GOLDEN.read_text(encoding="utf-8"))
    got = g.attacker_grid()
    assert len(got) == len(ref["attacker"])
    for i, (a, b) in enumerate(zip(got, ref["attacker"])):
        assert a["a"] == b["a"], f"row {i}: accel 불일치"
        assert a["e"] == b["e"], f"row {i}: e_cmd 불일치"


def test_p87_spawn_bit_identical_to_prewiring_golden():
    """SCALE_V2_SPAWN (r_range/azimuth off) draw == 배선 전 golden (bit)."""
    import make_golden_p87 as g
    ref = json.loads(GOLDEN.read_text(encoding="utf-8"))
    got = g.spawn_grid()
    for i, (a, b) in enumerate(zip(got, ref["spawn"])):
        assert a == b, f"ep {i}: spawn draw 불일치"


def test_p87_nesting_flags():
    assert is_a1_equivalent(AttackerSpec())                      # v3 기본 off
    assert not is_a1_equivalent(AttackerSpec(sprint_range=60.0))
    assert not is_a1_equivalent(AttackerSpec(slowdown_range=(90.0, 60.0)))
    assert not is_a1_equivalent(THREAT_V3_NOMINAL)


# ---------------------------------------------------- angular-gap (§3.2) ---
def _route(spec, p_att, limiters, v_att=(0.0, 0.0, 0.0), **over):
    kw = dict(ROUTE_KW, **over)
    return _route_accel(spec, p_att=np.asarray(p_att, float),
                        v_att=np.asarray(v_att, float), fwd=FWD.copy(),
                        limiters=np.asarray(limiters, float), **kw)


def test_gap_single_limiter_steers_away():
    """+y 쪽 limiter -> 최대 free arc 중점은 -y (반대 방향)."""
    a = _route(V3_ROUTE, [50.0, 0.0, 0.0], [[45.0, 2.0, 0.0]])
    assert a[1] < 0.0, f"+y limiter 인데 -y 회피가 아님: {a}"
    assert abs(float(np.linalg.norm(a)) - 0.5 * 30.0) < 1e-9   # route_gain*a_lat_max


def test_gap_mirror_flips_sign():
    """P88-a kinematic core: 좌우 mirror 배치 -> 횡 반응 부호 반전."""
    lims = [[45.0, 2.0, 0.0], [40.0, 5.0, 1.0]]
    mirr = [[x, -y, z] for x, y, z in lims]
    a = _route(V3_ROUTE, [50.0, 0.0, 0.0], lims)
    b = _route(V3_ROUTE, [50.0, 0.0, 0.0], mirr)
    assert a[1] * b[1] < 0.0, f"mirror 인데 부호 유지: {a[1]} vs {b[1]}"
    assert abs(a[1] + b[1]) < 1e-9 and abs(a[2] - b[2]) < 1e-9   # 정확한 mirror 대칭


def test_gap_sense_range_gates_detection():
    """P88-d kinematic core: sense_range 밖 limiter 는 기여 0."""
    spec_blind = AttackerSpec(level="A2", route_gain=0.5, sense_range=3.0)
    a = _route(spec_blind, [50.0, 0.0, 0.0], [[45.0, 2.0, 0.0]])   # 거리 5.4 > 3
    assert np.array_equal(a, np.zeros(3))


def test_gap_full_blockage_yields_zero():
    """전 원주 봉쇄 (r_block 안 8기 포위) -> 기여 0 (repel 만 남음)."""
    p = np.array([50.0, 0.0, 0.0])
    lims = []
    for k in range(8):
        ang = 2.0 * math.pi * k / 8.0
        # 횡단면 기저 u=[0,1,0], w=[0,0,-1] 위 반경 0.5 (< r_block 0.75) + 전방 1
        lims.append(p + FWD * 1.0
                    + 0.5 * (math.cos(ang) * np.array([0.0, 1.0, 0.0])
                             + math.sin(ang) * np.array([0.0, 0.0, -1.0])))
    a = _route(V3_ROUTE, p, lims)
    assert np.array_equal(a, np.zeros(3))


def test_gap_terminal_gate_and_off_switch():
    a = _route(V3_ROUTE, [50.0, 0.0, 0.0], [[45.0, 2.0, 0.0]], d_target=2.0)
    assert np.array_equal(a, np.zeros(3))                 # jink_terminal_r=3 안
    off = AttackerSpec(level="A2", route_gain=0.0)
    b = _route(off, [50.0, 0.0, 0.0], [[45.0, 2.0, 0.0]])
    assert np.array_equal(b, np.zeros(3))


def test_gap_coplanar_tie_prefers_world_plus_z():
    """P91b 1차 FAIL 교정 (docs/60 §4.3): 공면 퇴화에서 ±z free arc 동률
    -> 세계 +z 선호 (y-mirror·z-회전 공변 tie-break)."""
    lims = [[45.0, 2.0, 0.0], [45.0, -2.0, 0.0]]          # 평면 양쪽 봉쇄
    a = _route(V3_ROUTE, [50.0, 0.0, 0.0], lims)
    assert a[2] > 0.0, f"공면 동률인데 +z 가 아님: {a}"
    mirr = [[x, -y, z] for x, y, z in lims]
    b = _route(V3_ROUTE, [50.0, 0.0, 0.0], mirr)
    assert np.allclose(a, b, atol=1e-9)                   # y-대칭 입력 -> 동일 +z


def test_gap_deterministic():
    args = ([50.0, 0.0, 0.0], [[45.0, 2.0, 0.0], [42.0, -1.0, 2.0]])
    a = _route(V3_ROUTE, *args)
    b = _route(V3_ROUTE, *args)
    assert np.array_equal(a, b)


# ------------------------------------------------- 속도 프로파일 (§2) ---
def _act(spec, p, v, v_max=30.0):
    return _general_action(
        spec, np.asarray(p, float), np.asarray(v, float),
        target=np.zeros(3), net_center=np.zeros(3),
        finisher_p=np.array([2.0, 0.0, 0.0]), limiters=None,
        kill_radius=0.75, a_att_max=30.0, omega_att_max=8.0,
        v_nominal=20.0, dt=0.05, committed=False, repel_margin=1.0,
        v_max=v_max)["a"]


SPEED = AttackerSpec(level="A2", sprint_range=60.0,
                     slowdown_range=(90.0, 60.0), slowdown_frac=0.5)


def test_speed_profile_sprint_zone_accelerates():
    """d=50 <= 60: v_ref = 1.0*v_max=30 > 현 20 -> 전진 가속 (fwd 방향)."""
    a = _act(SPEED, [50.0, 0.0, 0.0], [-20.0, 0.0, 0.0])
    assert a[0] < 0.0, f"sprint 구간인데 가속 없음: {a}"
    assert abs(float(np.linalg.norm(a)) - 30.0) < 1e-9    # 4*(30-20)=40 -> clip 30


def test_speed_profile_slowdown_zone_decelerates():
    """d=80 in (60, 90]: v_ref = 0.5*20 = 10 < 현 20 -> 감속 (역방향)."""
    a = _act(SPEED, [80.0, 0.0, 0.0], [-20.0, 0.0, 0.0])
    assert a[0] > 0.0, f"slowdown 구간인데 감속 없음: {a}"


def test_speed_profile_outside_zones_is_cruise():
    """d=200: v_ref = v_nominal, 정속이면 전진항 0 (A1 동일)."""
    a = _act(SPEED, [200.0, 0.0, 0.0], [-20.0, 0.0, 0.0])
    assert np.allclose(a, 0.0, atol=1e-9)


def test_speed_profile_v_max_none_falls_back_to_nominal():
    """능력 미전달 시 sprint 는 v_nominal 상한 -> 능력 초과 불가 (P89 방어선)."""
    a = _act(SPEED, [50.0, 0.0, 0.0], [-20.0, 0.0, 0.0], v_max=None)
    assert np.allclose(a, 0.0, atol=1e-9)                 # v_ref = 20 = 현 속도


# ------------------------------------------------------ standby (§4.2) ---
def _v3_stack(standby, ep=0):
    from shepherd.env_sys import RewardSpec, SystemSpec
    from shepherd.m4_env import build_m4_env
    arm = V3_ARMS["V3-FULL"]
    return build_m4_env(
        0, ep,
        system=SystemSpec(enabled=True, contact_resolver=True,
                          miss_terminates=False, p_kill=1.0),
        reward=RewardSpec(w_kill=0.5, enabled=True),
        attacker=arm["attacker"], spawn=arm["spawn"], standby=standby,
        extra_cfg=dict(arm["cfg"]))


def test_standby_symmetric_ring_around_target():
    st = _v3_stack(THREAT_V3_STANDBY, ep=3)
    inner = st.env.env if hasattr(st.env, "env") else st.env
    tgt = np.asarray(st.lay.target, float)
    angs = []
    for lid, p0_lay in zip(inner.limiter_ids, inner.layout.limiter_p0):
        p0 = np.asarray(inner.backend.by_name(lid).p0, float)
        assert np.allclose(p0, p0_lay)                    # layout(COMA cf) 동기화
        rel = p0 - tgt
        assert abs(float(np.linalg.norm(rel)) - 12.0) < 1e-9
        assert abs(rel[2]) < 1e-12                        # 수평면
        angs.append(math.atan2(rel[1], rel[0]) % (2.0 * math.pi))
    angs = sorted(angs)
    gaps = np.diff(angs + [angs[0] + 2.0 * math.pi])
    assert np.allclose(gaps, math.pi / 2.0, atol=1e-9)    # 4방위 대칭
    # phi0 in [0, pi/2) (대칭 몫, r3)
    assert 0.0 <= min(angs) < math.pi / 2.0


def test_standby_deterministic_and_episode_varying():
    a = _v3_stack(THREAT_V3_STANDBY, ep=5)
    b = _v3_stack(THREAT_V3_STANDBY, ep=5)
    c = _v3_stack(THREAT_V3_STANDBY, ep=6)
    ia, ib, ic = (s.env.env if hasattr(s.env, "env") else s.env for s in (a, b, c))
    assert np.allclose(ia.layout.limiter_p0, ib.layout.limiter_p0)
    assert not np.allclose(ia.layout.limiter_p0, ic.layout.limiter_p0)


def test_standby_none_keeps_legacy_ring():
    """standby=None -> 기존 ring 배치 그대로 (P87 경로)."""
    st = _v3_stack(None)
    inner = st.env.env if hasattr(st.env, "env") else st.env
    ring_c = np.array([50.0, 0.0, 0.0])
    for p0 in inner.layout.limiter_p0:
        assert abs(float(np.linalg.norm(np.asarray(p0, float) - ring_c)) - 5.0) < 1e-6


def test_standby_disabled_spec_is_noop():
    st = _v3_stack(StandbySpec(enabled=False))
    inner = st.env.env if hasattr(st.env, "env") else st.env
    ring_c = np.array([50.0, 0.0, 0.0])
    for p0 in inner.layout.limiter_p0:
        assert abs(float(np.linalg.norm(np.asarray(p0, float) - ring_c)) - 5.0) < 1e-6


# ------------------------------------------------------ v3 spawn (§4.2) ---
def test_v3_spawn_bracket_and_sector():
    for ep in range(30):
        d = sample_spawn(THREAT_V3_SPAWN, base_p=[300.0, 0.0, 0.0],
                         target=[0.0, 0.0, 0.0], speed=20.0, seed=0, episode=ep)
        p = np.asarray(d.p, float)
        r = float(np.linalg.norm(p))
        az = math.atan2(p[1], p[0])
        # r_lat=5 횡오프셋 여유 포함
        assert 245.0 <= r <= 355.0, f"ep{ep}: r={r}"
        assert abs(az) <= math.pi / 4 + 0.03, f"ep{ep}: az={az}"
        v = np.asarray(d.v, float)
        assert float(v @ (-p)) > 0.0                      # 표적 방향 조준
