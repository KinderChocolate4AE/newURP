"""P28: M4 운용점 선언의 무결성.

`m4_config()` 가 동결 계약과 **선언된 항목에서만** 다른지 강제한다.
누군가 조용히 오버라이드를 추가하면(특히 결과를 본 뒤) 여기서 걸린다.
"""
from __future__ import annotations

import pytest

from shepherd.params import as_config, check_frozen_yaml
from shepherd.m4_config import (M4_OVERRIDES, M4_PROVENANCE, PENDING, m4_config,
                                THREAT_BRACKET, CAPABILITY_RATIOS, SWEEP_AXES,
                                draw_threat, m4_episode_config, TAU_DECOMPOSITION)
from shepherd.train.make_env import make_train_env


def _get(cfg, dotted):
    cur = cfg
    for part in dotted.split("."):
        cur = cur[part]
    return cur


def test_p28_frozen_yaml_still_matches():
    """동결 YAML 과 registry 기본값이 여전히 일치 (오버라이드는 파일을 안 건드린다)."""
    check_frozen_yaml()


def test_p28b_only_declared_keys_differ():
    """M4 config 는 선언 목록 밖에서 동결 계약과 다르면 안 된다."""
    base, m4 = as_config(), m4_config()

    def walk(a, b, prefix=""):
        diffs = []
        for k in a:
            pa, pb = a[k], b[k]
            key = f"{prefix}{k}"
            if isinstance(pa, dict) and isinstance(pb, dict):
                diffs += walk(pa, pb, key + ".")
            elif pa != pb:
                diffs.append(key)
        return diffs

    assert sorted(walk(base, m4)) == sorted(M4_OVERRIDES), (
        "선언되지 않은 오버라이드가 있다 (또는 선언했는데 반영이 안 됐다)")


def test_p28c_every_override_has_provenance():
    """근거 없는 오버라이드 금지."""
    missing = [k for k in M4_OVERRIDES if not M4_PROVENANCE.get(k, "").strip()]
    assert not missing, f"근거 미기재: {missing}"
    for k, v in M4_PROVENANCE.items():
        assert k in M4_OVERRIDES, f"{k}: 근거만 있고 오버라이드에 없다"
        assert "202" in v, f"{k}: 근거에 날짜가 없다"


def test_p28d_declared_set_is_pinned():
    """2026-07-29 선언 묶음. 늘어나면 여기서 걸리고, 근거를 함께 쓰게 만든다."""
    assert set(M4_OVERRIDES) == {
        "train.episode_len", "physics.tau_deploy", "physics.kill_radius",
        "attitude.omega_max", "train.limits.limiter_omega", "train.layout.x_fire",
        "viability.cone.range_max", "viability.cone.half_angle",
        "physics.net_radius"}
    assert M4_OVERRIDES["train.episode_len"] == 160
    assert M4_OVERRIDES["physics.tau_deploy"] == 0.30
    assert not (set(PENDING) & set(M4_OVERRIDES)), "PENDING 과 선언이 겹친다"


def test_p29_tau_sits_on_the_dt_lattice():
    """★ A8: FSM 은 timer -= dt 로 감산하므로 tau 는 dt 의 정수배여야 한다.

    아니면 실효 지연이 ceil(tau/dt)*dt 로 올라가 선언값과 달라진다.
    """
    import math
    cfg = m4_config()
    tau, dt = cfg["physics"]["tau_deploy"], cfg["physics"]["dt"]
    n = tau / dt
    assert abs(n - round(n)) < 1e-9, f"tau={tau} 가 dt={dt} 격자 위에 없다 (n={n})"
    assert abs(round(n) * dt - tau) < 1e-12
    # tau_lock 도 마찬가지
    n2 = cfg["physics"]["tau_lock"] / dt
    assert abs(n2 - round(n2)) < 1e-9


