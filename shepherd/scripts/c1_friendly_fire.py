"""C-1 friendly-fire Tier-1 geometric diagnostic (docs/09 (yyy); external
review §5-8). NOT a gate -- a DIAGNOSTIC TAG. The abstract se3_cone capture
judge ignores whether a friendly limiter sits in the net's deployment path;
this screens winning corridors against 2-3 plausible net-deployment
envelopes and tags them FF_SAFE_* / FF_RISK_*, WITHOUT promoting anything to
an admissibility gate (mission-cost semantics of entanglement = Hyunjun's
decision; see review §9).

Envelopes (cone from finisher apex along n_F toward the attacker-at-fire):
  narrow        half-angle = current cone (surrogate lower bound)
  nominal       half-angle = atan(net_radius / axial_to_attacker) -- a net
                that opens to net_radius at the target range
  conservative  nominal cone UNION a tube of radius net_radius around the
                apex->attacker axis (net edge + tether + body clearance)

Over the deployment window [t_fire, t_fire + round(tau_deploy/dt)] (limiters
keep moving), report per envelope: min friendly clearance (perp distance to
the envelope boundary; <0 = inside), whether any limiter intersects, first
crossing step, and the risky limiter. torch-free.

Usage: python -m shepherd.scripts.c1_friendly_fire --seed 1100
"""
from __future__ import annotations

import argparse
import json

import numpy as np

from shepherd.scripts.c1_corridor_probe import ProbeEnv, _load


def _cone_perp_clearance(p, apex, u, half, axial_len):
    """perp clearance of point p to a cone(apex, axis u, half-angle): >0 outside.
    Only meaningful for 0<=axial<=axial_len; behind apex -> +inf (not swept)."""
    r = np.asarray(p, float) - apex
    ax = float(r @ u)
    if ax < 0 or ax > axial_len:
        return np.inf, ax
    perp = float(np.linalg.norm(r - ax * u))
    return perp - ax * float(np.tan(half)), ax


def _tube_clearance(p, apex, u, R, axial_len):
    r = np.asarray(p, float) - apex
    ax = float(r @ u)
    if ax < 0 or ax > axial_len:
        return np.inf
    perp = float(np.linalg.norm(r - ax * u))
    return perp - R


def screen(cem_json, seed, cfg="configs/m3a_a3e_p1.yaml"):
    env_cfg, m3, theta = _load(cfg)
    pe = ProbeEnv(env_cfg, m3)
    E = pe.ad.env
    dt = float(env_cfg["dt"]) if "dt" in env_cfg else 0.05
    net_r = E.net_radius
    n_dep = int(round(E.tau_deploy / dt))
    d = json.load(open(cem_json))
    r = next(x for x in d["draws"] if x["reset_seed"] == seed and x.get("best_trace"))
    tr = r["best_trace"]
    OBS = np.asarray(tr["obs"], float)
    b = r["best_record"]
    fire = b["fire_steps"][0] if b["fire_steps"] else b.get("first_eligible_step")
    if fire is None:
        return {"seed": seed, "error": "no fire step"}

    o_f = OBS[fire]
    apex = o_f[36:39]
    nF = o_f[42:45]
    nF = nF / (np.linalg.norm(nF) + 1e-12)
    p_att = o_f[45:48]
    axial_len = float((p_att - apex) @ nF)               # apex -> attacker span

    envelopes = {
        "narrow": {"half": E.cone_half_angle, "tube": 0.0},
        "nominal": {"half": float(np.arctan2(net_r, max(axial_len, 1e-6))),
                    "tube": 0.0},
        "conservative": {"half": float(np.arctan2(net_r, max(axial_len, 1e-6))),
                         "tube": net_r},
    }
    win = list(range(fire, min(fire + n_dep + 1, len(OBS))))
    out = {"seed": seed, "fire_step": int(fire), "deploy_steps": n_dep,
           "window": [win[0], win[-1]], "axial_to_attacker": axial_len,
           "net_radius": net_r, "cone_half_deg": float(np.degrees(E.cone_half_angle)),
           "envelopes": {}}
    for name, e in envelopes.items():
        half = e["half"]
        min_clear = np.inf
        first_cross = None
        risky = None
        for t in win:
            o = OBS[t]
            for i in range(4):
                p = o[9 * i:9 * i + 3]
                cc, ax = _cone_perp_clearance(p, apex, nF, half, axial_len)
                tc = (_tube_clearance(p, apex, nF, e["tube"], axial_len)
                      if e["tube"] > 0 else np.inf)
                clear = min(cc, tc)                       # inside cone OR tube
                if clear < min_clear:
                    min_clear = clear
                    risky = i
                if clear < 0 and first_cross is None:
                    first_cross = t
        tag = ("SAFE" if min_clear >= 0 else "RISK")
        out["envelopes"][name] = {
            "half_angle_deg": float(np.degrees(half)), "tube_radius": e["tube"],
            "min_friendly_clearance_m": float(min_clear),
            "intersects": bool(min_clear < 0),
            "first_cross_step": first_cross, "risky_limiter": int(risky),
            "tag": f"FF_{tag}_{name.upper()}"}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cem", default="results/c1_corridor/cem_warm/c1_cem.json")
    ap.add_argument("--seed", type=int, default=1100)
    ap.add_argument("--out", default="results/c1_corridor/c1_friendly_fire.json")
    a = ap.parse_args()
    res = screen(a.cem, a.seed)
    import pathlib
    pathlib.Path(a.out).write_text(json.dumps(res, indent=1))
    print(f"seed {res['seed']} fire@{res['fire_step']} deploy_window={res['window']} "
          f"axial_to_att={res['axial_to_attacker']:.1f}m net_r={res['net_radius']}")
    for name, e in res["envelopes"].items():
        print(f"  {name:<13} half={e['half_angle_deg']:4.1f}deg tube={e['tube_radius']:.1f} "
              f"min_clearance={e['min_friendly_clearance_m']:+.2f}m "
              f"cross@{e['first_cross_step']} L{e['risky_limiter']} -> {e['tag']}")


if __name__ == "__main__":
    main()
