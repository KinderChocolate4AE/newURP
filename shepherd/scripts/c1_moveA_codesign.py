"""Move A -- net/kill-radius CO-DESIGN for eta = r_kill / r_net_eff > 1
(docs/09 (ffff); the engage-INDEPENDENT branch of the (eeee) fork). Held in
parallel to N1 temporal per the user directive: this file ships ONLY the static
eta calculation + the full-sweep SKELETON. The full sweep is GATED behind
--run-full and currently raises (deliberately held) -- do not run it until the
N1-temporal verdict says Move A is primary.

Context (docs/09 (dddd) operating envelope): deployment-safe capture needs the
design INSIDE a 2-factor region eta>1 AND capture-quality theta relaxed. The
current grounded point sits OUTSIDE on both axes. Move A attacks the eta axis:
raise r_kill (stronger/longer kill radius) and/or LOWER r_net_eff (a more
directional / tighter net) so the kill mechanism out-reaches the friendly net
lane. Unlike Move C, this does NOT depend on the unvalidated pre-engage net reach.
"""
from __future__ import annotations

import argparse
import json
import pathlib

# grounded current point (docs/09 (aaaa)/(cccc)/(dddd))
R_KILL_NOW = 2.0            # env kill_radius
R_NET_EFF_NOW = 2.24       # grounded directional net lane reach (G2)
THETA_NOW = 0.9            # current capture-quality bar


def static_eta():
    """Static eta = r_kill/r_net_eff at the current grounded point + the minimal
    single-axis design deltas that reach the analytic boundary eta=1."""
    eta = R_KILL_NOW / R_NET_EFF_NOW
    # to reach eta>=1 by moving ONE axis:
    r_kill_needed = R_NET_EFF_NOW                     # raise kill radius to net reach
    r_net_needed = R_KILL_NOW                         # shrink net lane to kill radius
    return {
        "current": {"r_kill": R_KILL_NOW, "r_net_eff": R_NET_EFF_NOW,
                    "eta": eta, "theta": THETA_NOW},
        "analytic_boundary": "eta = r_kill / r_net_eff = 1 (necessary, docs/09 (dddd))",
        "deltas_to_eta1": {
            "raise_r_kill_to": r_kill_needed,
            "d_r_kill": r_kill_needed - R_KILL_NOW,           # +0.24 m
            "shrink_r_net_eff_to": r_net_needed,
            "d_r_net_eff": r_net_needed - R_NET_EFF_NOW,      # -0.24 m
        },
        "note": ("eta axis is necessary-not-sufficient (docs/09 (dddd) 2-factor "
                 "envelope: also needs theta relaxed). Move A pairs an eta>1 design "
                 "with a theta-relaxation check on the SAME envelope. Engage-"
                 "independent (unlike Move C / the (ffff) net-temporal premise)."),
    }


def codesign_sweep(*args, **kw):
    """SKELETON (HELD). Full (r_kill x r_net_eff x net-design) co-design sweep:
    for each candidate net launch config (theta_deg, v0, m_g via net_forward ->
    r_net_eff + directional anisotropy) and each r_kill, recompute the (dddd)
    terminal operating-envelope (v_soft>=theta AND p_feas>0 AND lane-clear>=r_net_eff)
    and locate the eta>1 AND theta-feasible cells; then re-run a few G3 deployment
    rollouts at the winners. Held until the N1-temporal verdict makes Move A primary
    (user directive step 10)."""
    raise NotImplementedError(
        "Move A full sweep HELD (user directive): ship static eta + skeleton only. "
        "Enable after N1-temporal says Move A is primary.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-full", action="store_true",
                    help="(HELD) run the full co-design sweep -- currently raises")
    ap.add_argument("--out", default="results/c1_corridor/c1_moveA_eta.json")
    a = ap.parse_args()
    st = static_eta()
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(st, indent=1))
    c = st["current"]; dd = st["deltas_to_eta1"]
    print(f"[Move A static eta]  current: r_kill={c['r_kill']} r_net_eff={c['r_net_eff']} "
          f"-> eta={c['eta']:.3f} (theta={c['theta']})")
    print(f"  to reach eta=1 (analytic boundary): raise r_kill by {dd['d_r_kill']:+.2f} m "
          f"(-> {dd['raise_r_kill_to']:.2f})  OR  shrink r_net_eff by "
          f"{dd['d_r_net_eff']:+.2f} m (-> {dd['shrink_r_net_eff_to']:.2f})")
    print(f"  {st['note']}")
    print(f"  wrote {a.out}")
    if a.run_full:
        codesign_sweep()


if __name__ == "__main__":
    main()
