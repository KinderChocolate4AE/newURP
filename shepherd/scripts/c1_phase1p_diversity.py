"""C-1 Phase 1P step 1 — decorrelated re-search: does C-6 survive?

STATUS OF THIS RUN
------------------
This is the pre-registered `D0-MODE-DIVERSITY` diagnostic from the Phase 1M
escalation registry.  It produces DIVERSITY STATISTICS ONLY.  It does not emit,
revise, or re-derive a single D0 verdict, and nothing here can promote or demote
C-3 or C-4.  The frozen D0 verdicts stand as recorded in 1K/1L/1M/1N.

WHAT C-6 ACTUALLY CLAIMS, AND THE COMPETING EXPLANATION
-------------------------------------------------------
C-6 (provisional): the D0 raw/unique artifact counts overstate search diversity,
because the searches were witness-blind -- `reachable_accels` and the CEM seeds
carry no witness identifier, so every witness draws the same random stream.

Evidence so far is two shared `attack_policy_hash` values across DIFFERENT
scenarios (`651beb5780870eeb` from 1N, `961fcb3bbf8aa8b7` from the 1P seal).

But there is a competing explanation that the existing evidence does not
separate, and it deserves to be stated as strongly as C-6:

  H_ATTRACTOR : the shared policies are saturated box corners (1N measured
                ||a|| = 29.983 against a_att_max = 30, all four segments).  Two
                scenarios converging on the same corner may simply mean the corner
                is optimal for both.  Sharing would then be a fact about the
                objective landscape, not about the RNG, and C-6's diagnosis would
                be wrong even though its observation is right.

H_C6 and H_ATTRACTOR predict DIFFERENT things under decorrelation, so they can be
separated.

MECHANISM READ FROM THE CODE (checked, not assumed)
---------------------------------------------------
`c1_phase1k_frozen_audit.audit_one` warm-starts the CEM from

    acc1 = reachable_accels(a_att_max, n_cert, cert_seed)   # same bank, every witness
    warm = acc1[argmax(score_for_THIS_witness)]             # witness-dependent pick

so the warm start is a witness-dependent CHOICE out of a witness-independent POOL.
If two witnesses pick the same pool index, they start the CEM from the same point
with the same CEM seed, and will land in the same place.  That is a warm-start
collision, which is a sharper hypothesis than "the seeds are shared" -- and it is
directly measurable.

PRE-REGISTERED DESIGN (fixed before any number was looked at)
-------------------------------------------------------------
Three seed schemes per witness, everything else frozen:

  LEGACY     exactly what 1J-1N ran: bank seed = FROZEN cert seed, CEM seed =
             FROZEN confirm seed.  Witness-blind AND scenario-blind.
  RELABEL    same witness-blind structure, different constants (offset applied to
             both bank and CEM seed).  This is the NULL: it changes the stream
             without changing the blindness.
  DIVERSITY  bank and CEM seeds from `c1_governance.derive_seed(mode='diversity')`,
             so the stream depends on scenario_id AND witness_id.

Measured per scheme: the `attack_policy_hash` of each witness's top escape, the
number of distinct hashes, and the number of cross-witness collisions.

PRE-REGISTERED DECISION RULE  (implemented in `decide()`, not applied by hand)

  if collisions(RELABEL) < collisions(LEGACY):
        -> INCONCLUSIVE_CONFOUNDED.  Merely relabelling seeds already removes the
           collisions, so DIVERSITY cannot be credited with removing them.
  elif collisions(DIVERSITY) < collisions(LEGACY):
        -> C6_SUPPORTED.  Witness/scenario identity in the stream is what breaks
           the collisions, which is exactly C-6's mechanism.
  else:
        -> C6_NOT_SUPPORTED.  Decorrelation leaves the collisions standing, so they
           are a property of the objective landscape (H_ATTRACTOR) and C-6's
           diagnosis must be narrowed or retracted.

Warm-start collisions are reported alongside and interpreted the same way.

DIAGNOSTIC BUDGET (explicitly NOT the D0 budget)
------------------------------------------------
One bank seed and two CEM restarts per witness per scheme, versus D0's three bank
seeds and two confirm seeds.  This is a diversity measurement, so it is sized for
the comparison, not for a verdict.  Recorded here so the reduction is visible
rather than inferred.
"""
from __future__ import annotations
import argparse, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_response_probe import (make_spawn, make_contract, make_pd,
                                                THETA, R_BODY, M_SAFETY, PRIMARY, V_CLOSE)
