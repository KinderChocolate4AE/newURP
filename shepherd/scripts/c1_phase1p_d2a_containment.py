"""C-1 Phase 1P — D2a containment test.  MANDATORY, and it runs BEFORE D2a.

WHY IT COMES FIRST
------------------
D2a widens the attacker from K=4 to K=8 piecewise-constant segments.  The whole
point is that K=8 is a SUPERSET: tau/8 halves tau/4, so every K=4 attack is
exactly representable.  If that nesting is not actually realised in the code, a
K=8 null is worthless -- the defender would look stronger against a wider
attacker class purely because the wider search was re-parameterised into a space
where the old attacks were unreachable.

FOUR LAYERS, IN ORDER
---------------------
  L1  parameter embedding
      embed(a4) = repeat(a4, 2, axis=0).  The time-indexed control u(t) must be
      IDENTICAL under both parameterisations at densely sampled t.
  L2  step-level control bit parity
      the same comparison at the bit level (tobytes), not just np.allclose.
  L3  rollout / verdict parity
      endpoint, cone components and the CONTINUOUS clearance verdict.
      NOTE, and this is a correction to how the D1 readout phrased it: the
      floating-point ROLLOUT is *not* bit-identical and cannot be.  K=8 composes
      two half-steps where K=4 takes one full step, and `_seg_paths_turn`'s
      substep grid is finer.  Exact arithmetic makes them equal; IEEE754 does
      not.  So L3 asserts VERDICT identity and REPORTS the numerical
      discrepancy rather than asserting a bit-identity that is false.
  L4  known-K4-escape containment
      every known verified K=4 escape, embedded, must still be adjudicated an
      escape on the K=8 path.  This is the layer that would catch a silently
      weakened attacker.

Any layer failing blocks D2a.  A wider attacker class that cannot reproduce the
narrower one's counterexamples is not an escalation.
"""
from __future__ import annotations
import argparse, json, pathlib, time
import numpy as np

from shepherd.scripts.c1_phase1p_diversity import _env, witnesses, rollout_for
from shepherd.scripts.c1_phase1p_modes import cone_components, _artifacts
from shepherd.scripts.c1_phase1p_d1_canary import _ctx, replay
from shepherd.scripts import c1_governance as G
from shepherd.game import viability as V

K4, K8 = 4, 8
VERDICT_TOL_M = 1e-9          # verdicts must agree; margins are reported, not asserted
ENDPOINT_TOL_M = 1e-9


def embed(a4):
    """K=4 -> K=8.  Each tau/4 segment becomes two tau/8 segments with the same
    acceleration, so the control as a FUNCTION OF TIME is unchanged."""
    return np.repeat(np.asarray(a4, float), 2, axis=0)


def u_of_t(acc, tau, ts):
    """The piecewise-constant control sampled at global times -- the object that
    must be identical between the two parameterisations."""
    acc = np.asarray(acc, float); K = len(acc); h = tau / K
    idx = np.minimum((np.asarray(ts, float) / h).astype(int), K - 1)
    return acc[idx]


def l1_l2_control_parity(a4, tau, n=4096):
    """L1 + L2 -- embedding correctness and bit parity of the control signal."""
    a8 = embed(a4)
    ts = np.linspace(0.0, tau, n, endpoint=False)
    u4, u8 = u_of_t(a4, tau, ts), u_of_t(a8, tau, ts)
    return {"shape_k4": list(np.shape(a4)), "shape_k8": list(np.shape(a8)),
            "L1_embedding_control_identical": bool(np.array_equal(u4, u8)),
            "L2_control_bit_parity": bool(u4.tobytes() == u8.tobytes()),
            "n_sample_times": int(n),
            "max_abs_control_difference": float(np.abs(u4 - u8).max())}


