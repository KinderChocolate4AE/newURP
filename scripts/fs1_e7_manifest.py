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
        "schema": "fs1-e7b-manifest-v1.1",
        "status": ("sealed after the E7-a readout (P_RHO1_SUPPORTED, harvest b5f8695) and the "
                   "P-rho2 registration (note 2026-10-08c), BEFORE any E7-b training. Scope = "
                   "user approval 2026-10-08 (5 variants: cv rho-ladder 4 + ma contrast 1). "
                   "v1.1 AMENDMENT (user-approved 2026-10-08, before any E7-b production or "
                   "result): P-2c measurement source moved from JAX C-2 training logs to the "
                   "canonical eval (frozen defense vs dedicated exploiter = the judgment "
                   "condition; no dependence on log format), with a minimum-signal floor "
                   "(E7-a2 lesson: its criteria had none and the verdict rested on 1-3 tick "
                   "counts). Production: server4 single GPU (server rule); 4090 != parity-seal "
                   "GPU -> full parity green required before production"),
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
                       "environment": "server4; seed band 276000+ never used in training",
                       "cli": ("shepherd.fs1.eval run --tau-scale/--theta-scale/--aim per "
                               "variant + --coop-window (window = LOADED and d <= 16 m; judge "
                               "recomputed with limiters removed, same seed and heading)")},
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
            "P-2c (v1.1, supersedes the docs/129 sec 7 log-based wording)": (
                "learned_det vs ex_judge, canonical eval: window-tick cooperation share C = "
                "n(robust with limiters and not without) / n(window ticks). Prediction: "
                "C(t0.7_h1.0_cv, rho 3.93) > C(t0.5_h1.5_cv, rho 11.77) on >= 2 of 3 seeds -> "
                "P_2C_SUPPORTED, else P_2C_NOT_SUPPORTED. MIN-SIGNAL FLOOR: if the 3-seed pooled "
                "C is < 0.01 in BOTH compared variants -> UNDECIDABLE_LOW_SIGNAL (the "
                "cooperation channel is not measurable, not falsified). C and H (boxed harm) "
                "reported for all 5 variants and all defenders (rho-profile of learned vs "
                "scripted limiters). JAX C-2 logs = secondary, report only"),
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
                    "e7b": "65ef3b86715458fa",   # 봉인 시점 E7-b v1 hash 고정 (이후 E7-b 정정이 이 봉인을 흔들지 않게)
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


# ---------------------------------------------------------------- E7-c ------
MANIFEST_C = ROOT / "artifacts" / "fs1" / "e7c_manifest.json"
C_CONDS = [{"name": "P1_armed", "tau_scale": 0.85, "theta_scale": 1.0, "limiters": "post_shot", "rho": 2.662},
           {"name": "P1_inert", "tau_scale": 0.85, "theta_scale": 1.0, "limiters": "inert", "rho": 2.662},
           {"name": "P2_armed", "tau_scale": 1.0, "theta_scale": 1.5, "limiters": "post_shot", "rho": 2.941},
           {"name": "P2_inert", "tau_scale": 1.0, "theta_scale": 1.5, "limiters": "inert", "rho": 2.941}]
C_SEED0, C_STRIDE = 278000, 1000