from shepherd.scripts.c1_corridor_probe import ProbeEnv, _load, make_finisher_fn, ATT_P0
from shepherd.scripts.c1_a1_connectivity import _override
from shepherd.scripts.c1_phase1d import rollout_unified, log_ctrl
from shepherd.scripts.c1_phase1e import hermite_positions, DT
from shepherd.scripts.c1_plant_bound import solve_witness_hold, solve_witness, make_lp_arm
from shepherd.scripts.c1_replan_falsifier import (replan_search, kill_margin,
                                                  cone_exit_margin)
from shepherd.scripts.c1_phase1k_frozen_audit import FROZEN, RH, BASE, MAXCLR
from shepherd.scripts import c1_governance as G
from shepherd.game import viability as V

DIAG = {"role": "D0-MODE-DIVERSITY diagnostic -- NOT a verdict run",
        "n_bank": 20000, "K": FROZEN["K"], "pop": FROZEN["pop"], "iters": FROZEN["iters"],
        "restarts": 2, "reset": FROZEN["reset"],
        "d0_verdicts_touched": False}
RELABEL_OFFSET = 777_000_000
SCHEMES = ("LEGACY", "RELABEL", "DIVERSITY")


# --spread offsets / base seeds.  One offset is ONE SAMPLE of a witness-blind
# scheme; a single number cannot say whether a collision count is typical or
# extreme, so both families are swept.
BLIND_OFFSETS = (0, 777_000_000, 123_456_789, 55_000_000, 909_090_909, 314_159_265)
DIV_BASE_SEEDS = (7, 11, 23, 101)


def _blind_seeds(offset, restart):
    return (int(FROZEN["cert_seeds"][0]) + offset,
            int(FROZEN["replan_seeds_confirm"][restart]) + offset)


def _div_seeds(base_seed, scenario_id, witness_id, restart):
    kw = dict(base_seed=base_seed, scenario_id=scenario_id, witness_id=witness_id,
              reset_id=FROZEN["reset"], restart_id=restart, mode="diversity")
    return (G.derive_seed(attacker_class="bank", **kw) % (2 ** 31 - 1),
            G.derive_seed(attacker_class="K4-pwc-cem", **kw) % (2 ** 31 - 1))


def _seeds(scheme, scenario_id, witness_id, restart):
    """(bank seed, CEM seed) for one witness under one scheme."""
    if scheme == "LEGACY":
        return _blind_seeds(0, restart)
    if scheme == "RELABEL":
        return _blind_seeds(RELABEL_OFFSET, restart)
    if scheme == "DIVERSITY":
        return _div_seeds(7, scenario_id, witness_id, restart)
    if isinstance(scheme, tuple):                 # ("blind", off) | ("div", base_seed)
        kind, val = scheme
        return (_blind_seeds(val, restart) if kind == "blind"
                else _div_seeds(val, scenario_id, witness_id, restart))
    raise ValueError(scheme)


def _env():
    env_cfg, m3, _t = _load("configs/m3a_a3e_p1.yaml")
    pe = ProbeEnv(env_cfg, m3); E = pe.ad.env
    _override(E, PRIMARY["r_kill"], PRIMARY["r_net_dir"])
    return pe, E, make_finisher_fn(THETA)


