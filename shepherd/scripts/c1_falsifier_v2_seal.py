"""C-1 — FALSIFIER_V2_CODE_FREEZE.  Seal the falsifier, not the campaign.

TWO FREEZES, DELIBERATELY SEPARATE
----------------------------------
    FALSIFIER_V2_CODE_FREEZE         this file.  Code, budget, score and seed
                                     derivation are content-hashed now.
    CONFIRMATORY_EVALUATION_FREEZE   NOT this file.  It needs the held-out
                                     external-condition list sealed first
                                     (`c1_heldout_conditions`), and it is
                                     recorded here as INCOMPLETE so the two can
                                     never be quoted as one.

WHAT IS SEALED
--------------
  file content     sha256 of every module the falsifier's behaviour depends on,
                   including the scorer and the verifier it defers to
  budget           the literal constants that set how hard it searches
  score            the source of the scoring functions, so a later change to the
                   objective cannot pass as the same falsifier
  seed derivation  the source of `d0_seed`, so the stream namespace is pinned

`--verify` re-reads everything and reports drift, naming the file that moved.
A seal that cannot detect its own violation is decoration.
"""
from __future__ import annotations
import argparse, hashlib, inspect, json, pathlib, time

from shepherd.scripts.c1_phase1p_d0 import d0_seed
from shepherd.scripts.c1_falsifier_v2 import (STAGES, SCALES, N_PER_SCALE, TOP_M,
                                              ALIGN_K, N_GLOBAL_DIRS, s_proxy, s_auth,
                                              embed, temporal_starts, refine,
                                              segment_descent)
from shepherd.scripts.c1_phase1p_falsifier_v2_k1 import V2 as A0_CFG, k1_search
from shepherd.scripts.c1_falsifier_v2_k2_global import N_DIR as K2_N_DIR, MAGS as K2_MAGS

SEAL_VERSION = "FALSIFIER-v2-code-freeze-2026-07-26"
FILES = [
    "shepherd/scripts/c1_falsifier_v2.py",
    "shepherd/scripts/c1_phase1p_falsifier_v2_k1.py",
    "shepherd/scripts/c1_falsifier_v2_k2_global.py",
    "shepherd/scripts/c1_falsifier_v2_freeze.py",
    "shepherd/scripts/c1_phase1p_v2k1_verify.py",
    "shepherd/scripts/c1_replan_falsifier.py",      # kill / cone margin definitions
    "shepherd/scripts/c1_exact_clearance.py",       # authoritative verifier
    "shepherd/scripts/c1_phase1p_d0.py",            # seed derivation
    "shepherd/game/viability.py",                   # attacker dynamics
]


def _sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def _src(f):
    return hashlib.sha256(inspect.getsource(f).encode()).hexdigest()[:16]


def build():
    files = {p: _sha(p) for p in FILES}
    budget = {"stages": STAGES, "scales_x_a_max": SCALES, "n_per_scale": N_PER_SCALE,
              "top_m": TOP_M, "align_k": ALIGN_K, "n_global_dirs": N_GLOBAL_DIRS,
              "A0": {k: A0_CFG[k] for k in sorted(A0_CFG)},
              "K2_global": {"n_dir": K2_N_DIR, "magnitudes_x_a_max": list(K2_MAGS)}}
    score = {"s_proxy": _src(s_proxy), "s_auth": _src(s_auth),
             "embed": _src(embed), "temporal_starts": _src(temporal_starts),
             "refine": _src(refine), "segment_descent": _src(segment_descent),
             "k1_search": _src(k1_search)}
    seeds = {"d0_seed": _src(d0_seed),
             "development_stage_prefix": "V2-",
             "confirmatory_stage_prefix": "V2C-",
             "rule": "scenario_id ALWAYS in; arm NEVER in (paired CRN); stage_id "
                     "separates development from confirmatory streams"}
    body = {"seal_version": SEAL_VERSION, "files": files, "budget": budget,
            "score": score, "seeds": seeds}
    body["seal_hash"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/c1_corridor/c1_falsifier_v2_seal.json")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    now = build()
    p = pathlib.Path(a.out)

    if a.verify:
        if not p.exists():
            print("no seal at %s" % p); return 1
        old = json.loads(p.read_text())
        drift = [f for f in FILES if old["files"].get(f) != now["files"][f]]
        sdrift = [k for k in now["score"] if old["score"].get(k) != now["score"][k]]
        bdrift = json.dumps(old["budget"], sort_keys=True, default=str) != \
            json.dumps(now["budget"], sort_keys=True, default=str)
        ok = not drift and not sdrift and not bdrift
        # explicit names: an audit line reading "budget False" invites being read as
        # "budget disabled" rather than "budget did not drift".
        print("== FALSIFIER_V2_CODE_FREEZE --verify ==")
        print("   file_mismatch_count   = %d %s" % (len(drift), drift))
        print("   score_mismatch_count  = %d %s" % (len(sdrift), sdrift))
        print("   budget_mismatch       = %s" % bdrift)
        print("   SEAL_INTACT           = %s" % ok)
        return 0 if ok else 1

    print("== FALSIFIER_V2_CODE_FREEZE ==")
    for f in FILES:
        print("   %-52s %s" % (f, now["files"][f][:16]))
    print("\n   seal hash %s" % now["seal_hash"][:32])
    print("   score fns %s" % now["score"])
    print("\n   FALSIFIER_V2_CODE_FREEZE        SEALED")
    print("   CONFIRMATORY_EVALUATION_FREEZE  INCOMPLETE "
          "(needs the held-out condition list sealed first)")

    out = {"meta": {"script": "c1_falsifier_v2_seal",
                    "FALSIFIER_V2_CODE_FREEZE": "SEALED",
                    "CONFIRMATORY_EVALUATION_FREEZE": "INCOMPLETE",
                    "why_separate": "the code can be frozen now; the confirmatory "
                                    "protocol cannot, because the held-out external "
                                    "conditions are not yet generated and sealed",
                    "verify": "python3 -m shepherd.scripts.c1_falsifier_v2_seal --verify"},
           **now}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=str))
    print("\nwrote %s  (%.0fs)" % (p, time.time() - t0), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
