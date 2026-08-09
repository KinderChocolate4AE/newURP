"""Phase III 게이트 9 — 독립 judge cross-check (docs/75 게이트 9 · docs/77 [C]).

    python -m shepherd.scripts.judge_crosscheck --episodes 10 --out results/phase3/judge_crosscheck.json

왜 (docs/74 §2 B2): Phase II 와 Phase III 가 **같은 judge 코드**를 쓰면 judge 버그가
common-mode 로 양쪽에 동시에 들어간다. 그래서 지도 셀을 만들기 전에 세 판정을
**독립 수식 경로**로 재계산해 signed geometric margin 으로 대조한다:

  1. cone containment   primary: arccos(dot)-기반 각도 -> rn*sin(theta-ang) 마진
                        독립:    축/수직 성분 선형식 ax*sin(theta) - perp*cos(theta)
                        (수학적으로 동일량, 코드/수치 경로가 다름. 단위 = m)
  2. witness kill       primary: ||pts - L|| <= r_kill (subtract-then-norm)
                        독립:    |p|^2 + |L|^2 - 2 p.L 내적 전개 후 sqrt
                        마진 = min_{t,L} d - r_kill (m)
  3. threshold feasibility  primary: VShotResult (v_shot_soft, boxed) -> g = 1[v>=theta & ~boxed]
                        독립:    독립 predicate 로 caught/feasible 재카운팅

판정 (docs/77 [C]): |m1 - m2| <= eps (1e-6 m / 무차원 1e-9). predicate 불일치는
|m| <= eps 인 boundary case 에서만 허용 — **boundary 에서 먼 불일치 1 건이면
지도 중단·버그 감사** (verdict FAIL).

witness 집합(build_reachable_union)은 봉인된 *정의*이므로 입력으로 공유한다 —
cross-check 대상은 그 위의 **판정**이다. 봉쇄 비활성 함정(docs/77 §4-2)을 피하려고
hold 배치와 probe 배치(부분 봉쇄 활성) 둘 다에서 kill 판정을 대조한다.

torch-free.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib

import numpy as np

from shepherd.game import viability as V
from shepherd.m4_env import build_m4_env
from shepherd.scripts.measure_harness import (
    THETA, _lattice_hash, _world_kw, collect_states, probe_placement)
from shepherd.scripts.pivot_manifest import stamp
from shepherd.scripts.threat_v3_gates import _base_env

EPS_M = 1e-6          # 길이 마진 허용오차 (m)
EPS_DIMLESS = 1e-9    # 무차원 (v_shot 등)
_APEX_EPS = 1e-12     # primary 의 at_apex 판정 (_EPS) 과 동일한 봉인 정의


# ── primary-경로 마진 (primary 와 같은 수식 계열: arccos-dot / subtract-norm) ──

def cone_margin_primary(endpoints, apex, n_axis, theta, rmin, rmax):
    """rn·sin(theta - ang), ang = arccos(dot/(rn)) — primary `_caught_se3_cone`
    의 각도 경로를 그대로 밟아 m 로 환산. min(cone, band) 반환."""
    n = np.asarray(n_axis, float)
    n = n / np.linalg.norm(n)
    r = np.asarray(endpoints, float) - np.asarray(apex, float)[None, :]
    rn = np.linalg.norm(r, axis=1)
    ax = r @ n
    cos_a = np.where(rn < _APEX_EPS, 1.0, ax / (rn + 1e-12))
    ang = np.arccos(np.clip(cos_a, -1.0, 1.0))
    m_cone = rn * np.sin(float(theta) - ang)
    hi = np.inf if rmax is None else float(rmax)
    m_band = np.minimum(ax - float(rmin), hi - ax)
    m = np.minimum(m_cone, m_band)
    m[rn < _APEX_EPS] = 0.0                     # at_apex: 경계값 (caught 정의상 포함)
    return m


def kill_margin_primary(path_blocks, limiters, kill_radius):
    """min over (substep, limiter) of ||p - L|| - r_kill. primary 의
    subtract-then-norm 경로."""
    L = np.asarray(limiters, float).reshape(-1, 3)
    mins = []
    for pb in path_blocks:
        d = np.linalg.norm(pb[:, :, None, :] - L[None, None, :, :], axis=3)
        mins.append(d.min(axis=(1, 2)))
    return np.concatenate(mins) - float(kill_radius)


# ── 독립 경로 마진 (다른 수식 구성) ─────────────────────────────────────────

def cone_margin_indep(endpoints, apex, n_axis, theta, rmin, rmax):
    """ax·sin(theta) - perp·cos(theta) — arccos 없이 축/수직 분해 선형식."""
    n = np.asarray(n_axis, float)
    n = n / math.sqrt(float(n @ n))
    r = np.asarray(endpoints, float) - np.asarray(apex, float)[None, :]
    ax = r @ n
    perp_sq = np.maximum((r * r).sum(axis=1) - ax * ax, 0.0)
    perp = np.sqrt(perp_sq)
    st, ct = math.sin(float(theta)), math.cos(float(theta))
    m_cone = ax * st - perp * ct
    hi = np.inf if rmax is None else float(rmax)
    m_band = np.minimum(ax - float(rmin), hi - ax)
    m = np.minimum(m_cone, m_band)
    rn_sq = (r * r).sum(axis=1)
    m[rn_sq < _APEX_EPS ** 2] = 0.0
    return m


def kill_margin_indep(path_blocks, limiters, kill_radius):
    """내적 전개 |p|^2 + |L|^2 - 2 p·L 로 최소 제곱거리 -> sqrt - r_kill."""
    L = np.asarray(limiters, float).reshape(-1, 3)
    L_sq = (L * L).sum(axis=1)                              # (nL,)
    mins = []
    for pb in path_blocks:
        p_sq = (pb * pb).sum(axis=2)                        # (n, T)
        cross = pb @ L.T                                    # (n, T, nL)
        d_sq = p_sq[:, :, None] + L_sq[None, None, :] - 2.0 * cross
        mins.append(np.sqrt(np.maximum(d_sq, 0.0)).min(axis=(1, 2)))
    return np.concatenate(mins) - float(kill_radius)


def assemble_indep(caught, feasible, theta):
    """독립 카운팅: v = caught/feasible 비율, boxed = nf==0 (봉인 정의 그대로)."""
    nf = int(feasible.sum())
    if nf == 0:
        return 1.0, True, 0
    v = float(int(caught[feasible].sum()) / nf)
    return v, False, nf


# ── cross-check 본체 ─────────────────────────────────────────────────────────

def crosscheck_state(base, s, *, n=2000, n_segments=4, n_dir=32):
    kw = base._vshot_kwargs(s["p_att"], s["v_att"], s["fin"])
    union = V.build_reachable_union(
        s["p_att"], s["v_att"], tau=base.tau_deploy, a_att_max=base.a_att_max,
        n=n, n_segments=n_segments, n_dir=n_dir, seed=int(s["t"]), **kw)

    # 1. cone containment (layout 무관 -- union.caught 가 primary predicate)
    if kw["judge"] == "se3_cone":
        m1 = cone_margin_primary(union.endpoints, kw["net_apex"], kw["n_F"],
                                 kw["theta_net"], kw["range_min"], kw["range_max"])
        m2 = cone_margin_indep(union.endpoints, kw["net_apex"], kw["n_F"],
                               kw["theta_net"], kw["range_min"], kw["range_max"])
    else:                                                    # point_mass
        d1 = np.linalg.norm(union.endpoints - np.asarray(kw["net_center"])[None, :], axis=1)
        m1 = float(kw["net_radius"]) - d1
        e = np.asarray(union.endpoints, float)
        c = np.asarray(kw["net_center"], float)
        d2_sq = (e * e).sum(1) + float(c @ c) - 2.0 * (e @ c)
        m2 = float(kw["net_radius"]) - np.sqrt(np.maximum(d2_sq, 0.0))
    caught2 = m2 >= 0.0
    cone = _compare("cone", m1, m2, np.asarray(union.caught, bool), caught2, EPS_M)

    out = {"cone": cone, "layouts": {}}

    # 2·3. witness kill + threshold feasibility -- hold 배치와 probe 배치(봉쇄 활성) 둘 다
    layouts = {"hold": [np.asarray(p, float) for p in s["lim"]],
               "probe": probe_placement(base, s)}
    for name, lims in layouts.items():
        r1 = V.eval_union_with_limiters(union, lims, base.kill_radius)
        k1 = kill_margin_primary(union.path_blocks, lims, base.kill_radius)
        k2 = kill_margin_indep(union.path_blocks, lims, base.kill_radius)
        feas2 = k2 > 0.0                                     # hit 는 d <= r_kill
        kill = _compare("kill", k1, k2, k1 > 0.0, feas2, EPS_M)

        v2, boxed2, nf2 = assemble_indep(caught2, feas2 & union.turn_feasible, THETA)
        g1 = int(r1.v_shot_soft >= THETA and not r1.boxed_in)
        g2 = int(v2 >= THETA and not boxed2)
        # 독립 predicate 가 boundary witness 에서 뒤집힐 수 있는 최대량 = flips/nf
        flips = int(kill["n_boundary_mismatch"] + cone["n_boundary_mismatch"])
        v_tol = flips / max(nf2, 1) + EPS_DIMLESS
        thr = {
            "v_primary": float(r1.v_shot_soft), "v_indep": v2,
            "dv": abs(float(r1.v_shot_soft) - v2), "v_tol": v_tol,
            "boxed_agree": bool(r1.boxed_in == boxed2),
            "g_primary": g1, "g_indep": g2,
            "g_agree_or_boundary": bool(
                g1 == g2 or abs(float(r1.v_shot_soft) - THETA) <= v_tol),
            "ok": bool(abs(float(r1.v_shot_soft) - v2) <= v_tol
                       and r1.boxed_in == boxed2
                       and (g1 == g2 or abs(float(r1.v_shot_soft) - THETA) <= v_tol)),
        }
        out["layouts"][name] = {"kill": kill, "threshold": thr,
                                "blocked_frac": float(1.0 - r1.n_feasible
                                                      / max(union.n_total, 1))}
    return out


def _compare(tag, m1, m2, p1, p2, eps):
    """마진 대조 + predicate 대조. 불일치는 |m2| <= eps boundary 에서만 허용."""
    dm = np.abs(m1 - m2)
    mism = p1 != p2
    boundary = np.abs(m2) <= eps
    fatal = mism & ~boundary
    return {
        "check": tag, "n": int(len(m1)),
        "max_dm": float(dm.max()) if len(dm) else 0.0,
        "margin_ok": bool((dm <= eps).all()),
        "n_predicate_mismatch": int(mism.sum()),
        "n_boundary_mismatch": int((mism & boundary).sum()),
        "n_fatal_mismatch": int(fatal.sum()),
    }


def run(episodes, *, stride=25, n=2000, log=print):
    states = collect_states(episodes, stride=stride, log=log)
    base = _base_env(build_m4_env(0, int(episodes[0]), **_world_kw()).env)
    if log:
        log(f"states = {len(states)}")

    agg = {"cone": _agg0(), "kill_hold": _agg0(), "kill_probe": _agg0()}
    thr_bad, fatal_examples = [], []
    for i, s in enumerate(states):
        r = crosscheck_state(base, s, n=n)
        _acc(agg["cone"], r["cone"])
        for name in ("hold", "probe"):
            _acc(agg[f"kill_{name}"], r["layouts"][name]["kill"])
            t = r["layouts"][name]["threshold"]
            if not t["ok"]:
                thr_bad.append(dict(ep=s["ep"], t=s["t"], layout=name, **t))
        for tag, c in [("cone", r["cone"]),
                       ("kill_hold", r["layouts"]["hold"]["kill"]),
                       ("kill_probe", r["layouts"]["probe"]["kill"])]:
            if c["n_fatal_mismatch"] or not c["margin_ok"]:
                fatal_examples.append(dict(ep=s["ep"], t=s["t"], **c))
        if log and (i + 1) % 20 == 0:
            log(f"  {i+1}/{len(states)}", flush=True)

    n_fatal = sum(a["n_fatal_mismatch"] for a in agg.values())
    margin_all_ok = all(a["margin_ok"] for a in agg.values())
    verdict_pass = bool(margin_all_ok and n_fatal == 0 and not thr_bad)
    return dict(
        contract_doc="docs/75 게이트 9 · docs/77 [C] (독립 judge cross-check)",
        eps={"length_m": EPS_M, "dimensionless": EPS_DIMLESS},
        theta=THETA,
        n_states=len(states), episodes=[int(e) for e in episodes], stride=stride,
        checks=agg,
        threshold_failures=thr_bad[:20],
        fatal_examples=fatal_examples[:20],
        n_fatal_total=int(n_fatal),
        verdict=("PASS -- 세 판정 모두 독립 구현과 일치 (boundary 내)" if verdict_pass
                 else "FAIL -- boundary 에서 먼 불일치: 지도 중단·버그 감사 (docs/77 [C])"),
        **stamp(artifact="phase3_judge_crosscheck", lattice_hash=_lattice_hash()))


def _agg0():
    return {"n": 0, "max_dm": 0.0, "margin_ok": True,
            "n_predicate_mismatch": 0, "n_boundary_mismatch": 0,
            "n_fatal_mismatch": 0}


def _acc(a, c):
    a["n"] += c["n"]
    a["max_dm"] = max(a["max_dm"], c["max_dm"])
    a["margin_ok"] = a["margin_ok"] and c["margin_ok"]
    for k in ("n_predicate_mismatch", "n_boundary_mismatch", "n_fatal_mismatch"):
        a[k] += c[k]


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="게이트 9 독립 judge cross-check")
    ap.add_argument("--episodes", type=int, default=10)
    ap.add_argument("--ep0", type=int, default=0)
    ap.add_argument("--stride", type=int, default=25)
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--out", default="results/phase3/judge_crosscheck.json")
    a = ap.parse_args(argv)

    out = run(range(a.ep0, a.ep0 + a.episodes), stride=a.stride, n=a.n)
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    for tag, c in out["checks"].items():
        print(f"[{tag}] n={c['n']} max|m1-m2|={c['max_dm']:.2e} "
              f"mismatch={c['n_predicate_mismatch']} "
              f"(boundary {c['n_boundary_mismatch']} / fatal {c['n_fatal_mismatch']})")
    print(out["verdict"])
    print(f"-> {p}")


if __name__ == "__main__":
    main()
