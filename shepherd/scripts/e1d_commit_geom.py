"""E1d — commit geometry intervention (docs/83 §15 동결 프로토콜).

성격 (§15 머리)
--------------
"forced early fire" 가 **아니다**. `ax` 만의 순수 causal intervention 도 아니다.
정확히는 **ax-targeted commit-timing intervention** 이고, **terminal geometry
mechanism-isolation experiment** 이지 controller performance 실험이 아니다.
이 라벨을 결과 보고에도 유지한다.

질문
----
  Does moving the forced commit to a larger realized axial footprint shift the
  net-capture boundary as predicted by local cone geometry?

동기: a >= 32.2 에서 P(C|F,a) 를 관측할 수 없어(발사 0/350) "net 물리상 실패" 와
"controller 의 보수적 거절" 을 분리하지 못한다 (§14.6).

two-pass replay (§15.3)
-----------------------
  Pass 1  fire 없이 롤아웃 · 스텝별 기하 저장 -> target ax 에 가장 가까운 스텝 선택
          (|ax - target| 최소, 동률이면 이른 스텝. 밴드 밖 스텝은 후보 제외)
  Pass 2  동일 seed/CRN 재생 · **사전 선택된 그 스텝에서만** force commit
  Pass 1 은 target 과 무관하므로 **세 팔이 공유**한다.

팔 (§15.4)
---------
  D-a  ax 6.5, ideal aim (psi=0)     현 운용점 근처 기준
  D-b  ax 8.0, ideal aim             larger-footprint 반사실
  D-c  ax 8.0, actual aim, omega=inf slew cap 제거 후에도 남는 pointing 비용

예측 (§15.5, 결과 전 동결)
  Primary(방향성): a*_50(D-b) > a*_50(D-a)
  Reference benchmark(pass/fail 아님): 2*ax_realized*tan(theta)/tau^2
  보고 의무: **realized ax 분포**로 분석 (nominal target 아님) + psi_at_commit 병기

    python -m shepherd.scripts.e1d_commit_geom --n 300 --out results/e1d.json

torch-free.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
from typing import List, Optional

import numpy as np

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.agents.mobile_finisher import SLEW_UNLIMITED, apply_slew_limit
from shepherd.env_sys import RewardSpec, ratified_system
from shepherd.m4_config import m4_config
from shepherd.m4_env import build_m4_env
from shepherd.scripts.curve_sweep import _cross50, bin_edges
from shepherd.scripts.recoverability_probe import _Driver
from shepherd.scripts.slew_audit import aim_geometry
from shepherd.spawn_rand import SpawnSpec
from shepherd.stats import wilson

__all__ = ["reference_pass", "forced_pass", "ARMS"]

#: (이름, target ax, ideal aim, omega override)
ARMS = (("D-a", 6.5, True, None),
        ("D-b", 8.0, True, None),
        ("D-c", 8.0, False, SLEW_UNLIMITED))


def _build(ep: int, *, force_step: Optional[int] = None, ideal: bool = False,
           omega: Optional[float] = None):
    st = build_m4_env(
        0, ep,
        system=ratified_system(force_commit_step=force_step,
                               perfect_aim_at_commit=bool(ideal)),
        reward=RewardSpec(w_kill=0.5, enabled=True),
        attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0,
                              route_gain=0.5, sense_range=30.0),
        spawn=SpawnSpec())
    if omega is not None:
        apply_slew_limit(st.env, omega)
    return st


def reference_pass(ep: int, tau: float, rmax: float) -> dict:
    """Pass 1 — 발사 없이 굴리며 스텝별 ax 기록 (팔 간 공유)."""
    st = _build(ep)
    env, scn, lay = st.env, st.scn, st.lay
    d = _Driver(env, scn, lay, ep)
    d.fire_mode = "never"
    rows = []
    for t in range(int(lay.episode_len)):
        lims, fin, att = env._states()
        g = aim_geometry(env._p(att), env._v(att), env._p(fin), env._e(fin),
                         tau=tau, range_max=rmax)
        if g is not None:
            rows.append({"t": t, "ax": g["ax"], "in_band": g["in_band"]})
        d.step(limiter_mode="hold", baseline_commit=False)
        if d.done:
            break
    return {"episode": ep, "rows": rows,
            "a_att": float(env.a_att_max), "att_speed": float(env.v_nominal)}


def _select_step(ref: dict, target: float) -> Optional[int]:
    """|ax - target| 최소, 동률이면 이른 스텝. 밴드 밖은 후보 제외 (§15.3)."""
    cand = [r for r in ref["rows"] if r["in_band"]]
    if not cand:
        return None
    best = min(cand, key=lambda r: (abs(r["ax"] - target), r["t"]))
    return int(best["t"])


def forced_pass(ep: int, step: int, *, ideal: bool, omega: Optional[float],
                tau: float, rmax: float) -> dict:
    """Pass 2 — 동일 CRN 재생 + 사전 선택 스텝에서 강제 커밋."""
    # ★ env_sys.force_commit_step 은 _step_i 규약 (1-based). 여기 `step` 은
    #   reference pass 의 0-based t 이므로 +1 로 변환한다 (회귀 D-B/D-C).
    st = _build(ep, force_step=step + 1, ideal=ideal, omega=omega)
    env, scn, lay = st.env, st.scn, st.lay
    d = _Driver(env, scn, lay, ep)
    d.fire_mode = "never"                 # 게이트 우회가 유일한 발사 경로
    ax_r = psi_r = None
    fired = False
    for t in range(int(lay.episode_len)):
        lims, fin, att = env._states()
        if t == step:                     # 개입 **직전** 기하 (perfect aim 적용 전)
            g = aim_geometry(env._p(att), env._v(att), env._p(fin), env._e(fin),
                             tau=tau, range_max=rmax)
            if g is not None:
                ax_r, psi_r = g["ax"], g["psi"]
        fi = d.step(limiter_mode="hold", baseline_commit=False)
        if fi.get("forced_commit"):
            fired = True
            if ideal:                     # perfect aim 이면 판정 psi = 0
                psi_r = 0.0
        if d.done:
            break
    return {"episode": ep, "step": step, "label": d.label, "fired": fired,
            "ax_realized": None if ax_r is None else round(float(ax_r), 4),
            "psi_at_commit": None if psi_r is None else round(float(psi_r), 5),
            "captured": d.label in ("CAPTURED", "NET_CAPTURE",
                                    "CAPTURE_WITH_CONTACT")}


def main() -> None:
    ap = argparse.ArgumentParser(description="E1d commit geometry (docs/83 §15)")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--out", default="results/e1d.json")
    a = ap.parse_args()
    cfg = m4_config()
    tau = float(cfg["physics"]["tau_deploy"])
    rmax = float(cfg["viability"]["cone"]["range_max"])
    th = float(cfg["viability"]["cone"]["half_angle"])
    rho = float(cfg["physics"]["net_radius"])
    print(f"[E1d · docs/83 §15] n={a.n} · tau {tau} · R_max {rmax} · "
          f"theta {math.degrees(th):.2f}deg · arms {[x[0] for x in ARMS]}", flush=True)

    import time
    t0 = time.time()
    refs, sel = [], {}
    for ep in range(a.n):
        r = reference_pass(ep, tau, rmax)
        refs.append(r)
        sel[ep] = {nm: _select_step(r, tgt) for nm, tgt, _, _ in ARMS}
        if (ep + 1) % 50 == 0 or ep + 1 == a.n:
            el = time.time() - t0
            print(f"    [pass1] {ep+1}/{a.n}  {el:6.1f}s "
                  f"(ETA {el/(ep+1)*(a.n-ep-1):5.0f}s)", flush=True)

    edges = bin_edges(11.0, 78.0, 2 * rho / tau ** 2, per_side=4)
    arms = {}
    for nm, tgt, ideal, om in ARMS:
        rows, t1 = [], time.time()
        for ep in range(a.n):
            s = sel[ep][nm]
            if s is None:
                rows.append({"episode": ep, "step": None, "excluded": True})
                continue
            r = forced_pass(ep, s, ideal=ideal, omega=om, tau=tau, rmax=rmax)
            r["a_att"] = refs[ep]["a_att"]; r["att_speed"] = refs[ep]["att_speed"]
            r["excluded"] = False
            rows.append(r)
            if (ep + 1) % 50 == 0 or ep + 1 == a.n:
                el = time.time() - t1
                print(f"    [{nm}] {ep+1}/{a.n}  {el:6.1f}s "
                      f"(ETA {el/(ep+1)*(a.n-ep-1):5.0f}s)", flush=True)
        ok = [r for r in rows if not r["excluded"]]
        axs = np.array([r["ax_realized"] for r in ok if r["ax_realized"] is not None])
        psis = np.array([r["psi_at_commit"] for r in ok
                         if r["psi_at_commit"] is not None])
        # 포획 확률 곡선 -> 50% 교차 (동일 estimator 재사용)
        xs, ps, ns = [], [], []
        for i in range(len(edges) - 1):
            lo, hi = edges[i], edges[i + 1]
            sub = [r for r in ok if lo <= r["a_att"] < hi]
            if not sub:
                continue
            xs.append(0.5 * (lo + hi)); ns.append(len(sub))
            ps.append(sum(1 for r in sub if r["captured"]) / len(sub))
        k = sum(1 for r in ok if r["captured"])
        arms[nm] = {"target_ax": tgt, "ideal_aim": ideal, "omega": om,
                    "n": len(ok), "n_excluded": len(rows) - len(ok),
                    "n_fired": sum(1 for r in ok if r["fired"]),
                    "p_capture": k / max(len(ok), 1),
                    "p_capture_wilson": list(wilson(k, max(len(ok), 1))),
                    "ax_realized": {"med": float(np.median(axs)) if axs.size else None,
                                    "p25": float(np.percentile(axs, 25)) if axs.size else None,
                                    "p75": float(np.percentile(axs, 75)) if axs.size else None},
                    "psi_at_commit_deg": {
                        "med": float(np.degrees(np.median(psis))) if psis.size else None},
                    "cross50": _cross50(xs, ps), "bins": xs, "p": ps, "n_per_bin": ns,
                    "reference_benchmark": (2 * float(np.median(axs)) * math.tan(th)
                                            / tau ** 2) if axs.size else None,
                    "records": rows}
        A = arms[nm]
        print(f"\n  {nm} (target ax {tgt}, ideal_aim {ideal}, omega {om}): "
              f"n={A['n']} 제외 {A['n_excluded']} 발사 {A['n_fired']}")
        print(f"    ax_realized med {A['ax_realized']['med']} "
              f"[{A['ax_realized']['p25']}, {A['ax_realized']['p75']}] · "
              f"psi_at_commit med {A['psi_at_commit_deg']['med']} deg")
        print(f"    P(capture) {A['p_capture']:.3f} · **cross50 {A['cross50']:.2f}** · "
              f"reference benchmark {A['reference_benchmark']:.2f}", flush=True)

    from shepherd.scripts.pivot_manifest import stamp
    out = {"manifest": dict(
               stamp(artifact="e1d_commit_geom"), prereg_doc="docs/83 §15 (E1d)",
               label="ax-targeted commit-timing intervention; terminal geometry "
                     "MECHANISM-ISOLATION experiment (not controller performance)",
               caveat="perfect-aim 은 실현 불가능한 반사실이다. D-b 의 높은 포획률을 "
                      "'시스템 성능' 으로 읽지 않는다. ax 가 유일 원인이라고 쓰지 않는다.",
               primary="방향성 a*_50(D-b) > a*_50(D-a); reference benchmark 는 "
                       "pass/fail 기준이 아니다",
               n=a.n, world="ratified + T1 + hold + fire only via forced commit"),
           "arms": {k: {kk: vv for kk, vv in v.items() if kk != "records"}
                    for k, v in arms.items()},
           "records": {k: v["records"] for k, v in arms.items()}}
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n  -> {p}", flush=True)


if __name__ == "__main__":
    main()
