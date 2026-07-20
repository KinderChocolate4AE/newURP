"""C-1 post-fire deconfliction 3-arm test (docs/09 (zzz); external review §6).

The cheapest fix for the friendly-fire gap ((yyy)): keep the pre-fire CEM
corridor, and after the guard fires switch the limiters from "keep chasing"
(open-loop tail) to a deterministic lane-clear rule. Tests whether that alone
removes the net-lane intersection WITHOUT losing attacker containment.

Note on the model: capture is FROZEN at commit (worst-case at fire), so no
post-fire limiter motion can undo the (already-committed) capture verdict --
deconfliction is "free" w.r.t. the frozen verdict. The physically meaningful
check is therefore (a) does the arm clear the net lane over the deployment
window, and (b) does the attacker stay contained (v_soft high) as the boxers
leave -- a proxy for "would the attacker escape the still-deploying net"
(a true deployment-dynamics model would score this; here it is a diagnostic).

Arms (applied for t >= fire_step): hold (a=0) / radial (perp-away from net
axis) / lateral_behind (perp-away + backward past the finisher).

Envelopes reuse c1_friendly_fire (narrow/nominal/conservative). torch-free.
Usage: python -m shepherd.scripts.c1_deconflict --seed 1100
"""
from __future__ import annotations

import argparse
import json

import numpy as np

from shepherd.scripts.c1_corridor_probe import (ProbeEnv, _load, _seq_lim,
                                                make_finisher_fn, A_MAX, N_LIM)
from shepherd.scripts.c1_friendly_fire import (_cone_perp_clearance,
                                               _tube_clearance)


def _axis_proj(p, apex, u):
    r = np.asarray(p, float) - apex
    return apex + float(r @ u) * u


def make_arm(kind, apex, u):
    """(obs)->[accel3 x N_LIM] deterministic lane-clear rule (obs-only)."""
    def arm(obs, flags):
        o = np.asarray(obs, float)
        acts = []
        for i in range(N_LIM):
            p = o[9 * i:9 * i + 3]
            if kind == "hold":
                acts.append(np.zeros(3, np.float32))
                continue
            perp = p - _axis_proj(p, apex, u)                  # away from axis
            perp = perp / (np.linalg.norm(perp) + 1e-9)
            if kind == "radial":
                d = perp
            elif kind == "lateral_behind":
                d = perp - u                                   # away + backward
                d = d / (np.linalg.norm(d) + 1e-9)
            else:
                raise ValueError(kind)
            acts.append((A_MAX * d).astype(np.float32))
        return acts
    return arm


def _envelopes(E, apex, u, p_att, dt):
    axial_len = float((p_att - apex) @ u)
    net_r = E.net_radius
    half_nom = float(np.arctan2(net_r, max(axial_len, 1e-6)))
    return axial_len, {
        "narrow": {"half": E.cone_half_angle, "tube": 0.0},
        "nominal": {"half": half_nom, "tube": 0.0},
        "conservative": {"half": half_nom, "tube": net_r}}


def _clearance(p, apex, u, env, axial_len):
    cc, _ = _cone_perp_clearance(p, apex, u, env["half"], axial_len)
    tc = _tube_clearance(p, apex, u, env["tube"], axial_len) if env["tube"] > 0 else np.inf
    return min(cc, tc)


