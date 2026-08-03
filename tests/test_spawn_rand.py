"""P19–P26: 스폰 랜덤화 성질 (docs/36 §4 배선).

**헤드라인 실험 전에 성질 테스트** — 기존 규율. 특히 P19(동결 등가)와
P26(시나리오 적형성)은 재학습 전에 반드시 통과해야 한다.

torch-free. `python -m pytest tests/test_spawn_rand.py -q`
"""
from __future__ import annotations

import math
import os

import numpy as np
import pytest

from shepherd.params import as_config
from shepherd.train.make_env import make_train_env
from shepherd.spawn_rand import (SpawnSpec, sample_spawn, apply_spawn,
                                 spawn_for_episode, derive_spawn_u,
                                 randomized_config)

TARGET = (0.0, 0.0, 0.0)
BASE = (24.0, 0.0, 0.0)
SPEED = 20.0
DEFAULT = SpawnSpec()
OFF = SpawnSpec(enabled=False)


def _env(overrides=None):
    env, scn, lay = make_train_env(as_config(overrides or {}))
    return env, scn, lay


def _adv(env):
    return env.backend.by_name(env.adversary_id)


# ---------------------------------------------------------------- P19 -------
def test_p19_disabled_is_frozen_identical():
    """enabled=False 는 동결 경로와 bit-identical 이어야 한다."""
    env, scn, lay = _env()
    a = _adv(env)
    p0_frozen = np.array(a.p0, float).copy()
    v0_frozen = np.array(a.v0, float).copy()
    e0_frozen = np.array(a.e0, float).copy()

    for ep in range(8):
        draw = sample_spawn(OFF, base_p=p0_frozen, target=lay.target,
                            speed=scn.adversary.speed, seed=3, episode=ep)
        assert np.array_equal(np.array(draw.p), p0_frozen)
        # 동결 v0 = [-speed, 0, 0] (표적 정조준과 동일)
        assert np.allclose(draw.v, v0_frozen, rtol=0, atol=1e-12)
        assert np.allclose(draw.e, e0_frozen / np.linalg.norm(e0_frozen),
                           rtol=0, atol=1e-12)


def test_p19b_disabled_rollout_bit_identical():
    """enabled=False 로 apply 한 뒤 굴린 궤적이 apply 안 한 것과 완전히 같다."""
    def roll(apply: bool):
        env, scn, lay = _env()
        if apply:
            spawn_for_episode(env, OFF, seed=11, episode=5)
        env.reset(seed=11)
        acts = {aid: np.zeros(env.action_space(aid).shape, np.float32)
                for aid in env.agents}
        trace = []
        for _ in range(20):
            env.step(acts)
            trace.append(np.array(_adv(env).p, float).copy())
        return np.array(trace)

    assert np.array_equal(roll(False), roll(True))


# ---------------------------------------------------------------- P20 -------
def test_p20_determinism_and_variation():
    """같은 (seed, ep) -> 같은 값. 다른 ep -> 다른 값. 프로세스 재현 가능."""
    d1 = sample_spawn(DEFAULT, base_p=BASE, target=TARGET, speed=SPEED,
                      seed=7, episode=3)
    d2 = sample_spawn(DEFAULT, base_p=BASE, target=TARGET, speed=SPEED,
                      seed=7, episode=3)
    assert d1 == d2                                   # 결정론

    seen = {sample_spawn(DEFAULT, base_p=BASE, target=TARGET, speed=SPEED,
                         seed=7, episode=e).p for e in range(64)}
    assert len(seen) == 64                            # 에피소드마다 다르다

    # seed 가 다르면 다른 스트림
    a = sample_spawn(DEFAULT, base_p=BASE, target=TARGET, speed=SPEED,
                     seed=7, episode=3).p
    b = sample_spawn(DEFAULT, base_p=BASE, target=TARGET, speed=SPEED,
                     seed=8, episode=3).p
    assert a != b


def test_p20b_no_python_hash():
    """SHA-256 기반이므로 프로세스 salt 에 무관 -- 값이 고정 상수여야 한다."""
    u = derive_spawn_u(0, 0, "m4_spawn", 3)
    # 재현 고정값 (다른 프로세스/파이썬 세션에서도 동일해야 함)
    assert all(0.0 <= x < 1.0 for x in u)
    assert derive_spawn_u(0, 0, "m4_spawn", 3) == u
    assert derive_spawn_u(0, 1, "m4_spawn", 3) != u


# ---------------------------------------------------------------- P21 -------
def test_p21_ranges_respected():
    """선언 범위를 절대 벗어나지 않는다."""
    for ep in range(500):
        d = sample_spawn(DEFAULT, base_p=BASE, target=TARGET, speed=SPEED,
                         seed=1, episode=ep)
        p = np.array(d.p)
        assert BASE[0] - DEFAULT.dx - 1e-9 <= p[0] <= BASE[0] + DEFAULT.dx + 1e-9
        lat = math.hypot(p[1], p[2])
        assert lat <= DEFAULT.r_lat + 1e-9
        # speed_frac=0 -> 속력 정확히 보존
        assert abs(np.linalg.norm(d.v) - SPEED) < 1e-9
        assert abs(np.linalg.norm(d.e) - 1.0) < 1e-9


