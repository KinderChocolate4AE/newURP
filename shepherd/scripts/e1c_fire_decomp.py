"""E1c — fire/no-fire 분해 + commit 기하 진단 (**exploratory / post-result**).

증거 등급 (중요)
----------------
E1b(§13) 결과를 **본 뒤** 세운 가설을 보는 것이므로 **exploratory diagnostic** 이다.
여기서 어떤 기전이 강하게 보여도 KSAS 의 confirmatory mechanism claim 으로
**승격하지 않는다** -- "diagnostic suggests ..." 수준으로만 쓰고, 확인이 필요하면
별도 사전등록을 거친다.

왜 (docs/83 §13.4)
------------------
E1b fixed arm: 500 판 중 **발사 117**, 포획 84. 즉 실패의 상당수가 "쐈는데 못 잡음"
이 아니라 **애초에 fire gate 를 통과하지 못함** 이다. 따라서 곡선을 분해해야 한다:

    P(C | a) = P(F | a) * P(C | F, a)

  경우 A  P(F|a) 가 먼저 붕괴      -> commit-eligibility boundary
  경우 B  P(C|F,a) 가 붕괴         -> post-commit net geometry boundary
  경우 C  둘 다                     -> acquisition -> eligibility -> terminal 3 단 병목

commit 기하는 **소각 근사 없이** primitive 로 저장한다 (해석식을 artifact 에 박지
않는다). ax = |r|cos(psi), r_perp = |r|sin(psi) 이므로 r_perp = ax*tan(psi) 가 정확히
성립하고, cone slack = ax*tan(theta) - r_perp 도 exact 다.

★ 판정 원뿔이 보는 것은 발사 시점 거리 d 가 아니라 **예측점의 축방향 좌표 ax** 다
  (표적이 tau 동안 v*tau 만큼 접근하므로 d != ax). 둘 다 저장한다.

    python -m shepherd.scripts.e1c_fire_decomp --n 500 --out results/e1c_fire_decomp.json

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
from shepherd.env_sys import RewardSpec, ratified_system
from shepherd.m4_config import THREAT_BRACKET, m4_config
from shepherd.m4_env import mission_eval
from shepherd.scripts.curve_sweep import band_of, bin_edges
from shepherd.scripts.mobility_factorial import SUCCESS
from shepherd.scripts.slew_audit import aim_geometry
from shepherd.spawn_rand import SpawnSpec
from shepherd.stats import wilson

__all__ = ["episode_row", "run"]


def episode_row(ep_tel: dict, *, tau: float, range_max: float,
                half_angle: float) -> dict:
    """한 에피소드: 발사 여부 + commit 시점 기하 primitive (미발사면 None)."""
    t_fire = ep_tel["fire_step"]
    g = None
    if t_fire is not None:
        for row in ep_tel["rows"]:
            if int(row["t"]) == int(t_fire):
                g = aim_geometry(row["p_att"], row["v_att"], row["p_fin"],
                                 row["e_fin"], tau=tau, range_max=range_max)
                break
    out = {"episode": ep_tel["episode"], "a_att": float(ep_tel["a_att"]),
           "att_speed": float(ep_tel["att_speed"]), "regime": ep_tel["regime"],
           "fired": bool(t_fire is not None), "fire_step": t_fire,
           "captured": bool(ep_tel["label"] in SUCCESS),
           "terminal_label": ep_tel["label"], "steps": ep_tel["steps"],
           "d_at_commit": None, "ax_at_commit": None, "r_perp_at_commit": None,
           "psi_at_commit": None, "cone_slack_at_commit": None}
    if g is not None:
        out.update(d_at_commit=g["d"], ax_at_commit=g["ax"],
                   r_perp_at_commit=g["r_perp"], psi_at_commit=g["psi"],
                   cone_slack_at_commit=g["ax"] * math.tan(half_angle) - g["r_perp"])
    return out


def run(n: int, seed0: int, *, route_gain: float, sense_range: float,
        tau: float, range_max: float, half_angle: float) -> List[dict]:
    tel: List[dict] = []
    mission_eval(seed0, n, limiter_mode="hold", mobility=0.0, omega_max=None,
                 telemetry=tel,
                 system=ratified_system(),
                 reward=RewardSpec(w_kill=0.5, enabled=True),
                 attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0,
                                       route_gain=route_gain, sense_range=sense_range),
                 spawn=SpawnSpec())
    return [episode_row(e, tau=tau, range_max=range_max, half_angle=half_angle)
            for e in tel]


def _stat(vals) -> Optional[dict]:
    v = [x for x in vals if x is not None]
    if not v:
        return None
    a = np.array(v, float)
    return {"n": len(v), "med": float(np.median(a)),
            "p25": float(np.percentile(a, 25)), "p75": float(np.percentile(a, 75))}


def main() -> None:
    ap = argparse.ArgumentParser(
        description="E1c fire/no-fire 분해 + commit 기하 (exploratory)")
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--route-gain", type=float, default=0.5)
    ap.add_argument("--sense-range", type=float, default=30.0)
    ap.add_argument("--out", default="results/e1c_fire_decomp.json")
    a = ap.parse_args()

    cfg = m4_config()
    tau = float(cfg["physics"]["tau_deploy"])
    rmax = float(cfg["viability"]["cone"]["range_max"])
    th = float(cfg["viability"]["cone"]["half_angle"])
    rho = float(cfg["physics"]["net_radius"])
    print(f"[E1c · EXPLORATORY] n={a.n} · T1(route {a.route_gain}, sense {a.sense_range}) "
          f"· omega=2.0 (deployed) · tau {tau} · R_max {rmax} · theta {math.degrees(th):.2f}deg")

    rows = run(a.n, a.seed0, route_gain=a.route_gain, sense_range=a.sense_range,
               tau=tau, range_max=rmax, half_angle=th)
    lo, hi = THREAT_BRACKET["physics.a_att_max"]
    edges = bin_edges(lo, hi, 2.0 * rho / tau ** 2, per_side=4)

    # ── D1/D2: P(F|a) 와 P(C|F,a) ────────────────────────────────────────────
    print(f"\nD1/D2) 분해  P(C|a) = P(F|a) * P(C|F,a)      [a* = {2*rho/tau**2:.2f}]")
    print(f"{'a_att bin':>14} {'n':>4} {'P(F|a)':>16} {'P(C|F,a)':>16} {'P(C|a)':>8}")
    bins = []
    for i in range(len(edges) - 1):
        blo, bhi = edges[i], edges[i + 1]
        sub = [r for r in rows if blo <= r["a_att"] < bhi]
        if not sub:
            continue
        nf = sum(1 for r in sub if r["fired"])
        nc = sum(1 for r in sub if r["captured"])
        pf, pfl, pfh = nf / len(sub), *wilson(nf, len(sub))
        pc_f = (nc / nf) if nf else float("nan")
        cfl, cfh = wilson(nc, nf) if nf else (float("nan"), float("nan"))
        bins.append({"lo": blo, "hi": bhi, "n": len(sub), "n_fired": nf,
                     "n_captured": nc, "p_fire": pf, "p_fire_wilson": [pfl, pfh],
                     "p_capture_given_fire": pc_f,
                     "p_capture_given_fire_wilson": [cfl, cfh],
                     "p_capture": nc / len(sub)})
        print(f"{blo:6.1f}-{bhi:6.1f} {len(sub):4d} "
              f"{pf:6.3f} [{pfl:.3f},{pfh:.3f}] "
              f"{pc_f:6.3f} [{cfl:.3f},{cfh:.3f}] {nc/len(sub):8.3f}")

    # ── D3: 발사한 에피소드의 commit 기하 ────────────────────────────────────
    print(f"\nD3) commit 기하 (발사한 에피소드만; ax = 예측점 축방향 좌표)")
    print(f"{'a_att bin':>14} {'nF':>3} {'d':>16} {'ax':>16} {'r_perp':>16} "
          f"{'cone_slack':>16} {'psi(deg)':>14}")
    for b in bins:
        sub = [r for r in rows if b["lo"] <= r["a_att"] < b["hi"] and r["fired"]]
        if not sub:
            continue
        st = {k: _stat([r[k] for r in sub]) for k in
              ("d_at_commit", "ax_at_commit", "r_perp_at_commit",
               "cone_slack_at_commit", "psi_at_commit")}
        b["commit_geometry"] = st
        f = lambda k, sc=1.0: (f"{st[k]['med']*sc:6.2f}[{st[k]['p25']*sc:5.2f},"
                               f"{st[k]['p75']*sc:5.2f}]" if st[k] else "  --")
        print(f"{b['lo']:6.1f}-{b['hi']:6.1f} {len(sub):3d} "
              f"{f('d_at_commit')} {f('ax_at_commit')} {f('r_perp_at_commit')} "
              f"{f('cone_slack_at_commit')} {f('psi_at_commit', 180/math.pi)}")

    n_fired = sum(1 for r in rows if r["fired"])
    n_cap = sum(1 for r in rows if r["captured"])
    print(f"\n전체: n={len(rows)} · 발사 {n_fired} · 포획 {n_cap} "
          f"· P(C|F)={n_cap/max(n_fired,1):.3f}")
    print(f"공칭 rho={rho} 는 ax=R_max={rmax} 에서만 얻는 값 "
          f"(R_max*tan(theta)={rmax*math.tan(th):.3f})")

    from shepherd.scripts.pivot_manifest import stamp
    out = {"manifest": dict(
               stamp(artifact="e1c_fire_decomp_EXPLORATORY"),
               evidence_grade="EXPLORATORY / post-result diagnostic — "
                              "confirmatory 승격 금지 (docs/83 §13.4)",
               parent_result="results/e1b_aim_diag.json (docs/83 §13, branch B)",
               threat_class="T1", limiter_mode="hold", omega_max="2.0 (deployed)",
               attacker=dict(level="A2", jink_amp=0.6, seed=0,
                             route_gain=a.route_gain, sense_range=a.sense_range),
               n=a.n, seed0=a.seed0, crn_episode_range=[a.seed0, a.seed0 + a.n - 1],
               geometry=dict(rho=rho, tau=tau, cone_range_max=rmax,
                             cone_half_angle=th, kill_radius=cfg["physics"]["kill_radius"],
                             dt=cfg["physics"]["dt"],
                             episode_len=cfg["train"]["episode_len"]),
               note="commit 기하는 primitive 만 저장한다 (해석식 미포함). "
                    "ax = 예측점 축방향 좌표 != d(발사 시점 거리)."),
           "totals": {"n": len(rows), "n_fired": n_fired, "n_captured": n_cap},
           "bins": bins, "records": rows}
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  -> {p}")


if __name__ == "__main__":
    main()
