"""R2b B0 world-contract 봉인 (docs/81 §B0 이행 — 코드보다 문서 먼저).

    python -m shepherd.scripts.r2b_b0

Exit = B2_WORLD_CONTRACT_FROZEN. 설계 감사 = docs/review_prompt_r2b_redesign.txt
(r1~r5). 이 봉인 뒤에만 Phase 1 실행 가능; manifest 가 B0 timestamp < 실행을 검증.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def build() -> dict:
    l3 = json.loads((ROOT / "artifacts/r2a/lattice_R2a_P3.json").read_text(encoding="utf-8"))
    s3 = json.loads((ROOT / "artifacts/r2a/stage3_protocol.json").read_text(encoding="utf-8"))
    aborted = json.loads((ROOT / "artifacts/r2b/phase1_v1_aborted/ABORT_MANIFEST.json")
                         .read_text(encoding="utf-8"))
    branch = json.loads((ROOT / "artifacts/r2b/c_budget_branch.json").read_text(encoding="utf-8"))
    payload = {
        "schema": "r2b-b0-v2", "contract": "R2b",
        "amendment_status": {
            "supersedes_b0_v1": "e3fd7800003d34e1",
            "statement": "This amendment was triggered prospectively by the first valid "
                "occurrence of a previously structurally inaccessible terminal class "
                "(HARD_KILL) after limiter motion was enabled. Before amendment, 578 arm "
                "records from 289 scenarios had been generated; one HARD_KILL was observed "
                "in arm B and none in arm A. No cooperative effect estimand or boundary "
                "statistic was computed. All pre-amendment Phase-1 records were quarantined "
                "and excluded from confirmatory inference, and v2 restarted from a fresh "
                "CRN namespace.",
            "quarantine_manifest": aborted["manifest_hash"],
            "inherited_by_reference": {
                "oracle_server_benchmark": "pre-outcome infrastructure evidence",
                "c_budget_branch": branch["branch_hash"],
                "selected_C_design": branch["selected_C_design"]}},
        "question": "How far does limiter cooperation move the hold nominal boundary "
                    "chi50(eta, lam), and how does rule-based cooperation compare with "
                    "the achievable improvement found by a sealed-budget optimization "
                    "benchmark? (the former 'oracle upper bound' phrasing is RETIRED)",
        "world": {
            "inherits": {"lattice_R2a_P3": l3["lattice_hash"],
                         "stage3_protocol": s3["protocol_hash"]},
            "frozen": "legacy 24 m corridor · A2-nominal sealed evasion vector · "
                      "q_dec = 1/6 · capability-ratio family · same judge/labels. "
                      "Environment fidelity FROZEN (reduced-order 3DOF): the map is "
                      "chi50 = F(eta, lam | M_3DOF, sealed world); 6DOF transfer is a "
                      "separate transportability gate, never part of this campaign.",
            "identity_clause": "single/cooperative boundaries share the same world, "
                               "same adversary, same judgment (docs/87 sect-7 inherited)"},
        "treatment": {
            "single_difference": "the ONLY difference between arm A and arm B is the "
                                 "limiter controller/motion (hold vs rule-based "
                                 "intercept). Commit logic, fire logic, attacker "
                                 "controller, capability limits, judge, and the initial-"
                                 "condition distribution are identical.",
            "machine_assert": "the runner compares the resolved configs of A and B and "
                              "asserts equality of every field except the limiter arm "
                              "flag — otherwise Delta_coop is a bundle effect and the "
                              "run aborts",
            "reuse_note": "'curve_intercept reuse' means reuse of the controller/config/"
                          "code — NEVER reuse of old results. Arm A is measured fresh "
                          "(paired CRN); R2a values serve only as a cross-campaign "
                          "consistency check."},
        "contract_7A_7E": {
            "7A_observability": "unchanged: attacker senses limiters within sense_range "
                                "(sigma_dt ~17); defender full state; no new channels",
            "7B_commit": "global instantaneous commit-bit (unchanged; A/B identical, so "
                         "internal causal comparison is unaffected by its realism limit)",
            "7C_time_decomposition": "NOT introduced as an experimental axis. Event "
                                     "timestamps (commit step, first limiter-reaction "
                                     "step) ARE logged in raw records — descriptive "
                                     "diagnostics only, forbidden in inference or gates",
            "7D_route_post_commit": "unchanged semantics, stated explicitly",
            "7E_train_eval_parity": "not a blocker for scripted arms; re-checked before "
                                    "any learned arm"},
        "arms": {
            "A": "hold (single) — fresh paired measurement",
            "B": "rule-based cooperation (curve_intercept lower-bound controller)",
            "C": {"name": "sealed-budget optimization achievability benchmark "
                          "(code name p2prime/oracle-lite; paper vocabulary: "
                          "'search-based achievability benchmark' — NOT an upper bound)",
                  "definition": "C(s) = 1 iff the sealed search (3 solver seeds x 384 "
                                "rollouts, K_SEG=4 piecewise-constant plans, closed-loop "
                                "attacker, full-fidelity replay judgment) finds at least "
                                "one admissible limiter plan achieving capture on "
                                "scenario s",
                  "estimand": "p_C_hat = scenario-wise attainment rate of the sealed "
                              "search procedure — explicitly NOT the physical "
                              "achievability probability (unfound feasible plans may "
                              "exist)",
                  "pairing": "S_C = S_AB[0:100] — the prespecified first 100 scenario "
                             "ids of each cell's A/B stream (nested paired); solver-"
                             "search seeds are managed separately from scenario RNG",
                  "scale_rule": "server benchmark FIRST (3 solves x {full, lite} budgets "
                                "on old MISS_EPISODES, record mean AND max sec/solve; "
                                "no new R2b seeds). Then T_proj = 2800 * t_lite_mean / "
                                "N_shard. SEALED THRESHOLD: T_proj <= 14 h -> "
                                "UNCONDITIONAL lite C over all 28 cells x n=100; "
                                "T_proj > 14 h -> predeclared fallback = sentinel 6 rows "
                                "(eta {2.1, 3.0, 3.9} x lam {0, 2}) x n=50 lite. The "
                                "threshold is an operating budget fixed BEFORE the "
                                "benchmark result is seen."}},
        "cells": {"source": "Stage 3 band cells (28) from protocol " + s3["protocol_hash"],
                  "crn": {"ns": "r2b_p1_v2", "seed0": 7000,
                          "fresh_stream": "v1 scenarios (289) are never reused — outcome-"
                                          "class information was partially viewed, so v2 "
                                          "draws a fresh stream; S_C = S_AB_v2[0:100]",
                          "jitter": {"chi": 0.01, "eta": 0.15},
                          "pairing": "A and B run inside one scenario; C on the nested "
                                     "subset"},
                  "n_per_cell_AB": 400},
        "estimands": {
            "phase1_primary": "paired Delta_p_coop = p_B - p_A per cell",
            "p1_positive_rule": ">=12/14 rows with positive point estimate AND >=5/7 "
                                "positive rows within each lam slice AND equal-weight "
                                "global paired CI95 lower bound > 0 (scenario-paired "
                                "bootstrap B=4000) — sealed numbers",
            "phase2_primary": "Delta_chi50_coop(eta, lam) = chi50_coop - chi50_hold "
                              "(conditional on Phase 1 displacement; scout -> band, "
                              "R2a two-step discipline)",
            "secondary": "Delta_lam_coop(eta) = Delta_chi50(eta, lam2) - "
                         "Delta_chi50(eta, lam0) — lambda dependence of the cooperation "
                         "effect; two-slice vocabulary only",
            "n2_rule": "Phase 2 confirmatory n2 = max(400, ceil(1.96^2 * q_hat / "
                       "0.05^2)), q_hat = pooled paired discordance blinded to signs, "
                       "cap 1000, effect sizes never consulted"},
        "readout_3cases": {
            "B_pos_C_pos": "cooperative boundary gain established; report the fraction "
                           "of the search-benchmark improvement realized by the "
                           "rule-based controller (per cell, descriptive)",
            "B_null_C_pos": "cooperation-is-meaningless is rejected; the rule-based "
                            "controller failed to realize exploitable cooperative "
                            "geometry — 'motivates a learned or more expressive "
                            "cooperative controller' (NOT 'MARL will solve it')",
            "B_null_C_null": "EXACT sealed sentence: 'No cooperative boundary gain was "
                             "detected either with the rule-based controller or by the "
                             "sealed p2prime solver class at the tested lite search "
                             "budget.' — 'genuine physical null' and design conclusions "
                             "('tau reduction instead of cooperation') are FORBIDDEN "
                             "without separate argument"},
        "competing_risk_semantics": {
            "arm_A": "HARD_KILL => STOP (hold limiters cannot kinetically kill; any "
                     "occurrence signals a world-contract violation or harness fault)",
            "arm_B": "HARD_KILL is a VALID terminal outcome — the downstream consequence "
                     "of the single treatment (limiter motion), not a new treatment; "
                     "p_kill, kill radius and judge are identical across arms. Never "
                     "dropped, never recoded.",
            "estimand_layers": {
                "primary": "Delta_p_net = p_N^B - p_N^A, p_N = P(Y = NET_CAPTURE) — "
                           "HARD_KILL counts as a net-capture failure",
                "secondary": "Delta_p_neutralization on p_U = P(Y in {NET, HARD})",
                "reported": "p_H = P(Y = HARD_KILL) per arm and cell — with mutually "
                            "exclusive terminals p_U = p_N + p_H, so the three numbers "
                            "separate genuine net-boundary movement from kinetic "
                            "substitution",
                "forbidden": "conditional estimands such as P(NET | no HARD_KILL) are "
                             "never primary",
                "p1_rule_layer": "the sealed P1-positive rule applies to the "
                                 "Delta_p_net layer"},
            "C_arm_semantics": "C_N(s) = 1 iff the sealed search finds a plan achieving "
                               "NET_CAPTURE (a rollout ending in HARD_KILL does NOT count); "
                               "C_U and C_H recorded as secondaries. The 3-way readout "
                               "table is defined on (B_N, C_N); neutralization outcomes "
                               "are a separate secondary readout. This closes the "
                               "loophole where a 'positive' C built purely on kinetic "
                               "kills would falsely support the "
                               "learned-cooperative-controller sentence."},
        "gates": ["HARD_KILL STOP — ARM A ONLY (see competing_risk_semantics)",
                  "q_dec = 1/6 runtime assert",
                  "single-treatment-difference assert (see treatment.machine_assert)",
                  "B0 seal timestamp must precede every R2b execution (manifest check)"],
        "supersedes": {
            "docs87_sect7": "2-D minimal design (6 cells x 2 arms, 'oracle upper bound' "
                            "wording) — superseded by this seal; historical text "
                            "retained in docs/87 with an append-only amendment",
            "reason": "C045 = PARTIAL_3D invalidated the 2-D coordinate lock; closure "
                      "audit fixed nominal-shift primary; oracle wording retired by "
                      "solver-class audit",
            "inherited_principles": ["same world/adversary/judge identity clause",
                                     "fresh-measurement rule for arm A",
                                     "two-branch null reading (in downgraded wording)",
                                     "money figure = hold vs coop curves on shared axes"]},
        "exit": "B2_WORLD_CONTRACT_FROZEN",
    }
    payload["b0_hash"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    out = ROOT / "artifacts/r2b/b0_world_contract.json"
    out.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    return payload


if __name__ == "__main__":
    p = build()
    print(f"B0 sealed  b0_hash {p['b0_hash']}  exit {p['exit']}")
    print(f"  threshold: {p['arms']['C']['scale_rule'].split('SEALED THRESHOLD: ')[1][:60]}...")