def test_p29b_tau_equals_its_decomposition():
    """★ tau 는 선언된 분해의 합이어야 한다 -- 슬쩍 키우는 경로를 막는다."""
    total = sum(v[0] for v in TAU_DECOMPOSITION.values())
    assert abs(M4_OVERRIDES["physics.tau_deploy"] - total) < 1e-12, (
        f"tau {M4_OVERRIDES['physics.tau_deploy']} != 분해합 {total} -- "
        "값을 바꾸려면 분해 항을 바꾸고 근거를 써라")
    for name, (val, why) in TAU_DECOMPOSITION.items():
        assert val > 0 and why.strip(), f"{name}: 값 또는 근거 없음"


def test_p32_threat_bracket_straddles_proposition_N():
    """★ 위협 브래킷이 명제 N 의 경계를 가로질러야 한다.

    w = 0.5*a*tau^2 vs rho. 전 구간에서 w < rho 면 조향이 늘 불필요하고
    (게이트 실패), 전 구간에서 w > rho 면 늘 필요해서 regime 구분이 안 생긴다.
    **가로질러야** 정책이 위협에 따라 다르게 행동하는 것을 배울 수 있다.
    """
    cfg = m4_config()
    tau, rho = cfg["physics"]["tau_deploy"], cfg["physics"]["net_radius"]
    lo, hi = THREAT_BRACKET["physics.a_att_max"]
    w_lo, w_hi = 0.5 * lo * tau ** 2, 0.5 * hi * tau ** 2
    assert w_lo < rho < w_hi, (
        f"브래킷이 명제 N 경계를 안 가로지른다: w in [{w_lo:.2f}, {w_hi:.2f}], rho={rho}")
    a_star = 2 * rho / tau ** 2
    assert lo < a_star < hi
    print(f"\n[P32] 명제 N 경계 a* = {a_star:.1f} m/s^2, 브래킷 [{lo:g}, {hi:g}] 가 가로지름")


def test_p30_threat_bracket_and_ratios():
    """위협은 브래킷에서 뽑히고, 방어자 능력은 비율로 따라온다."""
    for ep in range(200):
        d = draw_threat(0, ep)
        for k, (lo, hi) in THREAT_BRACKET.items():
            assert lo - 1e-9 <= d[k] <= hi + 1e-9, f"{k} 브래킷 이탈"
        for k, (src, ratio) in CAPABILITY_RATIOS.items():
            assert abs(d[k] - d[src] * ratio) < 1e-9, f"{k} 비율 위반"
    assert draw_threat(0, 3) == draw_threat(0, 3)          # 결정론
    assert draw_threat(0, 3) != draw_threat(1, 3)          # seed 분리


def test_p30b_defender_is_inferior_every_episode():
    """★ 능력 비대칭이 모든 에피소드에서 유지된다 (Pliska: 속도 대등, 가속 열세)."""
    for ep in range(100):
        c = m4_episode_config(7, ep)
        assert c["physics"]["a_lim_max"] < c["physics"]["a_att_max"]
        assert c["train"]["limits"]["limiter_v_max"] <= c["physics"]["att_speed"] + 1e-9
        assert c["attitude"]["omega_max"] <= c["train"]["limits"]["adversary_omega"]