def build_e7c() -> dict:
    body = {
        "schema": "fs1-e7c-manifest-v1.3",
        "jseed_amendment_v1_3": ("2026-10-09, before any E7-c production (JAX-detected): the v1/v1.2 "
                                 "exploiter jseed bands overlapped numerically with E7-b "
                                 "(277000-281002) and E7-b2 (281000-285002) because bands 2000 "
                                 "apart each span ~4000 with stride 1000. No contamination "
                                 "(different worlds/defenses), but the disjoint-band rule was "
                                 "violated -> E7-c det exploiter jseed = 290000 + cond_idx*1000 + "
                                 "seed, sto exploiter jseed = 295000 + cond_idx*1000 + seed. These "
                                 "supersede the 279000 / 283000 bands written below. The E7-b vs "
                                 "E7-b2 overlap (already produced) is recorded as known and "
                                 "harmless"),
        "status": ("sealed 2026-10-08 on user approval ('fixed'), BEFORE any E7-b result and "
                   "before any E7-c production (contract: docs/130). v1.1 (user-approved, "
                   "still before any production/result): interpretation table fixed "
                   "(docs/130 section 7); gates unchanged. v1.2 (user-approved 2026-10-09, "
                   "after the E7-b readout, before any E7-c production/result): stochastic-"
                   "policy audit arm added (docs/130 section 9)"),
        "sto_audit_arm_v1_2": {
            "exploiters": "per condition x seed: fresh dedicated exploiter vs the frozen "
                          "STOCHASTIC defense (--exploit-sto), 1e7, jseed 283000 + cond_idx*1000 "
                          "+ seed (separate from the det exploiters, jseed 279000-band)",
            "judgment": ("two parallel lines, no preference (pre-declared): det line = section 3 "
                         "gates as sealed (learned_det vs det exploiter); sto line = the same "
                         "gate wording applied to learned_sto vs sto exploiter (P_RHO2L_S, "
                         "COOP_PUSHES_BOUNDARY_S) + the section 7 interpretation table; if the "
                         "lines disagree, report both and record the gap as an "
                         "unpredictability effect (never as emergence)"),
            "eval": "same seeds (278000 + cond_idx*1000), exploiter groups ex_judge and "
                    "ex_judge_sto",
        },
        "lineage": {"contract": "docs/130", "e7b": "543cd9e4b3582687 (v1.1, seal-time literal)",
                    "e7a2": "57b4faafba5d27bf", "p_rho2": "rho* = 2.813 (note 2026-10-08c)"},
        "question": ("does limiter-control opportunity (stage 1 of the original design: "
                     "cooperation -> net attempt -> kinetic fallback) push the net-capture "
                     "boundary near rho*; and does rho* hold at learning level in the "
                     "limiter-free (assumption A5) world"),
        "cell": {"cell": "m0.35_n1", "mu": 0.35, "nu": 1.0, "aim": "cv"},
        "conditions": C_CONDS, "seeds": [0, 1, 2],
        "rules": {
            "post_shot": ("limiter kinetic engagement (arm/commit path AND contact resolver) "
                          "allowed only after the finisher has fired (fsm leaves LOADED); "
                          "matches the judge's witness-closure semantics"),
            "inert": "physics.kill_radius = 0 (single config source: judge closure and kinetic "
                     "contact both off); limiters still move, observation structure unchanged",
            "no_cross_comparison": "E7-b uses ROE A; E7-c comparisons are internal only",
        },
        "production": ("per-condition new BC; arm C-1 recipe trained under each condition's "
                       "rule, 1.1e8; per-condition dedicated judge exploiter 1e7 (jseed "
                       "279000-band); server4 single GPU after E7-b"),
        "metric": ("D_shot = NET (NET_CAPTURE + CAPTURE_WITH_CONTACT) + kinetic kills inside "
                   "the shot window (after the shot, before net resolution); fallback kills "
                   "(after net miss) excluded and reported; pre-shot kinetic must be 0 under "
                   "post_shot (else run invalid); inert: D_shot = NET"),
        "evaluation": {"n": 240, "seed0": C_SEED0, "cond_seed_stride": C_STRIDE,
                       "cond_idx": "index in THIS manifest's conditions list",
                       "paired": True, "defenders": ["learned_det (judgment)",
                                                     "learned_sto (report)"],
                       "cli": "--tau-scale/--theta-scale/--aim + --limiter-roe post_shot | "
                              "--limiter-inert + --coop-window; episode kill_phase tag",
                       "environment": "server4; seed band 278000+ never used in training"},
        "gates": {
            "P-rho2L": ("D_shot(inert, P2) >= 29 AND D_shot(inert, P1) < 29 (each 2/3 seeds) "
                        "-> P_RHO2L_SUPPORTED, else NOT_SUPPORTED with direction"),
            "P-2d": ("at P1: D_shot(armed) >= 29 AND D_shot(armed) - D_shot(inert) >= +24 "
                     "(same-seed pairs, 2/3) -> COOP_PUSHES_BOUNDARY; P1 armed closed -> "
                     "COOP_NULL_BELOW; P2 armed - inert reported"),
            "mechanism_report": ("armed --coop-window C and H with min-signal floor 0.01 "
                                 "(LOW_SIGNAL below); D_shot gap not explained by C = "
                                 "trajectory-shaping candidate, reported as a range only"),
            "invalid": "budget/completion/paired/manifest/BC-lineage or post_shot violation",
        },
        "interpretation_P1_v1_1": {
            "delta": "D_shot(armed) - D_shot(inert) at P1, same-seed pairs; row by 2/3 majority",
            "closure_indicators": "C = armed coop-window share (3-seed pooled); K_sw = armed "
                                  "shot-window kinetic kills (kill_phase = shot_window)",
            "A_closure": "delta >= +24 and (C >= 0.01 or K_sw >= delta/2) -> contribution 3 "
                         "returns in its original form",
            "B_threat_shaping": "delta >= +24 and C < 0.01 and K_sw < delta/2 -> cooperation "
                                "real but via kinetic-threat trajectory shaping; contribution 3 "
                                "redefined",
            "C_null": "-24 < delta < +24 -> no net-cooperation effect in this regime; Paper 1 "
                      "without contribution 3, axis 2 explained by a geometry lemma, "
                      "cooperation question moves to Paper 2 (mode switching)",
            "D_harm": "delta <= -24 -> cooperation harmful near the boundary (boxed); as C_null "
                      "plus harm-mechanism report",
            "mixed": "no 2/3 majority -> MIXED, per-seed report only",
            "scope": "two points x 3 seeds, this net geometry, post-shot ROE, 1e7 exploiter; "
                     "no general statement about cooperation",
        },
        "follow_up_form_only": ("kappa = R_k / r (r = 0.5 a tau^2) as the axis-2 physical knob: "
                                "user derivation -> registered prediction -> learning-free "
                                "kill_radius probe after the E7-c readout; R_k x ROE learning "
                                "sweep moved to Paper 2"),
        "implementation_preconditions": ["FS1Spec.limiter_roe in {a (default, bit-exact), "
                                         "post_shot}", "FS1Spec.limiter_inert",
                                         "tests: default no-op; post_shot pre-shot kinetic 0 "
                                         "and post-shot contact possible; inert judge == "
                                         "limiters-removed judge and kinetic 0; eval kill_phase",
                                         "JAX parity: baseline golden + post_shot and inert "
                                         "one f64 spot-check each"],
        "not_evidence_for": ["world ceiling", "real-net representativeness",
                             "global rho cooperation profile (local test only)",
                             "cooperation vocabulary (limiter-control opportunity)",
                             "pooling with E7-a/b, arm C-1/D"],
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load_e7c() -> dict:
    data = json.loads(MANIFEST_C.read_text(encoding="utf-8"))
    if data != build_e7c():
        raise ValueError(f"E7-c manifest drift: {MANIFEST_C}")
    return data


# ---------------------------------------------------------------- E7-b′ -----
MANIFEST_B2 = ROOT / "artifacts" / "fs1" / "e7b2_manifest.json"
B2_JSEED0 = 281000


def build_e7b2() -> dict:
    body = {
        "schema": "fs1-e7b2-manifest-v1",
        "status": ("sealed 2026-10-09 on user approval, after the E7-b readout (E7B_NULL) and "
                   "BEFORE any E7-b2 exploiter training or result (contract: docs/129 section 8). "
                   "HONESTY FLAG: the hypothesis was motivated by already-seen UNAUDITED sto "
                   "ceilings (59-117/240 vs det-trained exploiters); the test itself (exploiters "
                   "trained vs sto) is unseen"),
        "lineage": {"contract": "docs/129 section 8", "e7b": "543cd9e4b3582687 (seal-time literal)",
                    "e7b_harvest": "576e55e", "defense_pin": "eef7c27 (E7-b checkpoints, not retrained)"},
        "question": ("in the opened net-physics worlds, does the frozen STOCHASTIC defense survive "
                     "a dedicated exploiter trained against it — i.e., has the remaining bottleneck "
                     "moved from window generation to predictability"),
        "variants": B_VARIANTS, "seeds": B_SEEDS,
        "exploiters": (f"per E7-b slot: fresh dedicated exploiter vs the frozen stochastic defense "
                       f"(--exploit-sto), {B_EX_STEPS:.0e}, same variant world flags, jseed "
                       f"{B2_JSEED0} + vi*1000 + seed"),
        "judgment_defender": ("learned_sto — PRE-DECLARED judgment-model change, this contract only "
                              "(arm D precedent); learned_det reported vs the same sto exploiter"),
        "evaluation": {"n": B_N, "seed0": B_SEED0, "variant_seed_stride": B_STRIDE,
                       "note": "same seed band as E7-b -> paired comparison with the det verdict",
                       "defenders": ["learned_sto (judgment)", "learned_det (report)"],
                       "group": "ex_judge_sto", "cli": "variant flags + --coop-window"},
        "gates": {
            "E7B2_OPENS": (f"per variant: ceil_learned_sto >= {B_CEIL_REF} + {B_MARGIN} = 29/{B_N} "
                           "on >= 2 of 3 seeds; none -> E7B2_NULL"),
            "P-rho3s": "cv ladder (4 points): seed-median ceil_sto monotone in rho, Spearman >= 0.7",
            "report": ["exploiter penetration (mean of last 10 win_rate)",
                       "paired det-vs-sto gap vs E7-b", "coop-window C and H"],
            "invalid": "budget (exploiter >= 1e7) / completion / paired / manifest / variant flags",
        },
        "not_evidence_for": ["emergence", "world ceiling", "pooling with E7-b det verdict "
                             "(paired comparison only)", "positive claims unconditional on 1e7"],
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load_e7b2() -> dict:
    data = json.loads(MANIFEST_B2.read_text(encoding="utf-8"))
    if data != build_e7b2():
        raise ValueError(f"E7-b2 manifest drift: {MANIFEST_B2}")
    return data


def main() -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    for path, body in ((MANIFEST, build_e7a()), (MANIFEST_B, build_e7b()),
                       (MANIFEST_A2, build_e7a2()), (MANIFEST_C, build_e7c()),
                       (MANIFEST_B2, build_e7b2())):
        path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{path} {body['manifest_hash']}")


if __name__ == "__main__":
    main()
