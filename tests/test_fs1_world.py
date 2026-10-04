"""docs/123 FS1: lean 은 포획 판정을 바꾸지 않는다 · 배치 편향 없음 · H_illegal 라벨."""
import numpy as np

from shepherd.fs1.world import ADV, FIN, FS1Env


def _scripted_episode(env, seed, fire_d=12.0):
    obs, _ = env.reset(seed=seed)
    done = False
    while not done:
        acts = {l: np.zeros(4) for l in env.limiter_ids}
        acts[FIN] = np.r_[0, 0, 0, fire_d, 1.0]          # FCS: 무장 + 발사거리
        acts[ADV] = np.zeros(3)
        obs, r, done, info = env.step(acts)
    return info[FIN]["fs1_label"], r


def test_lean_does_not_change_outcomes():
    a, b = FS1Env(seed=0), FS1Env(seed=0)
    b.inner.lean = False                               # 매 step 전체 viability 계산
    for s in range(6):
        assert _scripted_episode(a, 50 + s) == _scripted_episode(b, 50 + s)


def test_placement_is_unbiased_ring_and_center():
    e = FS1Env(seed=0)
    bear = []
    for s in range(40):
        e.reset(seed=s)
        p = np.asarray(e.inner.backend.by_name(ADV).p0)
        assert 100.0 <= np.hypot(p[0], p[1]) <= 300.0 and p[2] == 0.0
        bear.append(np.arctan2(p[1], p[0]))
        for lid in e.limiter_ids:
            assert abs(np.linalg.norm(e.inner.backend.by_name(lid).p0) - 2.0) < 1e-9
    assert np.ptp(bear) > 4.0                          # 방위가 한쪽에 몰리지 않음


def test_rewards_penetration_zero_sum_sign():
    e = FS1Env(seed=0)
    obs, _ = e.reset(seed=3)
    done = False
    while not done:
        acts = {l: np.zeros(4) for l in e.limiter_ids}
        acts[FIN] = np.r_[0, 0, 0, 12.0, 0.0]            # 무장 안 함
        acts[ADV] = np.zeros(3)
        obs, r, done, info = e.step(acts)
    assert info[FIN]["fs1_label"] == "PENETRATED"
    assert r[ADV] == 1.0 and r[FIN] == -1.0


def test_fcs_fires_inside_range_and_captures_sometimes():
    from collections import Counter
    e = FS1Env(seed=0)
    c = Counter(_scripted_episode(e, 200 + s)[0] for s in range(20))
    assert c["NET_CAPTURE"] + c["CAPTURE_WITH_CONTACT"] >= 3     # 직진 공격자 ~50% 포획
