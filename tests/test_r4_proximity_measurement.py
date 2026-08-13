"""R4 회귀 게이트 R4-A ~ R4-D (docs/83 §29.3). 4/4 통과 전 재실행 금지.

계약 = 주차 이전 post 좌표(`ModeSystemEnv.lims_post_raw`) + `retired_pre` 스냅샷 제외
       + `_Driver.d_min/t_min` 권위 측정.

    python -m pytest tests/test_r4_proximity_measurement.py -q

torch-free.
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

from shepherd.env_sys import ModeSystemEnv, _seg_min_dist
from shepherd.scripts.dump_trajectory import _build_t1
from shepherd.scripts.e4_stagger import R_CONTACT, episode_e4
from shepherd.scripts.recoverability_probe import _Driver

E4C = pathlib.Path("results/e4c_uniform.json")
EP0, DELTA = 30000, 0.125


def _run(ep: int, delta: float = DELTA):
    """E4-1c 와 동일 세계로 한 판 굴리고 driver 를 돌려준다."""
    env, scn, lay = _build_t1(ep)
    d = _Driver(env, scn, lay, ep)
    for _ in range(int(lay.episode_len)):
        d.step(limiter_mode="intercept", baseline_commit=True,
               limiter_kw={"lead_deltas": [delta] * len(env.limiter_ids)})
        if d.done:
            break
    return d


# --- R4-A (최우선) ---------------------------------------------------------
@pytest.mark.skipif(not E4C.exists(), reason="results/e4c_uniform.json 필요")
def test_r4a_labels_bit_exact_vs_frozen():
    """R4-A — 수리가 **결과를 바꾸지 않는다**. 동결 E4-1c 라벨과 완전 일치.

    실패 시 즉시 중단: 수리가 물리/순서/난수로 샜다는 뜻이다.
    """
    frozen = {r["episode"]: r for r in
              json.loads(E4C.read_text(encoding="utf-8"))["records"]["0.125"]}
    n = 0
    for ep in range(EP0, EP0 + 40):
        got = episode_e4(ep, DELTA, "uniform")
        exp = frozen[ep]
        assert got["label"] == exp["label"], f"ep{ep} 라벨 {got['label']} != {exp['label']}"
        assert got["deltas"] == exp["deltas"], f"ep{ep} delta 배정 불일치"
        n += 1
    assert n == 40


# --- R4-B ------------------------------------------------------------------
def test_r4b_contact_records_match_authoritative():
    """R4-B — 권위 측정이 해소기와 **같은 입력**을 쓰고, 접촉 record 를 재현한다."""
    orig = ModeSystemEnv._resolve_contacts
    seen = []

    def spy(self, p_att_pre, lims_pre, p_att_post, lims_post, d_asset):
        ev = orig(self, p_att_pre, lims_pre, p_att_post, lims_post, d_asset)
        if ev:
            # 해소기가 받은 post 좌표 == R4 가 기록한 주차 이전 좌표 (부동소수 동일)
            for i, q in enumerate(lims_post):
                assert np.array_equal(np.asarray(q, float),
                                      np.asarray(self.lims_post_raw[i], float)), \
                    "lims_post_raw 가 해소기 입력과 다르다"
            assert np.array_equal(np.asarray(p_att_post, float),
                                  np.asarray(self.p_att_post_raw, float))
            for r in ev:
                # 같은 술어를 같은 입력에 적용하면 같은 수가 나와야 한다
                i = r.limiter_index
                d = _seg_min_dist(np.asarray(p_att_pre, float) - np.asarray(lims_pre[i], float),
                                  np.asarray(p_att_post, float) - np.asarray(lims_post[i], float))
                assert d == r.d_nom, f"재계산 {d} != d_nom {r.d_nom}"
                seen.append(r)
        return ev

    ModeSystemEnv._resolve_contacts = spy
    try:
        n_contact = 0
        for ep in range(EP0, EP0 + 30):
            before = len(seen)
            d = _run(ep)
            for r in seen[before:]:
                if r.source != "contact":
                    continue
                n_contact += 1
                i = r.limiter_index
                # 결함의 핵심: 예전엔 여기가 63 m 였다
                assert d.d_min[i] <= R_CONTACT + 1e-9, \
                    f"ep{ep} limiter{i}: d_min {d.d_min[i]:.3f} > r_contact"
                assert d.d_min[i] <= r.d_nom + 1e-12, \
                    f"ep{ep} limiter{i}: d_min {d.d_min[i]} > d_nom {r.d_nom}"
    finally:
        ModeSystemEnv._resolve_contacts = orig
    assert n_contact > 0, "접촉 record 가 한 건도 없어 게이트가 공회전했다"


# --- R4-C ------------------------------------------------------------------
def test_r4c_no_retirement_episodes_bit_exact():
    """R4-C — retirement 가 없는 에피소드는 구/신 진단이 bit-exact.

    수리가 **주차 오염만** 제거했음을 증명한다 (범위 한정).
    """
    checked = 0
    for ep in range(EP0, EP0 + 60):
        env, scn, lay = _build_t1(ep)
        d = _Driver(env, scn, lay, ep)
        n_lim = len(env.limiter_ids)
        old = np.full(n_lim, np.inf)
        pre = [env._p(s).copy() for s in env._states()[0]]
        pre_a = env._p(env._states()[2]).copy()
        retired_ever = False
        for _ in range(int(lay.episode_len)):
            d.step(limiter_mode="intercept", baseline_commit=True,
                   limiter_kw={"lead_deltas": [DELTA] * n_lim})
            lims2, _, att2 = env._states()
            # 구 진단: post-step 좌표 + post-step retired 필터
            for i in range(n_lim):
                if i in d.se.retired:
                    continue
                old[i] = min(old[i], _seg_min_dist(pre_a - pre[i],
                                                   env._p(att2) - env._p(lims2[i])))
            pre = [env._p(s).copy() for s in lims2]
            pre_a = env._p(att2).copy()
            if d.se.retired:
                retired_ever = True
            if d.done:
                break
        if retired_ever:
            continue
        checked += 1
        assert np.array_equal(old, d.d_min), f"ep{ep} retirement 없는데 구/신 불일치"
    assert checked >= 5, f"retirement 없는 에피소드가 {checked} 개뿐 — 게이트가 약하다"


# --- R4-D ------------------------------------------------------------------
def test_r4d_p_reach_ge_p_hk_contact():
    """R4-D — 캠페인 수준 `p_reach >= P_HK_contact`. 수리 전엔 세 팔 전부 위반."""
    n, reach, hk = 50, 0, 0
    for ep in range(EP0, EP0 + n):
        d = _run(ep)
        if float(np.min(d.d_min)) <= R_CONTACT:
            reach += 1
        if d.label == "HARD_KILL":
            hk += 1
    assert hk > 0, "하드킬이 없어 게이트가 공회전했다"
    assert reach >= hk, f"p_reach {reach}/{n} < P_HK {hk}/{n} — 모순이 남아 있다"


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