def l3_rollout_verdict_parity(E, pa, va, L, cone, tau, a4):
    """L3 -- endpoint, cone terms and the continuous verdict, K=4 vs embedded K=8."""
    a8 = embed(a4)
    r4 = replay(E, pa, va, L, cone, tau, a4)
    r8 = replay(E, pa, va, L, cone, tau, a8)
    e4, _t4, _p4 = V._seg_paths_turn(pa, va, np.asarray(a4, float)[None], tau=tau,
                                     attacker_turn_limited=False, omega_att_max=None,
                                     e_att=None, n_t=24)
    e8, _t8, _p8 = V._seg_paths_turn(pa, va, a8[None], tau=tau,
                                     attacker_turn_limited=False, omega_att_max=None,
                                     e_att=None, n_t=24)
    dend = float(np.abs(e4 - e8).max())
    dcont = abs(r4["continuous_kill_margin_m"] - r8["continuous_kill_margin_m"])
    return {"k4": r4, "k8": r8,
            "endpoint_max_abs_difference_m": dend,
            "continuous_margin_abs_difference_m": float(dcont),
            "sampled_kill_margin_difference_m":
                float(r4["sampled_kill_margin_m"] - r8["sampled_kill_margin_m"]),
            "cone_exit_margin_difference_m":
                float(r4["cone_exit_margin_m"] - r8["cone_exit_margin_m"]),
            "L3_verdict_identical": bool(r4["verdict"] == r8["verdict"]),
            "L3_escape_label_identical":
                bool(r4["recognised_as_escape"] == r8["recognised_as_escape"]),
            "L3_endpoint_within_tol": bool(dend <= ENDPOINT_TOL_M),
            "L3_continuous_margin_within_tol": bool(dcont <= 1e-6),
            "bit_identity_claimed": False,
            "why_not_bit_identical":
                "K=8 composes two half-steps per K=4 step and samples a finer substep "
                "grid; equality holds in exact arithmetic, not in IEEE754"}