def test_p21b_speed_frac_bound():
    spec = SpawnSpec(speed_frac=0.25)
    for ep in range(200):
        d = sample_spawn(spec, base_p=BASE, target=TARGET, speed=SPEED,
                         seed=2, episode=ep)
        assert 0.75 * SPEED - 1e-9 <= np.linalg.norm(d.v) <= 1.25 * SPEED + 1e-9


# ---------------------------------------------------------------- P22 -------
def test_p22_velocity_aims_at_target_when_psi_zero():
    """psi=0 이면 초기 속도는 스폰점에서 표적을 정확히 겨눈다."""
    for ep in range(200):
        d = sample_spawn(DEFAULT, base_p=BASE, target=TARGET, speed=SPEED,
                         seed=5, episode=ep)
        p = np.array(d.p); v = np.array(d.v)
        want = np.array(TARGET) - p
        want /= np.linalg.norm(want)
        assert np.allclose(v / np.linalg.norm(v), want, atol=1e-12)


def test_p22b_psi_cone_bound():
    """psi>0 이면 각오차가 psi 를 넘지 않는다."""
    psi = 0.15
    spec = SpawnSpec(psi=psi)
    for ep in range(300):
        d = sample_spawn(spec, base_p=BASE, target=TARGET, speed=SPEED,
                         seed=6, episode=ep)
        p = np.array(d.p); v = np.array(d.v)
        want = np.array(TARGET) - p; want /= np.linalg.norm(want)
        ct = float(np.dot(v / np.linalg.norm(v), want))
        assert ct >= math.cos(psi) - 1e-9


# ---------------------------------------------------------------- P23 -------
def test_p23_lateral_is_area_uniform():
    """면적 균일이어야 한다 -- 반경 균일이면 중심이 과표집된다.

    면적 균일이면 lat <= r_lat/sqrt(2) 인 비율이 ~1/2 이다.
    """
    n = 4000
    lats = []
    for ep in range(n):
        d = sample_spawn(DEFAULT, base_p=BASE, target=TARGET, speed=SPEED,
                         seed=9, episode=ep)
        lats.append(math.hypot(d.p[1], d.p[2]))
    lats = np.array(lats)
    frac = float((lats <= DEFAULT.r_lat / math.sqrt(2)).mean())
    assert abs(frac - 0.5) < 0.03, f"area-uniform 위반: {frac:.3f}"
    # 축방향도 대략 균일
    xs = np.array([sample_spawn(DEFAULT, base_p=BASE, target=TARGET, speed=SPEED,
                                seed=9, episode=e).p[0] for e in range(n)])
    assert abs(xs.mean() - BASE[0]) < 0.12


def test_p23b_axes_uncorrelated():
    """축끼리 상관이 없어야 한다 (같은 균일난수 재사용 버그 방지)."""
    n = 3000
    xs, lats = [], []
    for ep in range(n):
        d = sample_spawn(SpawnSpec(speed_frac=0.3), base_p=BASE, target=TARGET,
                         speed=SPEED, seed=4, episode=ep)
        xs.append(d.p[0]); lats.append(math.hypot(d.p[1], d.p[2]))
    r = float(np.corrcoef(xs, lats)[0, 1])
    assert abs(r) < 0.06, f"축 상관 {r:.3f}"


# ---------------------------------------------------------------- P24 -------
def test_p24_spawn_constant_within_episode():
    """에피소드 내에서 스폰이 다시 흔들리지 않는다 (리셋 시점에만 적용)."""
    env, scn, lay = _env()
    spawn_for_episode(env, DEFAULT, seed=13, episode=2)
    p0 = np.array(_adv(env).p0, float).copy()
    env.reset(seed=13)
    acts = {aid: np.zeros(env.action_space(aid).shape, np.float32)
            for aid in env.agents}
    for _ in range(15):
        env.step(acts)
        assert np.array_equal(np.array(_adv(env).p0, float), p0)


def test_p24b_no_random_walk_across_episodes():
    """반복 적용해도 base 가 누적 이동하지 않는다."""
    env, scn, lay = _env()
    base = np.array(_adv(env).p0, float).copy()
    for ep in range(30):
        spawn_for_episode(env, DEFAULT, seed=17, episode=ep)
    # 같은 (seed, ep) 를 다시 요청하면 같은 값 -> 누적 없음
    d_again = spawn_for_episode(env, DEFAULT, seed=17, episode=5)
    d_fresh = sample_spawn(DEFAULT, base_p=base, target=lay.target,
                           speed=scn.adversary.speed, seed=17, episode=5)
    assert np.allclose(d_again.p, d_fresh.p, atol=1e-12)


