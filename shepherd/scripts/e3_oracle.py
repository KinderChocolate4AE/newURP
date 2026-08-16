"""E3 — controller-limited vs capability-limited 판별 (docs/83 §18 동결 프로토콜).

두 가지를 **한 런에서** 낸다:

  (1) per-limiter 분해 (§18.1b) — "4 기가 같이 달려들고 같이 놓치는가" 를 숫자로.
  (2) **hindsight pathwise reachability** (§18.2) — 정본 명칭 그대로.

      d_oracle,i = min_t max(0, |p_A(t) - (p_L0,i + v_L0,i * t)| - R(t))
      R = contact_reachability.reach_radius (재사용; 새 정의 금지)

★ 해석 한계 (§18.2, 결과 문장에 반드시 병기)
  T1 공격자는 방어자를 보고 반응하므로 pi_L 을 바꾸면 궤적도 바뀐다. 따라서 이 양은
  **realized attacker trajectory 에 대한 hindsight 도달성** 이고,
    보여주는 것 : vehicle dynamics alone do not explain the miss on that realized path
    보여주지 못하는 것 : a realizable causal role-assignment policy would necessarily succeed
  드리프트-중심 근사가 v_L0 + dv <= v_max 결합을 무시하므로 **의도적으로 낙관**이다
  (oracle 이 못 닿으면 capability 한계 주장이 강해진다).

세계 = curve_sweep/E2-A 와 동일 (ratified + T1 + intercept + commit).

    python -m shepherd.scripts.e3_oracle --n 300 --out results/e3_oracle_r4.json

torch-free.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
from typing import List

import numpy as np

from shepherd.scripts.contact_reachability import reach_radius
from shepherd.scripts.dump_trajectory import _build_t1
from shepherd.scripts.recoverability_probe import _Driver
from shepherd.stats import wilson

__all__ = ["episode_e3"]

R_CONTACT = 0.75          # 접촉반경 (판정 기준, m4_config kill_radius)


def episode_e3(ep: int) -> dict:
    env, scn, lay = _build_t1(ep)
    d = _Driver(env, scn, lay, ep)
    se = d.se
    dt = float(env.dt)
    n_lim = len(env.limiter_ids)

    # limiter 초기 상태 (oracle 의 출발점)
    lims0, _, att0 = env._states()
    pL0 = np.array([env._p(s) for s in lims0], float)
    vL0 = np.array([env._v(s) for s in lims0], float)
    a_lim = float(getattr(env, "a_lim_max", scn.limiter.a_max))
    v_lim = float(env.backend.by_name(env.limiter_ids[0]).limits.v_max)

    traj: List[np.ndarray] = []                      # p_A(t) (이동 후)
    # R4 (docs/83 §29): 근접거리는 _Driver 권위 측정을 읽는다. 자체 루프 금지.
    hk_step = None
    for t in range(int(lay.episode_len)):
        fi = d.step(limiter_mode="intercept", baseline_commit=True)
        lims2, _, att2 = env._states()
        p_att = env._p(att2)
        traj.append(p_att.copy())
        if hk_step is None and bool(fi.get("hard_kill", False)):
            hk_step = t
        if d.done:
            break

    dmin, tmin = d.d_min, d.t_min          # R4 권위 측정 (docs/83 §29)

    # --- oracle: hindsight pathwise reachability -----------------------------
    P = np.asarray(traj, float)                       # (T,3)
    T = len(P)
    tt = (np.arange(T) + 1) * dt                      # 이동 후 시각
    Rt = np.array([reach_radius(x, a_lim, v_lim) for x in tt])
    d_or = np.empty(n_lim)
    t_or = np.empty(n_lim, int)
    for i in range(n_lim):
        drift = pL0[i][None, :] + vL0[i][None, :] * tt[:, None]
        gap = np.linalg.norm(P - drift, axis=1) - Rt
        gap = np.maximum(gap, 0.0)
        k = int(np.argmin(gap))
        d_or[i], t_or[i] = float(gap[k]), k

    commits = {r.limiter_index: r.commit_step for r in se.commits}
    tc = [commits.get(i) for i in range(n_lim)]
    tmin_s = tmin * dt

    # 접근 방위 spread: 최근접 시점의 limiter->attacker 단위벡터 간 최대각
    ang = None
    try:
        us = []
        for i in range(n_lim):
            k = int(tmin[i])
            if k >= 0:
                v = P[k] - (pL0[i] + vL0[i] * tt[k])
                nv = float(np.linalg.norm(v))
                if nv > 1e-9:
                    us.append(v / nv)
        if len(us) >= 2:
            ang = max(float(math.degrees(math.acos(np.clip(a @ b, -1, 1))))
                      for a in us for b in us)
    except Exception:                                          # pragma: no cover
        ang = None

    return {
        "episode": ep, "label": d.label, "a_att": float(env.a_att_max),
        "att_speed": float(env.v_nominal), "steps": T,
        "hk_step": hk_step,
        "a_lim": a_lim, "v_lim": v_lim,
        # per-limiter
        "d_min": [round(float(x), 3) for x in dmin],
        "t_min": [round(float(x), 3) for x in tmin_s],
        "t_commit": [None if c is None else round(c * dt, 3) for c in tc],
        "d_oracle": [round(float(x), 3) for x in d_or],
        "t_oracle": [round(float(x) * dt, 3) for x in t_or],
        # episode 요약 (§18.1b)
        "d_min_best": round(float(dmin.min()), 3),
        "d_oracle_best": round(float(d_or.min()), 3),
        "std_t_min": round(float(np.std(tmin_s)), 3),
        "range_t_min": round(float(tmin_s.max() - tmin_s.min()), 3),
        "std_d_min": round(float(np.std(dmin)), 3),
        "n_committed": sum(1 for c in tc if c is not None),
        "spread_t_commit": (None if sum(1 for c in tc if c is not None) < 2 else
                            round(float(np.std([c * dt for c in tc if c is not None])), 3)),
        "angular_spread_deg": None if ang is None else round(ang, 1),
        "n_oracle_reach": int((d_or <= R_CONTACT).sum()),
        "n_actual_reach": int((dmin <= R_CONTACT).sum()),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="E3 oracle + per-limiter (docs/83 §18)")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--out", default="results/e3_oracle_r4.json")
    a = ap.parse_args()
    print(f"[E3 · docs/83 §18] n={a.n} · 세계 = curve_sweep/E2-A 동일 "
          f"(ratified + T1 + intercept + commit)", flush=True)

    rows = []
    import time
    t0 = time.time()
    for ep in range(a.n):
        rows.append(episode_e3(ep))
        if (ep + 1) % 25 == 0 or ep + 1 == a.n:
            el = time.time() - t0
            print(f"  {ep+1}/{a.n}  {el:6.1f}s ({el/(ep+1):.2f} s/ep, "
                  f"ETA {el/(ep+1)*(a.n-ep-1):5.0f}s)", flush=True)

    n = len(rows)
    act = np.array([r["d_min_best"] for r in rows])
    orc = np.array([r["d_oracle_best"] for r in rows])
    ka, ko = int((act <= R_CONTACT).sum()), int((orc <= R_CONTACT).sum())
    rng = np.random.default_rng(0)
    dd = orc - act
    idx = rng.integers(0, n, size=(20000, n))
    lo, hi = np.percentile(np.median(dd[idx], axis=1), [2.5, 97.5])

    print(f"\n=== Primary (§18.3) ===")
    print(f"  P(d_actual <= {R_CONTACT}) = {ka/n:.3f} {wilson(ka,n)}")
    print(f"  P(d_oracle <= {R_CONTACT}) = {ko/n:.3f} {wilson(ko,n)}")
    print(f"  paired Delta_d median {np.median(dd):+.3f} m  CI95 [{lo:+.3f}, {hi:+.3f}]")
    print(f"  최근접 med  actual {np.median(act):.3f} · oracle {np.median(orc):.3f}")
    print(f"\n=== per-limiter 분해 (§18.1b) ===")
    print(f"  std(t_min) med {np.median([r['std_t_min'] for r in rows]):.3f} s · "
          f"range(t_min) med {np.median([r['range_t_min'] for r in rows]):.3f} s")
    print(f"  std(d_min) med {np.median([r['std_d_min'] for r in rows]):.3f} m")
    ang = [r["angular_spread_deg"] for r in rows if r["angular_spread_deg"] is not None]
    if ang:
        print(f"  angular spread med {np.median(ang):.1f} deg")
    print(f"  커밋 limiter 수 med {np.median([r['n_committed'] for r in rows]):.1f} / 4")
    print(f"  oracle 로 닿을 수 있었던 limiter 수 med "
          f"{np.median([r['n_oracle_reach'] for r in rows]):.1f} / 4 "
          f"(실제 {np.median([r['n_actual_reach'] for r in rows]):.1f})")

    from shepherd.scripts.pivot_manifest import stamp
    out = {"manifest": dict(
               stamp(artifact="e3_oracle"),
               prereg_doc="docs/83 §18 (E3)",
               oracle_name="hindsight pathwise reachability on the realized "
                           "attacker trajectory",
               oracle_caveat="T1 attacker reacts to defenders; changing pi_L changes "
                             "the trajectory. Shows vehicle dynamics alone do not "
                             "explain the miss on that realized path; does NOT show a "
                             "realizable causal policy would succeed. Drift-center "
                             "approximation ignores v_max coupling => optimistic.",
               world="curve_sweep/E2-A 동일 (ratified + T1 route0.5/sense30 + "
                     "intercept + baseline_commit)",
               r_contact=R_CONTACT, n=a.n),
           "primary": {"n": n, "p_actual_reach": ka / n, "p_oracle_reach": ko / n,
                       "wilson_actual": list(wilson(ka, n)),
                       "wilson_oracle": list(wilson(ko, n)),
                       "delta_median": float(np.median(dd)),
                       "delta_ci95": [float(lo), float(hi)],
                       "d_actual_med": float(np.median(act)),
                       "d_oracle_med": float(np.median(orc))},
           "records": rows}
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n  -> {p}", flush=True)


if __name__ == "__main__":
    main()
