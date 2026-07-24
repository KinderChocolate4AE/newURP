"""C-1 P2: terminal deployment-safe operating-envelope map (docs/09 (dddd);
external plan deployment_safe_capture_operating_envelope_plan §9-10).

Answers the TERMINAL question (cheaper than full-horizon CEM, plan §9): at a
fixed attacker/finisher fixture, for a grid of (r_kill, r_net_eff), can 4
limiters be PLACED to make the shot eligible (v_soft>=theta AND p_feas>0)
WHILE staying out of the net lane (lateral clearance >= r_net_eff)? This maps
the geometric compatibility of direct crowding-based capture vs friendly
net-clearance, and overlays the analytic boundary eta = r_kill/r_net_eff = 1.

Per grid cell: CEM over 4 limiter positions (around the attacker), evaluating
viability with kill_radius = r_kill (variable), maximizing capture margin
subject to (or penalized by) lane clearance. Records best SAFE capture margin
(clearance>=0) and best UNSAFE, i.e. the capture-clearance Pareto per cell.

Mechanism note (plan §4): capture here is INSTANTANEOUS-geometry dominated
(Case A) -- viability masks the attacker reachable set by the CURRENT limiter
kill-radii; drop-one at the eligible step collapses v_soft (docs/09 (xxx)).
So the analytic necessary condition r_kill >= r_net_eff is tight for this
mechanism. torch-free.
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np

from shepherd.scripts.c1_corridor_probe import _load
from shepherd.game import viability as V

ALPHAS = (0.6, 0.8, 1.0, 1.2, 1.4)
R_KILL0 = 2.0
R_NET0 = 2.24


def _cap_margin(v_soft, p_feas, theta, s_v=0.1, s_p=0.01):
    if v_soft < theta or p_feas <= 0:
        return float("-inf")
    return float(min((v_soft - theta) / s_v, p_feas / s_p))


def eval_placement(lim_pos, fix, E, theta, r_kill, apex, axis, r_net_eff):
    """v_soft/p_feas at a limiter placement (kill_radius=r_kill) + min lateral
    clearance to the net axis."""
    pa = np.asarray(fix["att_p"], float); va = np.asarray(fix["att_v"], float)
    fin = np.asarray(fix["fin"], float)
    kw = E._vshot_kwargs(pa, va, fin)
    r = V.v_shot(pa, va, tau=E.tau_deploy, a_att_max=E.a_att_max,
                 limiters=list(lim_pos), kill_radius=r_kill,
                 n=E.n_samples, seed=1100 * 100003 + 10,
                 n_segments=E.n_segments, **kw)
    mcap = _cap_margin(r.v_shot_soft, r.p_feasible, theta)
    clear = np.inf
    for p in lim_pos:
        rr = np.asarray(p, float) - apex
        ax = float(rr @ axis)
        perp = float(np.linalg.norm(rr - ax * axis))
        clear = min(clear, perp - r_net_eff)
    return mcap, float(clear), float(r.v_shot_soft), float(r.p_feasible)


def cem_cell(fix, E, theta, r_kill, r_net_eff, apex, axis, rng, *,
             pop=60, iters=18, elite=0.25):
    # init from the KNOWN capturing config (seed 1100 boxers, ~5-7 m back from
    # the attacker toward the finisher) + noise -- search whether it can move
    # to clear the lane while staying eligible (NOT around the attacker).
    mu = np.asarray(fix["lim"], float) + rng.normal(0, 0.5, (4, 3))
    sig = np.full((4, 3), 1.5)
    best_safe = {"mcap": -np.inf, "pos": None, "clear": None}
    best_any = {"score": -np.inf, "mcap": -np.inf, "clear": None}
    n_el = max(2, int(pop * elite))
    for _ in range(iters):
        cand = mu + sig * rng.standard_normal((pop, 4, 3))
        scores = np.empty(pop)
        for c in range(pop):
            mcap, clear, vs, pf = eval_placement(cand[c], fix, E, theta,
                                                 r_kill, apex, axis, r_net_eff)
            # lexicographic: safe(clear>=0) & captured ranks top; else push
            # toward capture then toward clearance
            cap_ok = np.isfinite(mcap)
            if cap_ok and clear >= 0 and mcap > best_safe["mcap"]:
                best_safe = {"mcap": float(mcap), "pos": cand[c].tolist(),
                             "clear": float(clear)}
            sc = (100.0 if (cap_ok and clear >= 0) else 0.0) \
                + (mcap if cap_ok else -1.0) + 0.3 * min(clear, 0.0)
            scores[c] = sc
            if sc > best_any["score"]:
                best_any = {"score": float(sc), "mcap": float(mcap),
                            "clear": float(clear)}
        el = np.argsort(scores)[-n_el:]
        mu = cand[el].mean(0); sig = cand[el].std(0) * 1.1 + 0.2
    return {"safe_exists": best_safe["pos"] is not None,
            "best_safe_mcap": (best_safe["mcap"] if best_safe["pos"] else None),
            "best_safe_clear": best_safe["clear"],
            "best_any_mcap": (best_any["mcap"] if np.isfinite(best_any["mcap"]) else None),
            "best_any_clear": best_any["clear"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/m3a_a3e_p1.yaml")
    ap.add_argument("--fixture", default="/tmp/c1_fire_fixture.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_envelope.json")
    ap.add_argument("--pop", type=int, default=60)
    ap.add_argument("--iters", type=int, default=18)
    a = ap.parse_args()
    env_cfg, m3, theta = _load(a.config)
    from shepherd.scripts.c1_corridor_probe import ProbeEnv
    E = ProbeEnv(env_cfg, m3).ad.env
    fix = json.load(open(a.fixture))
    apex = np.asarray(fix["fin"][:3], float)
    axis = np.asarray(fix["fin"][6:9], float); axis /= np.linalg.norm(axis)
    grid = []
    print(f"terminal envelope map: theta={theta} r_kill0={R_KILL0} r_net0={R_NET0} "
          f"(analytic boundary eta=r_kill/r_net_eff=1)")
    print(f"{'ak':>4} {'an':>4} {'r_kill':>6} {'r_neteff':>8} {'eta':>5} "
          f"{'safe?':>5} {'safe_mcap':>9} {'best_clear':>10}")
    for ak in ALPHAS:
        for an in ALPHAS:
            r_kill = R_KILL0 * ak
            r_net_eff = R_NET0 * an
            eta = r_kill / r_net_eff
            rng = np.random.default_rng(350_000 + int(ak * 100) * 1000 + int(an * 100))
            res = cem_cell(fix, E, theta, r_kill, r_net_eff, apex, axis, rng,
                           pop=a.pop, iters=a.iters)
            row = {"alpha_k": ak, "alpha_n": an, "r_kill": r_kill,
                   "r_net_eff": r_net_eff, "eta": eta, **res}
            grid.append(row)
            print(f"{ak:>4} {an:>4} {r_kill:>6.2f} {r_net_eff:>8.2f} {eta:>5.2f} "
                  f"{str(res['safe_exists']):>5} "
                  f"{(res['best_safe_mcap'] if res['best_safe_mcap'] is not None else float('nan')):>9.3f} "
                  f"{res['best_any_clear']:>10.2f}")
    out = {"meta": {"theta": theta, "r_kill0": R_KILL0, "r_net0": R_NET0,
                    "fixture": "seed1100 eligible t=10", "alphas": list(ALPHAS),
                    "analytic_boundary": "eta = r_kill / r_net_eff = 1",
                    "mechanism": "instantaneous-geometry (Case A, docs/09 (xxx) drop-one)",
                    "pop": a.pop, "iters": a.iters},
           "grid": grid,
           "current_point": {"eta": R_KILL0 / R_NET0,
                             "note": "r_body/m_safety excluded; including them lowers eta"}}
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1))
    n_safe = sum(1 for r in grid if r["safe_exists"])
    print(f"\nsafe cells: {n_safe}/{len(grid)}  wrote {a.out}")


if __name__ == "__main__":
    main()