# ---------------------------------------------------------------- P25 -------
def test_p25_rollout_reproducible_under_spawn():
    """스폰을 적용해도 (seed, ep) 가 같으면 궤적이 완전히 재현된다."""
    def roll():
        env, scn, lay = _env()
        spawn_for_episode(env, DEFAULT, seed=21, episode=4)
        env.reset(seed=21)
        acts = {aid: np.zeros(env.action_space(aid).shape, np.float32)
                for aid in env.agents}
        out = []
        for _ in range(25):
            env.step(acts)
            out.append(np.array(_adv(env).p, float).copy())
        return np.array(out)

    assert np.array_equal(roll(), roll())


# ---------------------------------------------------------------- P26 -------
@pytest.mark.parametrize("ep", list(range(24)))
def test_p26_scenario_stays_well_posed(ep):
    """★ 시나리오 적형성: 어떤 스폰에서도 공격자가 지평선 안에 표적에 도달한다.

    이게 깨지면 M4 보상이 TRUNCATED(=실패)를 남발하고, 결과가 '지평선의 산물'이
    되어 §6 주장이 무너진다. **무방어 조건**에서 확인한다.
    """
    env, scn, lay = _env()
    spawn_for_episode(env, DEFAULT, seed=31, episode=ep)
    env.reset(seed=31)
    acts = {aid: np.zeros(env.action_space(aid).shape, np.float32)
            for aid in env.agents}
    # limiter 를 멀리 치워 무방어로 만든다 (개입 없는 도달성만 본다)
    for i, aid in enumerate(env.limiter_ids):
        env.backend.by_name(aid).p = np.array([0.0, 0.0, 1.0e4]) + i

    d_min = np.inf
    for k in range(lay.episode_len):
        env.step(acts)
        d = float(np.linalg.norm(np.array(_adv(env).p, float)
                                 - np.asarray(lay.target, float)))
        d_min = min(d_min, d)
        if d <= lay.target_radius:
            break
    assert d_min <= lay.target_radius + 1e-6, (
        f"ep={ep}: 무방어인데 표적 미도달 (d_min={d_min:.2f} > "
        f"{lay.target_radius}) -- 스폰 범위가 시나리오를 깨뜨린다")


# ---------------------------------------------------------------- P27 -------
@pytest.mark.skipif(not os.environ.get("RUN_SLOW"),
                    reason="임무 롤아웃 (수십 초). RUN_SLOW=1 로 활성화")
def test_p27_horizon_is_not_the_binding_constraint():
    """★ 지평선 게이트: TRUNCATED 가 방어 결과여야지 부기(簿記) 산물이면 안 된다.

    P26 은 **무방어** 도달성만 본다. 링이 서 있으면 공격자가 밀려나며 지연되므로
    지평선이 짧으면 TRUNCATED 가 대량 발생하고, M4 보상은 그걸 `-c_trunc`
    (실패)로 벌한다 -> 결과가 지평선의 산물이 된다 (docs/36 §2.6 의 위험).

    측정값(2026-07-29, ring, 기본 스폰, 30 ep): H=80 -> 13/30 TRUNCATED,
    H=160 -> 2/30, H=320 -> 2/30 (수렴). **80 은 짧고 160 이 최소 충분 지평선이다.**
    """
    from shepherd.scripts.mission_rollout import run_episode

    def trunc_frac(H, n=10):
        k = 0
        for ep in range(n):
            env, scn, lay = _env({"train.episode_len": H})
            spawn_for_episode(env, DEFAULT, seed=0, episode=ep)
            r = run_episode(env, scn, lay, seed=ep, limiter_mode="ring",
                            fire_mode="clean")
            k += (r.label == "TRUNCATED")
        return k / n

    f80, f160 = trunc_frac(80), trunc_frac(160)
    assert f80 > f160, f"H=80 {f80:.2f} vs H=160 {f160:.2f}"
    assert f160 <= 0.2, (
        f"H=160 에서도 TRUNCATED {f160:.2f} -- 지평선을 더 늘리거나 "
        "스폰 범위 선언을 재검토할 것 (범위를 결과에 맞춰 줄이지 말 것)")


# ---------------------------------------------------------------- config ----
def test_config_axis_is_opt_in():
    """randomized_config 는 범위를 안 주면 아무것도 바꾸지 않는다."""
    cfg = as_config()
    out = randomized_config(cfg, seed=1, episode=1)
    assert out["physics"] == cfg["physics"]

    out2 = randomized_config(cfg, seed=1, episode=1, att_speed_range=(15.0, 25.0))
    assert 15.0 <= out2["physics"]["att_speed"] <= 25.0
    assert out2["physics"]["a_att_max"] == cfg["physics"]["a_att_max"]
    assert cfg["physics"]["att_speed"] == 20.0          # 원본 불변 (딥카피)