def witnesses():
    """The cheap 12 of the 15 D0 scenarios.  The 3 EXPLOIT witnesses need
    c1_controller_gap.cem_O to rebuild the CONTROLLER and are handled by
    --with-exploit, since that cost is unrelated to what is being measured."""
    out = []
    for rho0, tl, f in RH:
        out.append(("RH", "RH %.1f/%.2f f=%d" % (rho0, tl, f), rho0, tl, ("RH", f)))
    for rho0, tl, arm in BASE:
        out.append(("BASE", "BASE %.1f/%.2f %s" % (rho0, tl, arm), rho0, tl, ("BASE", arm)))
    for rho0, tl, f in MAXCLR:
        out.append(("MAXCLR", "MAXCLR %.1f/%.2f f=%d" % (rho0, tl, f), rho0, tl, ("MAXCLR", f)))
    return out


def rollout_for(pe, fin, kind, rho0, tl, spec):
    RL, RB = PRIMARY["r_net_dir"], R_BODY + M_SAFETY
    if kind == "RH":
        s, d, _m = solve_witness_hold(rho0, spec[1]);  w = log_ctrl(make_lp_arm(s))
    elif kind == "MAXCLR":
        s, _m = solve_witness(rho0, spec[1]);          w = log_ctrl(make_lp_arm(s))
    elif kind == "BASE":
        w = log_ctrl(make_contract() if spec[1] == "C" else make_pd())
    else:
        raise ValueError(kind)
    return rollout_unified(pe, make_spawn(rho0, tl * V_CLOSE), w, fin, r_lane=RL, r_body=RB)


def probe(pe, E, rec, scheme, scenario_id, witness_id):
    """Run the diagnostic search for one witness under one seed scheme."""
    tau = float(E.tau_deploy); t = rec["_t_ref"]
    o = np.asarray(rec["_obs"][t], float)
    p_att = o[ATT_P0:ATT_P0 + 3]; v_att = o[ATT_P0 + 3:ATT_P0 + 6]
    P = np.asarray(rec["_lim"][t:], float); Vp = np.asarray(rec["_vel"][t:], float)
    kw = E._vshot_kwargs(p_att, v_att, o[36:45])
    cone_kw = {k: kw[k] for k in ("net_apex", "n_F", "theta_net", "range_min", "range_max")}
    L = lambda ts: hermite_positions(P, Vp, np.asarray(ts))[0]

    best_all, warm_idx = {"score": -np.inf, "acc": None}, None
    for r in range(DIAG["restarts"]):
        sd_bank, sd_cem = _seeds(scheme, scenario_id, witness_id, r)
        acc1 = V.reachable_accels(E.a_att_max, DIAG["n_bank"], int(sd_bank))
        ep1, tf1, pts1 = V._seg_paths_turn(p_att, v_att,
                                           np.repeat(acc1[:, None, :], DIAG["K"], axis=1),
                                           tau=tau, attacker_turn_limited=False,
                                           omega_att_max=None, e_att=None, n_t=24)
        sc1 = np.minimum(kill_margin(pts1, L, E.kill_radius, tau),
                         cone_exit_margin(ep1, **cone_kw))
        j = int(np.argmax(sc1))
        if r == 0:
            warm_idx = j
        warm = np.repeat(acc1[j][None, :], DIAG["K"], axis=0)
        best, _escs = replan_search(p_att, v_att, tau=tau, a_att_max=E.a_att_max,
                                    L_of_t=L, kill_radius=E.kill_radius, cone_kw=cone_kw,
                                    K=DIAG["K"], pop=DIAG["pop"], iters=DIAG["iters"],
                                    seed=int(sd_cem), warm=warm)
        if best["score"] > best_all["score"]:
            best_all = best
    acc = np.asarray(best_all["acc"], float)
    return {"scheme": scheme, "scenario_id": scenario_id,
            "attack_policy_hash": G.attack_policy_hash(acc),
            "score_m": float(best_all["score"]),
            "accel_norms": [round(float(x), 4) for x in np.linalg.norm(acc, axis=1)],
            "saturated": bool((np.linalg.norm(acc, axis=1) > 0.99 * E.a_att_max).all()),
            "warm_start_index": int(warm_idx),
            "is_escape": bool(best_all["score"] > 0)}


