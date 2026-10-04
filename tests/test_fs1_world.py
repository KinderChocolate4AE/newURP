"""docs/123 FS1: lean 은 포획 판정을 바꾸지 않는다 · 배치 편향 없음 · H_illegal 라벨."""
import numpy as np

from shepherd.fs1.world import ADV, FIN, FS1Env


def _scripted_episode(env, seed, fire_d=12.0):
    obs, _ = env.reset(seed=seed)
    inn, done = env.inner, False
    while not done:
        lims, fin, att = inn._states()
        pa, pf = inn._p(att), inn._p(fin)
        nc = np.asarray(inn._net_center(pa, inn._v(att)))
        ax = (nc - pf) / max(np.linalg.norm(nc - pf), 1e-9)
        f = 1.0 if (np.linalg.norm(pa - pf) < fire_d and inn.fsm.state.value == "LOADED") else 0.0
        acts = {l: np.zeros(4) for l in env.limiter_ids}
        acts[FIN] = np.r_[ax, 1.0, f, 0, 0, 0]
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
        acts[FIN] = np.r_[1, 0, 0, 1, 0, 0, 0, 0]
        acts[ADV] = np.zeros(3)
        obs, r, done, info = e.step(acts)
    assert info[FIN]["fs1_label"] == "PENETRATED"
    assert r[ADV] == 1.0 and r[FIN] == -1.0