def test_p31_cone_is_consistent_with_tau():
    """★ 콘의 축방향 밴드와 tau 가 정합해야 한다.

    포획은 tau 시점에 판정된다. 그때 네트가 실제로 간 거리보다 먼 곳을 콘이
    '포획 가능'으로 판정하면, 네트가 닿을 수 없는 표적을 잡았다고 세게 된다.
    적형성 게이트에서 실제로 그렇게 됐다 (hold/ring/intercept 전부 24/24 NET_CAPTURE).
    """
    import math
    cfg = m4_config()
    rmax = cfg["viability"]["cone"]["range_max"]
    ha = cfg["viability"]["cone"]["half_angle"]
    r_net = cfg["physics"]["net_radius"]
    tau = cfg["physics"]["tau_deploy"]

    # (1) half_angle 은 range_max 의 도출값이어야 한다 (params.py 정의)
    assert abs(ha - math.atan(r_net / rmax)) < 1e-3, "half_angle 이 range_max 와 어긋난다"

    # (2) range_max 는 **tau_flight** 동안의 네트 병진과 같아야 한다.
    #     sense/decide 지연은 발사 전에 일어나므로 네트 병진에 안 들어간다.
    NET_TRAVEL_AT_FLIGHT = 8.22       # prototypes/net_forward, (45deg, 60 m/s, 35 g)
    assert r_net < 2.0, "A3: 최악방향 반경이 등가면적 반경보다 작아야 한다"
    assert abs(rmax - NET_TRAVEL_AT_FLIGHT) < 0.5, (
        f"range_max {rmax} != tau_flight 병진 {NET_TRAVEL_AT_FLIGHT} -- "
        "네트가 닿을 수 없는 볼륨을 판정하게 된다")
    assert tau > TAU_DECOMPOSITION["tau_flight"][0], "tau_total 은 비행시간보다 커야"

    # (3) 명제 N 경계 관련 검사는 P32 로 분리 (브래킷이 경계를 가로지르는지)


def test_p30c_episode_config_builds():
    """랜덤화된 config 로 env 가 실제로 조립된다."""
    for ep in (0, 5, 11):
        env, scn, lay = make_train_env(m4_episode_config(0, ep))
        assert lay.episode_len == 160
        assert scn.limiter.a_max < scn.adversary.a_att_max


def test_p28e_env_actually_uses_it():
    """조립까지 실제로 전달되는지 (선언만 하고 안 쓰이는 사고 방지)."""
    env, scn, lay = make_train_env(m4_config())
    assert lay.episode_len == 160
    base_env, _, base_lay = make_train_env(as_config())
    assert base_lay.episode_len == 80          # 동결 계약은 그대로


def test_p28f_extra_is_not_a_declaration():
    """extra 로 넘긴 값은 선언 목록을 오염시키지 않는다."""
    before = dict(M4_OVERRIDES)
    cfg = m4_config({"physics.tau_deploy": 0.25})
    assert _get(cfg, "physics.tau_deploy") == 0.25
    assert M4_OVERRIDES == before
    assert _get(m4_config(), "physics.tau_deploy") == M4_OVERRIDES["physics.tau_deploy"]
    assert _get(as_config(), "physics.tau_deploy") == 0.4      # 동결 계약은 그대로


# ---------------------------------------------------------------- P38 sweep 축 --
def test_p38_sweep_axes_are_well_formed():
    """선언된 sweep 축: 기본값이 축 안에 있고, config 축은 실제 config 키다."""
    cfg = m4_config()
    for key, ax in SWEEP_AXES.items():
        assert set(ax) >= {"target", "default", "values", "why"}, key
        assert len(ax["values"]) >= 2, f"{key}: 축이 점 하나면 sweep 이 아니다"
        assert ax["default"] in ax["values"], f"{key}: 기본값이 축 위에 없다"
        assert len(ax["why"]) >= 40, f"{key}: 축을 둔 이유가 비어 있다"
        if ax["target"] == "config":
            assert _get(cfg, key) == ax["default"], f"{key}: 기본값이 운용점과 불일치"


def test_p38b_swept_config_keys_are_declared():
    """config 를 겨냥한 sweep 축은 선언(M4_OVERRIDES)된 항목이어야 한다.

    선언되지 않은 파라미터를 결과를 본 뒤 축으로 승격시키는 경로를 막는다.
    """
    for key, ax in SWEEP_AXES.items():
        if ax["target"] != "config":
            continue
        assert key in M4_OVERRIDES, f"{key}: 선언되지 않은 항목은 축이 될 수 없다"
        assert key in M4_PROVENANCE, f"{key}: 근거 없는 항목은 축이 될 수 없다"