def run(cem_json, seed, cfg="configs/m3a_a3e_p1.yaml"):
    env_cfg, m3, theta = _load(cfg)
    dt = float(env_cfg.get("dt", 0.05))
    d = json.load(open(cem_json))
    rec = next(x for x in d["draws"] if x["reset_seed"] == seed and x.get("best_trace"))
    acts_cem = np.asarray(rec["best_trace"]["acts"], float)
    fire = rec["best_record"]["fire_steps"][0]
    pe = ProbeEnv(env_cfg, m3)
    E = pe.ad.env
    n_dep = int(round(E.tau_deploy / dt))

    # geometry frozen at fire (need a first pass to read the fire-state obs)
    base = pe.rollout(_seq_lim(acts_cem), make_finisher_fn(theta), seed, trace=True)
    o_f = np.asarray(base["trace"]["obs"][fire], float)
    apex = o_f[36:39]
    u = o_f[42:45]; u = u / (np.linalg.norm(u) + 1e-12)
    p_att_f = o_f[45:48]
    axial_len, envs = _envelopes(E, apex, u, p_att_f, dt)

    out = {"seed": seed, "fire_step": int(fire), "deploy_steps": n_dep,
           "axial_to_attacker": axial_len, "net_radius": E.net_radius,
           "arms": {}}

    # baseline = original CEM tail (for reference) + 3 deconfliction arms
    arms = {"cem_tail": None, "hold": make_arm("hold", apex, u),
            "radial": make_arm("radial", apex, u),
            "lateral_behind": make_arm("lateral_behind", apex, u)}
    for name, arm_fn in arms.items():
        ad = pe.ad
        obs_d, _ = ad.reset(seed=seed)
        obs = obs_d[ad.limiter_ids[0]]
        fin = make_finisher_fn(theta)
        flags = {}
        clr = {k: np.inf for k in envs}
        vmin = np.inf
        first_cross = {k: None for k in envs}
        risky = {k: None for k in envs}
        t = 0
        while True:
            if name == "cem_tail" or t < fire:
                a = (acts_cem[t] if t < len(acts_cem)
                     else np.zeros((N_LIM, 3)))
                lim = [a[i] for i in range(N_LIM)]
            else:
                lim = arm_fn(obs, flags)
            if t >= fire:                                    # deployment window
                for i in range(N_LIM):
                    p = np.asarray(lim and obs, float)[9 * i:9 * i + 3]
                    for k, e in envs.items():
                        c = _clearance(obs[9 * i:9 * i + 3], apex, u, e, axial_len)
                        if c < clr[k]:
                            clr[k] = c; risky[k] = i
                        if c < 0 and first_cross[k] is None:
                            first_cross[k] = t
                vmin = min(vmin, float(obs[-3]))             # containment proxy
            live = {lid: np.asarray(lim[i], np.float32)
                    for i, lid in enumerate(ad.limiter_ids)}
            live[ad.finisher_id] = np.asarray(fin(obs, flags), np.float32)
            r = ad.step(live)
            obs = r.obs[ad.limiter_ids[0]]; flags = r.flags
            t += 1
            if r.done or t > fire + n_dep:
                break
        out["arms"][name] = {
            "min_clearance": {k: float(clr[k]) for k in envs},
            "intersects": {k: bool(clr[k] < 0) for k in envs},
            "first_cross": {k: first_cross[k] for k in envs},
            "risky_limiter": {k: risky[k] for k in envs},
            "min_v_soft_deploy": float(vmin),   # containment: high = still boxed
            "tags": {k: ("FF_SAFE" if clr[k] >= 0 else "FF_RISK") + "_" + k.upper()
                     for k in envs}}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cem", default="results/c1_corridor/cem_warm/c1_cem.json")
    ap.add_argument("--seed", type=int, default=1100)
    ap.add_argument("--out", default="results/c1_corridor/c1_deconflict.json")
    a = ap.parse_args()
    res = run(a.cem, a.seed)
    import pathlib
    pathlib.Path(a.out).write_text(json.dumps(res, indent=1))
    print(f"seed {res['seed']} fire@{res['fire_step']} axial={res['axial_to_attacker']:.1f}m "
          f"deploy_steps={res['deploy_steps']}")
    print(f"{'arm':<16} {'narrow':>8} {'nominal':>8} {'conserv':>8}  vmin(contain)")
    for name, a2 in res["arms"].items():
        mc = a2["min_clearance"]
        print(f"{name:<16} {mc['narrow']:+8.2f} {mc['nominal']:+8.2f} "
              f"{mc['conservative']:+8.2f}  {a2['min_v_soft_deploy']:.3f}")


if __name__ == "__main__":
    main()
