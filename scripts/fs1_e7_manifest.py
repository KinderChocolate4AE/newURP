"""Seal E7-a probe grid: ①축 net 물리 sweep stage a — docs/129.

    python scripts/fs1_e7_manifest.py      # E7-a manifest 기록 (프로브 결과 보기 전 봉인)
"""
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "fs1" / "e7a_manifest.json"


def build_e7a() -> dict:
    body = {
        "schema": "fs1-e7a-manifest-v1.1",
        "status": ("sealed before any full E7-a probe result (contract: docs/129). v1.1 "
                   "PRE-LAUNCH CORRECTION (E3 v1->v1.1 precedent): the 2-ep scratch smoke "
                   "revealed the v1 instant-aim axis approximation dominates the map (anchor "
                   "agree 0.70-0.90; the identity variant itself got promoted) -> replaced "
                   "with a per-variant turret-slew simulation (great-circle, omega_fin*dt, "
                   "shepherd.sim.analytic._slew; omega_fin runtime-recorded). Entry criterion "
                   "and predictions unchanged. No full-run result was seen before this seal"),
        "lineage": {"contract": "docs/129", "armd": "c21ab916d68e3e30 (ARMD_NULL)",
                    "occupancy_15a": "artifacts/fs1/e3b/occupancy.json (9275722) — protocol "
                    "reused (SEED0 268000, no-fire, LOADED & d<=16)",
                    "jax_design": "newURP-jax 103165d E7_PLUMBING_DESIGN.md (E7-a needs zero "
                    "world change: all three knobs are judge-call arguments in a no-fire probe)"},
        "grid": {"cell": "m0.35_n1 (mu-nu plane flat per E3 — axis-1 isolation)",
                 "tau_scale": [1.0, 0.7, 0.5], "theta_scale": [1.0, 1.5],
                 "aim": ["cv (nc = p+v*tau, current)",
                         "ma (nc += 0.5*ahat*tau^2; ahat = (v_t - v_{t-1})/dt, |ahat| <= "
                         "a_att_max clip, first tick 0)"],
                 "variants": 12,
                 "excluded": "range, axis-3 turn-limit (P0a AXIS3_NULL), FRPN terminal guidance"},
        "rho": ("rho(variant) = d_star * tan(theta_v) / (0.5 * a_att * tau_v^2), d_star = "
                "cone_range_max (runtime-recorded). Absolute level depends on the d_star "
                "convention — monotonicity/ratios only; no absolute comparison to the A.1 "
                "anchor 1.6"),
        "aggregation": "per variant: median over the 4 slot medians of per-episode robust-step "
                       "counts (same family as P0a), 24 eps x 4 adapted attackers",
        "predictions": {
            "P-rho1": "window med is monotone in rho: Spearman(rho, window_med) >= 0.7 -> "
                      "P_RHO1_SUPPORTED; an inversion-rich map rejects rho-sole-dominance",
            "P-rho2": "the K1 hand-proof rho boundary (user lane, <= 2026-10-31) overlays the "
                      "E7-a window map contour — boundary value must be registered BEFORE "
                      "E7-b training starts, else E7-b proceeds flagged as boundary-unregistered",
        },
        "e7b_entry": "variant window med >= 4 steps (same threshold family as P0a) -> promotion "
                     "to E7-b training candidates; zero promotions -> grid extension resubmitted "
                     "to the user (no training)",
        "probe_approximations": [
            "attackers = old-world adapted exploiters (non-co-evolved) — optimistic bias; "
            "selection only, positive claims E7-b only (fresh new-world exploiter + audit)",
            "aim axis = per-variant turret-slew simulation (v1.1): tracks desired = "
            "unit(nc_v - p_fin) at omega_fin*dt per tick from the episode-start heading; "
            "identity-variant vs rollout-axis anchor agree reported as simulation fidelity "
            "(expected ~1)",
            "wiring self-check: (tau0, theta0, n_F = rollout e_fin) bit-exact vs inn._vshot",
        ],
        "jax_parity_note": ("risk-1 answer (JAX memo section 3): E7-a touches no world code. "
                            "For E7-b the canonical landing must scale inn.tau_deploy AND the "
                            "FSM dep-timer table from ONE FS1Spec source — recorded as an E7-b "
                            "addendum precondition"),
        "not_evidence_for": ["world ceiling", "capture probability (guaranteed-capture lower "
                             "bound only)", "pooling with old-world numbers (reference anchor "
                             "comparison only)"],
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load_e7a() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data != build_e7a():
        raise ValueError(f"E7-a manifest drift: {MANIFEST}")
    return data


# ---------------------------------------------------------------- E7-b ------
MANIFEST_B = ROOT / "artifacts" / "fs1" / "e7b_manifest.json"

B_VARIANTS = [{"name": "t0.7_h1.0_cv", "tau_scale": 0.7, "theta_scale": 1.0, "aim": "cv", "rho": 3.925},
              {"name": "t0.7_h1.5_cv", "tau_scale": 0.7, "theta_scale": 1.5, "aim": "cv", "rho": 6.002},
              {"name": "t0.5_h1.0_cv", "tau_scale": 0.5, "theta_scale": 1.0, "aim": "cv", "rho": 7.692},
              {"name": "t0.5_h1.5_cv", "tau_scale": 0.5, "theta_scale": 1.5, "aim": "cv", "rho": 11.765},
              {"name": "t0.5_h1.0_ma", "tau_scale": 0.5, "theta_scale": 1.0, "aim": "ma", "rho": 7.692}]
B_SEEDS = [0, 1, 2]
B_N, B_MARGIN, B_CEIL_REF = 240, 24, 5
B_TRAIN_STEPS, B_EX_STEPS = 1.1e8, 1e7
B_SEED0, B_STRIDE = 276000, 1000


def build_e7b() -> dict:
    body = {
        "schema": "fs1-e7b-manifest-v1",
        "status": ("sealed after the E7-a readout (P_RHO1_SUPPORTED, harvest b5f8695) and the "
                   "P-rho2 registration (note 2026-10-08c), BEFORE any E7-b training. Scope = "
                   "user approval 2026-10-08 (5 variants: cv rho-ladder 4 + ma contrast 1)"),
        "lineage": {"contract": "docs/129 section 6", "e7a": build_e7a()["manifest_hash"],
                    "p_rho2": "note 2026-10-08c: rho* = 2.813 (4dt, V=23.01) / 2.427 (3.5dt); "
                              "registered pre-E7-b, no flag",
                    "recipe": "arm C-1 (docs/127, 1173759cf5e4854b) — distilled fire head; "
                              "arm D stack excluded (ARMD_NULL)"},
        "question": ("Q-E7b: in net-physics variants whose probe window opened (E7-a), does "
                     "the retrained defense open the capture ceiling under a FRESH new-world "
                     "dedicated judge exploiter — i.e., does rho buy capture capability, not "
                     "just probe windows"),
        "cell": {"cell": "m0.35_n1", "mu": 0.35, "nu": 1.0},
        "variants": B_VARIANTS, "seeds": B_SEEDS,
        "production": {
            "world": ("canonical-first variant landing, JAX mirror: tau via the SINGLE config "
                      "source physics.tau_deploy override (propagates to env.tau_deploy AND "
                      "the FSM dep timer through the scenario — resolves JAX risk-1 by "
                      "construction); theta via judge cone_half_angle scale; ma aim nc += "
                      "0.5*ahat*tau^2 (finite-difference ahat, a_att_max clip) applied at BOTH "
                      "the turret-tracking (env_sys) and net_center (env) sites. Baseline "
                      "(1.0/1.0/cv) must be bit-exact with the current world (test required); "
                      "JAX parity = baseline golden + one non-default variant f64 spot-check"),
            "bc": "NEW per-variant BC (canonical bc.py, 3000 eps) — old-world BC reuse banned",
            "train": f"arm C-1 recipe, {B_TRAIN_STEPS:.1e} steps, seeds {B_SEEDS}",
            "exploiter": f"fresh dedicated judge exploiter vs the frozen defense, "
                         f"{B_EX_STEPS:.0e}, jseed 277000-band, audit curve logged",
        },
        "evaluation": {"n": B_N, "seed0": B_SEED0, "variant_seed_stride": B_STRIDE,
                       "variant_idx": "index in THIS manifest's variants list",
                       "paired": True, "stack": "r4p", "groups": "none",
                       "defenders": ["learned_det (judgment)", "learned_sto (report)",
                                     "fin12_fb + kfirst50 (scripted TRANSFER reference vs the "
                                     "same judge exploiter — exploiter was trained vs the "
                                     "learned defense, so reference-only, never a gate)"],
                       "environment": "server4; seed band 276000+ never used in training"},
        "gates": {
            "E7_OPENS": (f"per variant: ceil_learned_det >= {B_CEIL_REF} + {B_MARGIN} = "
                         f"29/{B_N} on >= 2 of 3 seeds. HONESTY FLAG: new-world ceil_ref not "
                         "re-measured (threshold family continuity); scripted transfer "
                         "reference reported as the compensating context"),
            "overall": "any variant opens -> E7_OPENS else E7B_NULL; INVALID per budget/"
                       "completion/paired/manifest/BC-lineage violation (variant excluded)",
            "P-rho3": "cv-ladder (4 points): seed-median ceil_det monotone in rho, "
                      "Spearman >= 0.7 -> P_RHO3_SUPPORTED (money-curve claim); ma point "
                      "reported as a pair contrast at equal rho",
        },
        "readout_extras": ["P-rho2 overlay: recompute the E7-a window median CONDITIONAL on "
                           "shell-passing encounters (registered population) from "
                           "artifacts/fs1/e7a/rows.npz, then overlay rho* = 2.813 and the "
                           "N = N_inf*(1 - rho0/rho) shape (rho0 = 1.238) on the money curve; "
                           "registered values immutable",
                           "NET-occupancy vs audit-penetration correlation across variants "
                           "(m0.35_s2 clue tracking)", "C-2 logs retained",
                           "fired-ep / robust-fire conversion (same threshold family "
                           "reference to armc1/armd only)"],
        "not_evidence_for": ["world ceiling", "real-net representativeness",
                             "positive claims unconditional on this exploiter budget (1e7)",
                             "pooling with old-world numbers"],
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load_e7b() -> dict:
    data = json.loads(MANIFEST_B.read_text(encoding="utf-8"))
    if data != build_e7b():
        raise ValueError(f"E7-b manifest drift: {MANIFEST_B}")
    return data


# ---------------------------------------------------------------- E7-a′ -----
MANIFEST_A2 = ROOT / "artifacts" / "fs1" / "e7a2_manifest.json"


def build_e7a2() -> dict:
    body = {
        "schema": "fs1-e7a2-manifest-v1.1",
        "status": ("sealed BEFORE any E7-b result (E7-b not yet launched) and before the "
                   "E7-a′ full run (contract: docs/129 section 7; user agreement 2026-10-08). "
                   "v1.1 PRE-LAUNCH LABEL FIX: the 2-ep scratch smoke gave C = 0 at every rho; "
                   "v1 would have labeled that NOT_SUPPORTED, but an all-zero C means the "
                   "prediction is untestable, not falsified -> explicit UNDECIDABLE_C0 "
                   "verdict. Criteria unchanged. Context: P0 rows show scripted limiters "
                   "prune witnesses in 12% of window ticks (p_feas < 1), so C = 0 would mean "
                   "pruning never flips the judgment, not a wiring fault"),
        "lineage": {"contract": "docs/129 section 7", "e7a": build_e7a()["manifest_hash"],
                    "e7b": build_e7b()["manifest_hash"],
                    "p_rho2": "rho* = 2.813 is the axis-2 = 0 boundary (K1 assumption A5)"},
        "question": ("axis 2 (cooperation, docs/126): how much of the robust window exists ONLY "
                     "because limiters close escape witnesses, as a function of rho"),
        "protocol": ("E7-a protocol unchanged (m0.35_n1, 4 adapted attackers x 24 eps, SEED0 "
                     "268000, no-fire, 12 variants, slew-simulated aim) + --coop: same tick/"
                     "seed/aim-axis judge recompute with limiters removed"),
        "metrics": {"C": "share of window ticks robust WITH limiters and not robust WITHOUT "
                         "(cooperation share), pooled over 4 slots",
                    "H": "share robust WITHOUT and not WITH (boxed_in harm) — report only"},
        "predictions": {
            "P-2a": "per aim: argmax_rho C(rho) has rho <= 4.0 -> SUPPORTED if both aims",
            "P-2b": "per aim: max C over rho >= 6.0 <= (1/3) max C -> SUPPORTED if both aims",
            "degenerate": ("if C = 0 at every rho for an aim -> UNDECIDABLE_C0 (scripted "
                           "limiter geometry never flips the judgment; axis-2 test deferred "
                           "to learned limiters: P-2c in E7-b and E7-c)"),
            "P-2c": ("E7-b readout: window-conditioned C-2 escape-shrinkage share of "
                     "t0.7_h1.0_cv (rho 3.93) > t0.5_h1.5_cv (rho 11.77) on >= 2 of 3 seeds; "
                     "undecidable if the log format does not allow window conditioning "
                     "(reported as such)"),
        },
        "limitations": ["limiters in the rollout are scripted -> C is a LOWER BOUND on what "
                        "learned limiters could contribute",
                        "old-world adapted attackers (non-co-evolved) — optimistic bias",
                        "no bit-reproduction claim vs E7-a (stochastic RL attacker); paired "
                        "within E7-a′ only"],
        "follow_ups_form_only": ["E7-c: transition-band (rho 2-3.5) learned points x {limiters "
                                 "armed / disarmed}, numbers sealed after the E7-a′ readout",
                                 "Prop 2 (user/K1 lane): rho*_eff under partial witness "
                                 "closure + boxed_in upper bound"],
        "not_evidence_for": ["cooperation vocabulary (limiter-control opportunity)",
                             "learned-limiter contribution (lower bound only)", "world ceiling"],
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load_e7a2() -> dict:
    data = json.loads(MANIFEST_A2.read_text(encoding="utf-8"))
    if data != build_e7a2():
        raise ValueError(f"E7-a′ manifest drift: {MANIFEST_A2}")
    return data


def main() -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    for path, body in ((MANIFEST, build_e7a()), (MANIFEST_B, build_e7b()),
                       (MANIFEST_A2, build_e7a2())):
        path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{path} {body['manifest_hash']}")


if __name__ == "__main__":
    main()
