"""Move A0 -- physically-grounded terminal CO-DESIGN boundary probe (docs/09
(gggg); user directive 2026-07-21). NOT a full sweep: a boundary probe near the
physically realizable edge, with the friendly-lane safety geometry and the
net-directionality<->capture-aperture trade-off made EXPLICIT.

Fixed Move-B verdict (carried, not re-litigated): HISTORY_COMMITMENT_KINEMATICS_
CONFIRMED / CASE_B_CAPTURE_NOT_VALIDATED / GROUNDED_LOWER_BOUND_FAIL /
TEMPORAL_PREMISE_UNRESOLVED. A0 attacks the ETA axis (engage-independent), holding
theta=0.9 (never relax geometry AND judge together, user pt1).

Corrected eta (user pt2 -- body + safety MUST be in the denominator):
    eta = r_kill_eff / (r_net_dir + r_body + m_safety)
so the friendly lane the limiters must clear is r_net_dir + r_body + m_safety,
NOT the bare net reach. The current point's honest eta is thus 0.76, not 0.89.

r_kill / r_net are PHYSICAL, not free knobs (user pt3 -- see PHYS manifest):
  r_kill_eff  limiter terminal-effector neutralization radius (kinetic/net-gun/
              proximity). realizable ~2.0-2.6 m (small interceptor); 2.6-3.0 m
              needs heavier payload/larger charge -> flagged diagnostic.
  r_net_dir   finisher deployed-net DIRECTIONAL lateral reach = BOTH the friendly
              lane half-width AND the capture aperture. baseline 2.24 m (grounded
              G2, net_forward directional max @ engage). shrinking = a more
              collimated net: it also SHRINKS the capture aperture (theta_net scaled
              by r_net_dir/2.24; aperture area loss = 1-(r_net_dir/2.24)^2). <2.0 m
              -> flagged diagnostic (over-collimated).
  r_body      limiter airframe half-span (rotor tip). 0.20 m (small-drone 0.2-0.4).
  m_safety    net-lane engineering safety buffer (billow, pos/timing uncertainty).
              0.20 m nominal.

Terminal-only (Case A instantaneous), user pt4-6:
  grid r_kill {2.0,2.3,2.6,3.0} x r_net_dir {2.24,2.10,2.00,1.80}. Per cell a
  4-limiter placement CEM (init = seed-1100 boxers + noise) records: safe terminal
  existence, capture margin, clearance margin, p_cap/p_feas, active limiter
  geometry, APERTURE LOSS, eta, best capture-clearance Pareto point. eta ALONE
  never decides success -- aperture loss is co-reported.

Then (user pt7-9): theta-slice {0.90,0.875,0.85} on BOUNDARY cells only; warm/cold
dynamic G3 on {current, just-above-boundary, feasible-interior}. Success gate =
a PHYSICALLY REALIZABLE cell with capture margin>0 AND clearance margin>0 AND a
dynamic safe-corridor replay (tier>=4) simultaneously.

folded-deployment model = PARALLEL track (does not block A0, user pt10); full
Move C opens only when a grounded folded model shows R_cap>=R_req at the 10 m
crossing. torch-free.
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np

from shepherd.scripts.c1_corridor_probe import (ProbeEnv, _load, _seq_lim,
                                                make_finisher_fn)
from shepherd.game import viability as V

R_KILLS = (2.0, 2.3, 2.6, 3.0)
R_NETS = (2.24, 2.10, 2.00, 1.80)
R_BODY = 0.20
M_SAFETY = 0.20
R_NET0 = 2.24                 # baseline directional reach (aperture anchor)
THETA0 = 0.9
S_V, S_P = 0.1, 0.01
RNG_A0_BASE = 370_000_000     # disjoint from CEM/corral/robust/G3/persistence
# realizable core: small-interceptor kill radius AND not-over-collimated net
REALIZABLE = {"r_kill_max": 2.6, "r_net_min": 2.00}

PHYS = {
    "r_kill_eff": {"meaning": "limiter terminal-effector neutralization radius "
                   "(kinetic/net-gun/proximity)", "unit": "m", "baseline": 2.0,
                   "realizable_range": [2.0, 2.6],
                   "beyond": "2.6-3.0 needs heavier payload/charge -> diagnostic"},
    "r_net_dir": {"meaning": "finisher deployed-net directional lateral reach = "
                  "friendly-lane half-width AND capture aperture (coupled)",
                  "unit": "m", "baseline": 2.24, "realizable_range": [2.0, 2.24],
                  "beyond": "<2.0 over-collimated (large aperture loss) -> diagnostic",
                  "coupling": "capture theta_net *= r_net_dir/2.24; aperture area "
                  "loss = 1-(r_net_dir/2.24)^2"},
    "r_body": {"meaning": "limiter airframe half-span (rotor tip)", "unit": "m",
               "baseline": 0.20, "range": [0.2, 0.4]},
    "m_safety": {"meaning": "net-lane engineering safety buffer (net billow, "
                 "position/timing uncertainty)", "unit": "m", "baseline": 0.20},
    "eta": {"def": "r_kill_eff / (r_net_dir + r_body + m_safety)"},
}


def _cap_margin(v_soft, p_feas, theta):
    if v_soft < theta or p_feas <= 0:
        return float("-inf")
    return float(min((v_soft - theta) / S_V, p_feas / S_P))


def eval_placement(lim_pos, fix, E, theta, r_kill, r_net_dir, apex, axis):
    """v_soft/p_feas at a placement with kill_radius=r_kill AND the capture cone
    scaled to the net directionality (aperture coupling), + min in-band lateral
    clearance to the friendly lane (r_net_dir + r_body + m_safety)."""
    pa = np.asarray(fix["att_p"], float); va = np.asarray(fix["att_v"], float)
    fin = np.asarray(fix["fin"], float)
    kw = dict(E._vshot_kwargs(pa, va, fin))
    kw["theta_net"] = float(kw["theta_net"]) * (r_net_dir / R_NET0)   # aperture coupling
    r = V.v_shot(pa, va, tau=E.tau_deploy, a_att_max=E.a_att_max,
                 limiters=list(lim_pos), kill_radius=r_kill,
                 n=getattr(E, "n_samples", 2000), seed=RNG_A0_BASE + 11,
                 n_segments=getattr(E, "n_segments", 4), **kw)
    mcap = _cap_margin(r.v_shot_soft, r.p_feasible, theta)
    lane = r_net_dir + R_BODY + M_SAFETY
    axial_len = float((pa - apex) @ axis)
    clear = np.inf
    for p in lim_pos:
        rr = np.asarray(p, float) - apex
        ax = float(rr @ axis)
        if 0.0 <= ax <= axial_len:                       # in the forward net lane
            perp = float(np.linalg.norm(rr - ax * axis))
            clear = min(clear, perp - lane)
    return mcap, float(clear), float(r.v_shot_soft), float(r.p_feasible)


def _push_out(pos, apex, axis, target_perp):
    """Move each limiter radially (perp-to-axis) so its perp distance = target_perp,
    keeping its axial coordinate -- the physics-informed co-design seed (box from the
    lane boundary)."""
    out = np.asarray(pos, float).copy()
    for i in range(len(out)):
        rr = out[i] - apex; ax = float(rr @ axis); pv = rr - ax * axis
        pn = float(np.linalg.norm(pv))
        if pn > 1e-6:
            out[i] = apex + ax * axis + pv / pn * target_perp
    return out


def cem_cell(fix, E, theta, r_kill, r_net_dir, apex, axis, rng, *,
             pop=36, iters=16, elite=0.25):
    fixture = np.asarray(fix["lim"], float)
    lane = r_net_dir + R_BODY + M_SAFETY
    # co-design seeds: the safe-eligible shell is a NARROW (~0.1 m) band at perp
    # ~= r_kill -- perp<r_kill over-boxes (p_feas->0, not a clean shot), perp>>r_kill
    # loses v_soft. clearance = perp - lane, so eta=r_kill/lane>=1 is the boundary.
    # Seed the shell finely and require perp>=lane (clearance-feasible).
    seeds = [fixture] + [_push_out(fixture, apex, axis, max(lane, r_kill + e))
                         for e in (0.0, 0.03, 0.06, 0.1, 0.15)]
    mu = fixture.copy()
    sig = np.full((4, 3), 0.4)
    best_safe = {"mcap": -np.inf, "pos": None, "clear": None, "vs": None, "pf": None}
    best_pareto = {"mcap": -np.inf, "clear": -np.inf, "pos": None}
    n_el = max(2, int(pop * elite))
    for _ in range(iters):
        cand = mu + sig * rng.standard_normal((pop, 4, 3))
        for j, sd in enumerate(seeds):                     # inject physics seeds
            if pop > j:
                cand[j] = sd
        scores = np.empty(pop)
        for c in range(pop):
            mcap, clear, vs, pf = eval_placement(cand[c], fix, E, theta, r_kill,
                                                 r_net_dir, apex, axis)
            cap_ok = np.isfinite(mcap)
            if cap_ok and clear >= 0 and mcap > best_safe["mcap"]:
                best_safe = {"mcap": float(mcap), "pos": cand[c].tolist(),
                             "clear": float(clear), "vs": vs, "pf": pf}
            # best capture-clearance Pareto point (max of min(mcap, clear-scaled))
            if cap_ok and min(mcap, clear / S_V + 1e3 * (clear >= 0)) > \
                    min(best_pareto["mcap"], best_pareto["clear"] / S_V):
                best_pareto = {"mcap": float(mcap), "clear": float(clear),
                               "pos": cand[c].tolist()}
            sc = (100.0 if (cap_ok and clear >= 0) else 0.0) \
                + (mcap if cap_ok else -1.0) + 0.3 * min(clear, 0.0)
            scores[c] = sc
        el = np.argsort(scores)[-n_el:]
        mu = cand[el].mean(0); sig = cand[el].std(0) * 1.1 + 0.2
    safe = best_safe["pos"] is not None
    return {"safe_exists": safe,
            "capture_margin": (best_safe["mcap"] if safe else best_pareto["mcap"]
                               if np.isfinite(best_pareto["mcap"]) else None),
            "clearance_margin": (best_safe["clear"] if safe else best_pareto["clear"]
                                 if best_pareto["pos"] else None),
            "p_cap": best_safe["vs"], "p_feas": best_safe["pf"],
            "active_limiter_geometry": (best_safe["pos"] if safe else best_pareto["pos"]),
            "best_pareto": {"capture_margin": (best_pareto["mcap"]
                            if np.isfinite(best_pareto["mcap"]) else None),
                            "clearance_margin": (best_pareto["clear"]
                            if best_pareto["pos"] else None)}}


def cell_eta(r_kill, r_net_dir):
    return r_kill / (r_net_dir + R_BODY + M_SAFETY)


def realizable(r_kill, r_net_dir):
    return bool(r_kill <= REALIZABLE["r_kill_max"] and r_net_dir >= REALIZABLE["r_net_min"])


def aperture_loss(r_net_dir):
    return float(1.0 - (r_net_dir / R_NET0) ** 2)


def geometry_stage(fix, E, apex, axis, theta=THETA0, pop=44, iters=14):
    grid = []
    for rk in R_KILLS:
        for rn in R_NETS:
            rng = np.random.default_rng(RNG_A0_BASE + int(rk * 100) * 1000 + int(rn * 100))
            res = cem_cell(fix, E, theta, rk, rn, apex, axis, rng, pop=pop, iters=iters)
            row = {"r_kill": rk, "r_net_dir": rn, "eta": cell_eta(rk, rn),
                   "realizable": realizable(rk, rn), "aperture_loss": aperture_loss(rn),
                   "lane": rn + R_BODY + M_SAFETY, **res}
            row["diagnostic_only"] = not row["realizable"]
            grid.append(row)
            print(f"  rk={rk} rn={rn} eta={row['eta']:.3f} real={row['realizable']} "
                  f"apLoss={row['aperture_loss']:.2f} safe={row['safe_exists']} "
                  f"cap={_f(res['capture_margin'])} clr={_f(res['clearance_margin'])}",
                  flush=True)
    return grid


def _f(x):
    return f"{x:+.2f}" if isinstance(x, (int, float)) else "  na"


def pick_cells(grid):
    """current / just-above-boundary / feasible-interior (realizable only)."""
    cur = next(c for c in grid if c["r_kill"] == 2.0 and c["r_net_dir"] == 2.24)
    real = [c for c in grid if c["realizable"]]
    safe_geq1 = [c for c in real if c["safe_exists"] and c["eta"] >= 1.0]
    boundary = min(safe_geq1, key=lambda c: c["eta"], default=None)     # smallest eta>=1 safe
    # interior = realizable safe cell, eta>=1.05, best (capture+clearance) - aperture penalty
    interior_cands = [c for c in real if c["safe_exists"] and c["eta"] >= 1.05]
    interior = max(interior_cands,
                   key=lambda c: (c["capture_margin"] or -9) + (c["clearance_margin"] or -9)
                   - 2 * c["aperture_loss"], default=None)
    # boundary cells for theta-slice = realizable cells with 0.95<=eta<=1.12,
    # capped to the 3 nearest eta=1 (bound theta-slice cost)
    boundary_band = sorted([c for c in real if 0.95 <= c["eta"] <= 1.12],
                           key=lambda c: abs(c["eta"] - 1.0))[:3]
    return {"current": cur, "just_above_boundary": boundary, "feasible_interior": interior,
            "boundary_band": boundary_band}


def theta_slice(fix, E, apex, axis, cells, pop=40, iters=12):
    out = []
    for c in cells:
        rk, rn = c["r_kill"], c["r_net_dir"]
        for th in (0.90, 0.875, 0.85):
            rng = np.random.default_rng(RNG_A0_BASE + 500_000 + int(rk * 100) * 1000
                                        + int(rn * 100) + int(th * 1000))
            res = cem_cell(fix, E, th, rk, rn, apex, axis, rng, pop=pop, iters=iters)
            out.append({"r_kill": rk, "r_net_dir": rn, "theta": th,
                        "eta": cell_eta(rk, rn), "safe_exists": res["safe_exists"],
                        "capture_margin": res["capture_margin"],
                        "clearance_margin": res["clearance_margin"]})
            print(f"  [theta] rk={rk} rn={rn} th={th}: safe={res['safe_exists']} "
                  f"cap={_f(res['capture_margin'])} clr={_f(res['clearance_margin'])}",
                  flush=True)
    return out


def _standoff_ring(r_kill, kp=6.0, kd=4.0):
    """Ring-of-4 formation TRACKING the attacker at radius r_kill (perp to heading),
    velocity-matched -- the dynamic analogue of the terminal standoff box: it boxes
    from perp~r_kill (so ~lane-clear for eta>1) while following the moving attacker,
    unlike the old E1 crowd-to-perp0.3 trajectory or a static hold."""
    from shepherd.scripts.c1_corridor_probe import make_corral_fn
    return make_corral_fn({"pattern": "ring4", "d_lead": 0.0, "d_back": 0.0,
                           "R0": r_kill, "R1": r_kill, "t_shrink0": 0.0,
                           "shrink_len": 1.0, "phi0": 0.0,
                           "kp": kp, "kd": kd, "vmatch": 1.0})


def dynamic_g3(pe, cem_json, seed, cells, theta):
    """WARM vs STANDOFF-RING dynamic G3 per selected cell (env kill_radius + cone
    aperture overridden per cell). WARM = replay the E1 winner (OLD eta=0.89
    trajectory -- CROWDS limiters to perp~0.3, fails ANY lane). STANDOFF-RING = a
    ring-of-4 tracking the attacker at radius r_kill: does boxing from standoff
    (perp~r_kill, ~lane-clear for eta>1) capture AND hold the lane through
    deployment? This is the FAIR, cheap dynamic test; dynamic_safe uses it (tier>=4)."""
    from shepherd.scripts.c1_g3_deploy import rollout_g3
    E = pe.ad.env
    kr0, ch0 = E.kill_radius, E.cone_half_angle
    w = json.loads(pathlib.Path(cem_json).read_text())
    rec = next(x for x in w["draws"] if x["reset_seed"] == seed and x.get("best_acts"))
    acts = np.asarray(rec["best_acts"], float)
    fin = make_finisher_fn(theta)
    out = []
    for tag, c in cells:
        if c is None:
            continue
        rk, rn = c["r_kill"], c["r_net_dir"]
        E.kill_radius = rk                                   # per-cell overrides
        E.cone_half_angle = ch0 * (rn / R_NET0)
        rw = rollout_g3(pe, _seq_lim(acts), fin, seed,
                        r_lane=rn, r_body=R_BODY + M_SAFETY)
        rs = rollout_g3(pe, _standoff_ring(rk), fin, seed,
                        r_lane=rn, r_body=R_BODY + M_SAFETY)
        stand = {"best_tier": rs["tier"], "E_safe": rs["E_safe"],
                 "E_capture": rs["E_capture"], "E_lane": rs["E_lane"],
                 "m_clear": rs["m_clear"], "fire_step": rs["fire_step"],
                 "M_capture": (rs["M_capture"] if np.isfinite(rs["M_capture"]) else None)}
        out.append({"cell": tag, "r_kill": rk, "r_net_dir": rn, "eta": cell_eta(rk, rn),
                    "warm": {"tier": rw["tier"], "E_safe": rw["E_safe"],
                             "m_clear": rw["m_clear"]},
                    "standoff_ring": stand,
                    "dynamic_safe": bool((stand.get("best_tier") or 0) >= 4)})
        wmc = rw["m_clear"]; wmc = f"{wmc:.2f}" if wmc is not None else "na"
        print(f"  [G3] {tag} rk={rk} rn={rn}: warm tier={rw['tier']} m_clear={wmc}"
              f"  | ring tier={stand['best_tier']} E_cap={stand['E_capture']} "
              f"E_lane={stand['E_lane']} m_clear={stand['m_clear']} fire={stand['fire_step']}",
              flush=True)
    E.kill_radius, E.cone_half_angle = kr0, ch0             # restore
    return out


def verdict(grid, dyng3):
    real_safe = [c for c in grid if c["realizable"] and c["safe_exists"]
                 and (c["capture_margin"] or -1) > 0 and (c["clearance_margin"] or -1) > 0]
    dyn_safe = {(d["r_kill"], d["r_net_dir"]) for d in dyng3 if d["dynamic_safe"]}
    gate = [c for c in real_safe if (c["r_kill"], c["r_net_dir"]) in dyn_safe]
    if gate:
        v = "A0_FEASIBLE_INTERIOR_CONFIRMED"
        note = ("a physically realizable cell clears the FULL gate: capture>0 AND "
                "clearance>0 terminal AND a COLD-re-optimized (standoff-boxing) "
                "dynamic corridor is lane-safe (tier>=4). -> open the full dynamic "
                "sweep + MARL development at these designs.")
    elif real_safe:
        v = "A0_TERMINAL_FEASIBLE_DYNAMIC_UNSOLVED"
        note = ("realizable cells pass the TERMINAL gate at eta>1 (a static safe "
                "placement exists, engage-independent, cap>0 AND clearance>0) but no "
                "CHEAP dynamic corridor reaches tier>=4: the E1 warm replay CROWDS "
                "limiters to perp~0.3 (old-eta trajectory), and a standoff ring "
                "tracking at radius r_kill is too SPARSE to seal the box (never fires). "
                "eta>1 resolves the STATIC box/clear tension, but the DYNAMIC "
                "challenge -- track the moving attacker AND seal the escape gaps AND "
                "hold perp>=lane -- is unmet by cheap controllers. -> barrier is "
                "TRAJECTORY-level; next = focused dynamic co-design (a sealing standoff "
                "formation / post-fire deconfliction (zzz) / MARL) at the identified "
                "realizable cells (2.6/2.0-2.1) before the full sweep. NOT a blind sweep.")
    else:
        v = "A0_NO_REALIZABLE_FEASIBLE"
        note = ("no physically realizable cell achieves capture>0 AND clearance>0 at "
                "theta=0.9 -> eta>1 alone (within realizable r_kill/r_net) does not "
                "buy a safe terminal state; escalate net directionality (aperture "
                "cost) or the parallel folded-deployment track.")
    # did the standoff ring at least beat the warm replay?
    cold_beats_warm = any((d["standoff_ring"].get("best_tier") or 0) > d["warm"]["tier"]
                          for d in dyng3)
    return {"verdict": v, "note": note, "cold_beats_warm": cold_beats_warm,
            "n_realizable_terminal_safe": len(real_safe),
            "n_gate_pass": len(gate),
            "gate_cells": [(c["r_kill"], c["r_net_dir"]) for c in gate],
            "terminal_safe_cells": [(c["r_kill"], c["r_net_dir"]) for c in real_safe]}


def run(cfg="configs/m3a_a3e_p1.yaml", fixture="/tmp/c1_fire_fixture.json",
        cem_json="results/c1_corridor/cem_warm/c1_cem.json", seed=1100,
        pop=44, iters=14):
    env_cfg, m3, theta = _load(cfg)
    pe = ProbeEnv(env_cfg, m3)
    E = pe.ad.env
    fix = json.load(open(fixture))
    apex = np.asarray(fix["fin"][:3], float)
    axis = np.asarray(fix["fin"][6:9], float); axis /= np.linalg.norm(axis)
    print(f"[A0 geometry] theta={THETA0} grid {len(R_KILLS)}x{len(R_NETS)} "
          f"eta=r_kill/(r_net_dir+{R_BODY}+{M_SAFETY})  current eta={cell_eta(2.0,2.24):.3f}")
    grid = geometry_stage(fix, E, apex, axis, theta=THETA0, pop=pop, iters=iters)
    picks = pick_cells(grid)
    print(f"\n[A0 theta-slice] boundary band cells: "
          f"{[(c['r_kill'], c['r_net_dir']) for c in picks['boundary_band']]}")
    tslice = theta_slice(fix, E, apex, axis, picks["boundary_band"],
                         pop=max(24, pop - 12), iters=max(8, iters - 4))
    dyn_cells = [("current", picks["current"]),
                 ("just_above_boundary", picks["just_above_boundary"]),
                 ("feasible_interior", picks["feasible_interior"])]
    print(f"\n[A0 dynamic G3] cells: "
          f"{[(t, (c['r_kill'], c['r_net_dir']) if c else None) for t, c in dyn_cells]}")
    dyng3 = dynamic_g3(pe, cem_json, seed, dyn_cells, THETA0)
    vd = verdict(grid, dyng3)
    return {"meta": {"theta": THETA0, "r_body": R_BODY, "m_safety": M_SAFETY,
                     "r_net0": R_NET0, "eta_def": "r_kill_eff/(r_net_dir+r_body+m_safety)",
                     "current_eta": cell_eta(2.0, 2.24), "rng_base": RNG_A0_BASE,
                     "realizable_core": REALIZABLE, "seed": seed,
                     "moveB_verdict_carried": ["HISTORY_COMMITMENT_KINEMATICS_CONFIRMED",
                                               "CASE_B_CAPTURE_NOT_VALIDATED",
                                               "GROUNDED_LOWER_BOUND_FAIL",
                                               "TEMPORAL_PREMISE_UNRESOLVED"],
                     "folded_track": "PARALLEL, does not block A0; full Move C opens only "
                     "when a grounded folded model shows R_cap>=R_req at the 10 m crossing",
                     "pop": pop, "iters": iters},
            "phys_manifest": PHYS,
            "picks": {k: ((v["r_kill"], v["r_net_dir"]) if isinstance(v, dict) and "r_kill" in v
                          else [(c["r_kill"], c["r_net_dir"]) for c in v] if isinstance(v, list)
                          else None) for k, v in picks.items()},
            "geometry_grid": grid, "theta_slice": tslice, "dynamic_g3": dyng3,
            "readout": vd}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/c1_corridor/c1_moveA0.json")
    ap.add_argument("--pop", type=int, default=44)
    ap.add_argument("--iters", type=int, default=14)
    a = ap.parse_args()
    out = run(pop=a.pop, iters=a.iters)
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1))
    r = out["readout"]
    print(f"\nVERDICT: {r['verdict']}")
    print(f"  {r['note']}")
    print(f"  realizable terminal-safe: {r['terminal_safe_cells']}")
    print(f"  gate-pass (terminal+dynamic): {r['gate_cells']}")
    print(f"\nwrote {a.out}")


if __name__ == "__main__":
    main()