def collisions(rows):
    """cross-witness identical-policy pairs, and identical warm-start pairs."""
    pol, warm = {}, {}
    for r in rows:
        pol.setdefault(r["attack_policy_hash"], []).append(r["scenario_id"])
        warm.setdefault(r["warm_start_index"], []).append(r["scenario_id"])
    npair = lambda d: sum(len(v) * (len(v) - 1) // 2 for v in d.values())
    return {"n_unique_policies": len(pol), "n_policy_collision_pairs": npair(pol),
            "shared_policies": {k: v for k, v in pol.items() if len(v) > 1},
            "n_unique_warm_starts": len(warm), "n_warm_collision_pairs": npair(warm),
            "shared_warm_starts": {str(k): v for k, v in warm.items() if len(v) > 1}}


def decide(stats):
    """The pre-registered rule, applied mechanically."""
    cl, cr, cd = (stats[s]["n_policy_collision_pairs"] for s in SCHEMES)
    if cr < cl:
        return ("INCONCLUSIVE_CONFOUNDED",
                "relabelling alone drops collisions %d -> %d, so DIVERSITY cannot be "
                "credited with the reduction" % (cl, cr))
    if cd < cl:
        return ("C6_SUPPORTED",
                "collisions LEGACY %d -> RELABEL %d -> DIVERSITY %d; identity in the "
                "stream is what breaks them" % (cl, cr, cd))
    return ("C6_NOT_SUPPORTED",
            "collisions LEGACY %d -> RELABEL %d -> DIVERSITY %d; decorrelation does not "
            "remove them, so they are a property of the objective landscape "
            "(H_ATTRACTOR), not of the RNG" % (cl, cr, cd))


def spread(pe, E, fin, ws, recs):
    """Sweep both seed families.  A single offset cannot distinguish 'this scheme
    collapses' from 'this one offset was unlucky', so the answer is a RANGE."""
    res = {"blind": [], "diversity": []}
    print("== spread: witness-blind family (%d offsets) ==" % len(BLIND_OFFSETS))
    for off in BLIND_OFFSETS:
        sub = [probe(pe, E, recs[tag], ("blind", off), tag, "w:" + tag)
               for _k, tag, _r, _t, _s in ws]
        c = collisions(sub); n_esc = sum(1 for r in sub if r["is_escape"])
        res["blind"].append({"offset": off, "n_unique": c["n_unique_policies"],
                             "policy_collisions": c["n_policy_collision_pairs"],
                             "warm_collisions": c["n_warm_collision_pairs"],
                             "escapes": n_esc})
        print("   offset %-11d unique %2d/%d  pol-coll %2d  warm-coll %2d  escapes %2d/%d"
              % (off, c["n_unique_policies"], len(ws), c["n_policy_collision_pairs"],
                 c["n_warm_collision_pairs"], n_esc, len(ws)), flush=True)
    print("== spread: decorrelated family (%d base seeds) ==" % len(DIV_BASE_SEEDS))
    for bs in DIV_BASE_SEEDS:
        sub = [probe(pe, E, recs[tag], ("div", bs), tag, "w:" + tag)
               for _k, tag, _r, _t, _s in ws]
        c = collisions(sub); n_esc = sum(1 for r in sub if r["is_escape"])
        res["diversity"].append({"base_seed": bs, "n_unique": c["n_unique_policies"],
                                 "policy_collisions": c["n_policy_collision_pairs"],
                                 "warm_collisions": c["n_warm_collision_pairs"],
                                 "escapes": n_esc})
        print("   base %-11d unique %2d/%d  pol-coll %2d  warm-coll %2d  escapes %2d/%d"
              % (bs, c["n_unique_policies"], len(ws), c["n_policy_collision_pairs"],
                 c["n_warm_collision_pairs"], n_esc, len(ws)), flush=True)
    bc = [r["policy_collisions"] for r in res["blind"]]
    dc = [r["policy_collisions"] for r in res["diversity"]]
    be = [r["escapes"] for r in res["blind"]]
    de = [r["escapes"] for r in res["diversity"]]
    res["summary"] = {
        "blind_policy_collisions": bc, "div_policy_collisions": dc,
        "blind_escapes": be, "div_escapes": de,
        "separation": "witness-blind collisions range %d-%d; decorrelated are %d-%d"
                      % (min(bc), max(bc), min(dc), max(dc)),
        "escape_rate_note": "escape counts OVERLAP (blind %d-%d vs decorrelated %d-%d); "
                            "decorrelation is a diversity fix, NOT a demonstrated "
                            "search-efficiency improvement"
                            % (min(be), max(be), min(de), max(de))}
    print("\n   blind  collisions %s   decorrelated %s" % (bc, dc))
    print("   blind  escapes    %s   decorrelated %s" % (be, de))
    print("   %s" % res["summary"]["escape_rate_note"])
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1p_diversity.json")
    ap.add_argument("--spread", action="store_true",
                    help="sweep both seed families instead of the 3 named schemes")
    a = ap.parse_args()
    pe, E, fin = _env()
    ws = witnesses()
    if a.spread:
        recs = {tag: rollout_for(pe, fin, k, r0, tl, sp) for k, tag, r0, tl, sp in ws}
        res = spread(pe, E, fin, ws, recs)
        p = pathlib.Path("results/c1_corridor/c1_phase1p_diversity_spread.json")
        p.write_text(json.dumps({"meta": {"script": "c1_phase1p_diversity --spread",
                                          "diagnostic_budget": DIAG,
                                          "blind_offsets": list(BLIND_OFFSETS),
                                          "div_base_seeds": list(DIV_BASE_SEEDS)},
                                 **res}, indent=1, default=float))
        print("wrote", p, flush=True)
        return 0
    print("== D0-MODE-DIVERSITY diagnostic (no verdict is produced) ==")
    print("   witnesses %d x schemes %d, restarts %d" % (len(ws), len(SCHEMES), DIAG["restarts"]))

    recs = {}
    for kind, tag, rho0, tl, spec in ws:
        recs[tag] = rollout_for(pe, fin, kind, rho0, tl, spec)

    rows, stats = [], {}
    for scheme in SCHEMES:
        t0 = time.time(); sub = []
        for kind, tag, rho0, tl, spec in ws:
            r = probe(pe, E, recs[tag], scheme, tag, witness_id="w:" + tag)
            r["class"] = kind
            sub.append(r); rows.append(r)
            print("   [%-9s] %-22s pol %s  score %+.4f m  warm %6d  %s"
                  % (scheme, tag, r["attack_policy_hash"], r["score_m"],
                     r["warm_start_index"], "SAT" if r["saturated"] else ""), flush=True)
        stats[scheme] = collisions(sub)
        print("   -> %-9s unique %2d/%d | policy-collision pairs %d | warm-collision pairs %d"
              " | %.0fs" % (scheme, stats[scheme]["n_unique_policies"], len(sub),
                            stats[scheme]["n_policy_collision_pairs"],
                            stats[scheme]["n_warm_collision_pairs"], time.time() - t0),
              flush=True)

    verdict, why = decide(stats)
    n_esc = {s: sum(1 for r in rows if r["scheme"] == s and r["is_escape"]) for s in SCHEMES}
    print("\n   escapes found: %s of %d witnesses per scheme" % (n_esc, len(ws)))
    print("   PRE-REGISTERED DECISION: %s\n     %s" % (verdict, why))

    out = {"meta": {"script": "c1_phase1p_diversity", "diagnostic_budget": DIAG,
                    "protocol": G.PROTOCOL_VERSION, "schemes": list(SCHEMES),
                    "relabel_offset": RELABEL_OFFSET,
                    "decision_rule": decide.__doc__,
                    "hypotheses": {"H_C6": "sharing caused by witness-blind RNG streams",
                                   "H_ATTRACTOR": "sharing caused by a common saturated "
                                                  "box-corner optimum"}},
           "n_witnesses": len(ws), "stats": stats, "n_escapes_per_scheme": n_esc,
           "decision": verdict, "decision_reason": why, "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("wrote", p, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