def known_k4_escapes(pe, E, fin, d0):
    """L4 sources -- every verified K=4 escape this campaign can still produce,
    spanning millimetre (D0) and metre (MAXCLR) scale."""
    out = []
    for r in d0["rows"]:
        for e in r["d0"]["escapes"]:
            out.append({"source": "D0 verified escape", "witness": r["witness"],
                        "arm": r["arm"], "delta_m": r["selected_delta_m"],
                        "mode": e["mode"], "acc": np.asarray(e["acc"], float)})
    for tag in ("MAXCLR 5.0/0.55 f=10", "RH 4.0/0.40 f=7"):     # CEGIS attack set members
        kind, _t, rho0_, tl, spec = [w for w in witnesses() if w[1] == tag][0]
        rec = rollout_for(pe, fin, kind, rho0_, tl, spec)
        d = _artifacts(pe, E, rec, tag, (7,))
        if d is None:
            continue
        sc = np.minimum(d["km"], d["cm"])
        for lbl, i in (("largest-margin", int(np.argmax(sc))),
                       ("tightest-margin", int(np.argmin(sc)))):
            out.append({"source": "CEGIS attack set (%s)" % lbl, "witness": tag,
                        "arm": "NOMINAL", "delta_m": 0.0, "mode": "REDERIVED",
                        "acc": d["A"][i]})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--d0", default="results/c1_corridor/c1_phase1p_d0.json")
    ap.add_argument("--out", default="results/c1_corridor/c1_phase1p_d2a_containment.json")
    a = ap.parse_args()
    pe, E, fin = _env(); t0 = time.time()
    d0 = json.loads(pathlib.Path(a.d0).read_text())

    print("== D2a containment test (MANDATORY, runs before D2a) ==")
    print("   K=8 must CONTAIN K=4.  A wider class that cannot reproduce the narrower")
    print("   one's counterexamples is not an escalation.\n")

    src = known_k4_escapes(pe, E, fin, d0)
    print("   known K=4 escapes assembled: %d" % len(src))
    rows = []
    for s in src:
        pa, va, L, cone, tau = _ctx(pe, E, fin, s["witness"], s["delta_m"])
        c12 = l1_l2_control_parity(s["acc"], tau)
        c3 = l3_rollout_verdict_parity(E, pa, va, L, cone, tau, s["acc"])
        contained = bool(c3["k8"]["recognised_as_escape"])
        rows.append({**{k: s[k] for k in ("source", "witness", "arm", "delta_m", "mode")},
                     "k4_hash": G.attack_policy_hash(np.asarray(s["acc"], float)),
                     "k8_hash": G.attack_policy_hash(embed(s["acc"])),
                     "L1_L2": c12, "L3": c3,
                     "L4_known_escape_contained": contained})
        print("   %-26s %-22s L1 %s L2 %s L3verdict %s L4 %s  (dEnd %.2e dMargin %.2e)"
              % (s["source"][:26], s["witness"],
                 "OK" if c12["L1_embedding_control_identical"] else "FAIL",
                 "OK" if c12["L2_control_bit_parity"] else "FAIL",
                 "OK" if c3["L3_verdict_identical"] else "FAIL",
                 "OK" if contained else "FAIL",
                 c3["endpoint_max_abs_difference_m"],
                 c3["continuous_margin_abs_difference_m"]), flush=True)

    L1 = all(r["L1_L2"]["L1_embedding_control_identical"] for r in rows)
    L2 = all(r["L1_L2"]["L2_control_bit_parity"] for r in rows)
    L3 = all(r["L3"]["L3_verdict_identical"] and r["L3"]["L3_escape_label_identical"]
             and r["L3"]["L3_endpoint_within_tol"] for r in rows)
    L4 = all(r["L4_known_escape_contained"] for r in rows)
    ok = bool(L1 and L2 and L3 and L4 and rows)

    dend = max(r["L3"]["endpoint_max_abs_difference_m"] for r in rows) if rows else 0.0
    dmar = max(r["L3"]["continuous_margin_abs_difference_m"] for r in rows) if rows else 0.0
    print("\n   L1 parameter embedding        %s" % ("PASS" if L1 else "FAIL"))
    print("   L2 control bit parity         %s" % ("PASS" if L2 else "FAIL"))
    print("   L3 rollout / verdict parity   %s  (worst endpoint %.3e m, "
          "worst continuous margin %.3e m)" % ("PASS" if L3 else "FAIL", dend, dmar))
    print("   L4 known-K4-escape contained  %s  (%d artifacts)"
          % ("PASS" if L4 else "FAIL", len(rows)))
    print("\n   VERDICT: %s"
          % ("D2A_CONTAINMENT_VERIFIED -- D2a may run"
             if ok else "D2A_BLOCKED -- containment failed; a K=8 null would be meaningless"))

    out = {"meta": {"script": "c1_phase1p_d2a_containment",
                    "role": "MANDATORY gate before D2a; changes no controller",
                    "layers": {"L1": "parameter embedding: repeat(a4,2) reproduces u(t)",
                               "L2": "step-level control BIT parity",
                               "L3": "rollout / verdict parity -- verdict asserted, "
                                     "fp discrepancy reported (bit identity is NOT claimed "
                                     "and is not achievable)",
                               "L4": "known K=4 escapes, embedded, still adjudicated escapes"},
                    "correction_to_d1_readout":
                        "the D1 readout wrote 'K=4 artifact must reproduce bit-for-bit'. "
                        "Bit identity holds for the CONTROL SIGNAL (L2); the ROLLOUT differs "
                        "at fp level by construction. The operative test is verdict identity.",
                    "tolerances_m": {"endpoint": ENDPOINT_TOL_M, "continuous_margin": 1e-6}},
           "L1_pass": L1, "L2_pass": L2, "L3_pass": L3, "L4_pass": L4,
           "worst_endpoint_difference_m": dend,
           "worst_continuous_margin_difference_m": dmar,
           "verdict": "D2A_CONTAINMENT_VERIFIED" if ok else "D2A_BLOCKED",
           "rows": rows}
    p = pathlib.Path(a.out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=float))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
