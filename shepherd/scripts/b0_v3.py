"""B0 v3 hybrid-mission world contract 봉인 (docs/94 이행 — 코드보다 문서 먼저).

    python -m shepherd.scripts.b0_v3

서술 정본 = `docs/94_b0_v3_world_contract_draft.md` (결재 ①~⑦ 반영).
기계 정본 = 이 스크립트가 내는 `artifacts/b0/b0_v3_world_contract.json`.
Exit = B2_WORLD_CONTRACT_FROZEN — 이 봉인 뒤에만 B2 scripted / MARL 진입 가능.

격자는 **하드코딩하지 않는다**: 봉인된 R2a 산출물 (stage3_protocol · stage2_readout ·
scout_l2_envelope) 에서 유도해 provenance 사슬을 유지한다. 계약 조항의 기계 검증은
`tests/test_b0_v3_contract.py` (11 tests) 가 담당한다.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

R2A = ROOT / "artifacts/r2a"
R2B = ROOT / "artifacts/r2b"
ETAS = [2.1, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9]
STEP = 0.02                 # R2a micro-grid lattice step
EXT = 0.04                  # 2 lattice steps — base outer offset == extension step


def _load(p: pathlib.Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def build_grid() -> dict:
    """R2a Stage 3 구조에서 base 격자를 유도한다 (재설계 아님 — 인용)."""
    st3 = _load(R2A / "stage3_protocol.json")
    s2 = _load(R2A / "stage2_readout.json")["rows"]                 # lam0, confirmatory
    sc = _load(R2A / "scout_l2_envelope.json")["rows"]              # lam2, exploratory
    rows = []
    for sl, meta in sorted(st3["slices"].items()):
        for eta in ETAS:
            pair = sorted(c[1] for c in st3["cells"]
                          if c[0] == int(sl) and abs(c[2] - eta) < 1e-9)
            assert len(pair) == 2, (sl, eta, pair)
            lo, hi = (round(x, 4) for x in pair)
            c50 = (s2[str(eta)]["chi50_isotonic"] if sl == "0" else sc[str(eta)]["chi50"])
            rows.append({
                "lam_slice": int(sl), "lam": meta["lam"], "R_max": meta["R_max"],
                "eta": eta, "r2a_chi50": round(float(c50), 4),
                "chi50_provenance": ("stage2_readout (n=4800, confirmatory)" if sl == "0"
                                     else "scout_l2_envelope (n=480, EXPLORATORY scout)"),
                "chi_base": [round(lo - EXT, 4), lo, hi, round(hi + EXT, 4)],
            })
    assert len(rows) == 14
    return {
        "G": len(rows),
        "row_definition": "one (eta, lambda) pair = one row",
        "inherits_cells_rule": st3["cells_rule"],
        "lattice_step": STEP,
        "base_points_per_row": 4,
        "base_rule": "{chi_lo - 0.04, chi_lo, chi_hi, chi_hi + 0.04}; chi_lo/chi_hi are the "
                     "R2a nearest-inside / nearest-outside micro-grid points bracketing that "
                     "slice's chi50. Symmetric support about chi50 (approx -0.05, -0.01, "
                     "+0.01, +0.05) — deliberately NOT tilted toward positive shift.",
        "direction": "chi = a*tau0^2/(2*rho): chi UP = more agile attacker = harder. "
                     "INSIDE (capture-likely) is BELOW chi50.",
        "n_per_cell_per_seed": 300,
        "arms": ["B-3", "B-4", "B-5"], "seeds_min": 3, "pairing": "paired CRN",
        "attacker_primary": "A2-nominal ONLY — primary claim is conditioned as "
                            "chi50^net(eta, lambda | A2-nominal). A-family robustness is a "
                            "separate layer-3 (W10) frozen-policy arm; pooling with primary "
                            "is FORBIDDEN.",
        "threat_bracket_check": "every base cell satisfies a in [11,78], v in [8,30] "
                                "(realized a 16.5..27.5, v 12.4..23.0) — the bracket does not "
                                "bind in this chi range; the binding constraint is budget.",
        "extension_rule": {
            "statement": "Base grid is 4 points/row. If the isotonic fit of ANY arm x seed has "
                         "its p=0.5 crossing censored outside the sampled range, extend in that "
                         "direction by 2 lattice steps (0.04). Extension cells are added for ALL "
                         "arms x ALL seeds of that row under the SAME CRN. After at most TWO "
                         "extensions per direction, stop and report a one-sided bound.",
            "trigger": "CENSORING ONLY — never effect size. Extending because an effect 'looks "
                       "large' is adaptive cherry-picking and is forbidden.",
            "row_scope": "a single censored arm x seed extends the WHOLE row (seed-level chi50 "
                         "feeds the majority rule, so one truncated seed breaks it)",
            "upper": ["hi+0.04", "hi+0.08", "hi+0.12"],
            "lower": ["lo-0.04", "lo-0.08", "lo-0.12"],
        },
        "lam2_anchor_status": "lambda = 3.574 base grid centering uses the pre-existing "
                              "exploratory scout estimate; all learned-arm comparisons on this "
                              "grid are fresh confirmatory evaluations. The scout estimate is "
                              "NOT itself re-promoted as confirmatory evidence.",
        "rows": rows,
    }


def build() -> dict:
    lat = _load(R2A / "lattice_R2a_P3.json")
    st3 = _load(R2A / "stage3_protocol.json")
    b0v2 = _load(R2B / "b0_world_contract.json")
    payload = {
        "schema": "b0-v3-hybrid",
        "contract": "B0 v3 — hybrid net/kinetic mission world contract",
        "narrative_source": "docs/94_b0_v3_world_contract_draft.md",
        "question": "Does learned cooperative shaping move the clean-net-capture boundary "
                    "chi50^net(eta, lambda | A2-nominal) relative to rule-based control, under "
                    "a hybrid mission in which net failure hands off to a scripted kinetic "
                    "fallback?",

        "world": {
            "inherits": {"lattice_R2a_P3": lat["lattice_hash"],
                         "stage3_protocol": st3["protocol_hash"],
                         "r2b_b0_v2": b0v2["b0_hash"]},
            "fidelity": "reduced-order 3DOF, FROZEN. The map is chi50 = F(eta, lam | M_3DOF, "
                        "sealed world); 6DOF transfer is a separate transportability gate "
                        "(docs/93), never part of this campaign.",
            "frozen": "legacy 24 m corridor · A2-reactive adversary (jink 0.6 / route 0.5 / "
                      "sense 30) · capability-ratio family (mu, nu, kappa, N pinned) · same "
                      "judge and labels as R2a/R2b",
            "system_flags": "ratified F-contract: SystemSpec(enabled=True, "
                            "contact_resolver=True, miss_terminates=False) + "
                            "capture_terminates=True, p_kill=1.0, r_nk=6.0*r, "
                            "tau_kill=q_kill*tau0",
            "machine_identity": "resolved-contract manifest (m4_env.contract_manifest, schema "
                                "resolved-contract-v1). train/eval/sweep/scripted MUST share one "
                                "manifest hash; manifest_mismatch(a,b) == [] (test t8).",
        },

        "time_structure": {
            "tau0": {"value_s": 0.30, "role": "post-fire characteristic delayed-effect scale",
                     "phrasing": "tau0 is implemented through both the fire-time viability "
                                 "horizon and the delayed outcome-resolution timer",
                     "forbidden_phrasing": "'physically realized' alone (misreads as net "
                                           "ballistic integration; this world is reduced-order)"},
            "q_dec": {"value": "1/6", "status": "pinned temporal-resolution conditioning",
                      "note": "dt_phys = Delta_t_dec = 0.05 s coupled"},
            "q_race": {"value": "1/3", "status": "contract-fixed ratio (tau_lock/tau0)"},
            "q_kill": {"value": "1/2", "status": "contract-fixed ratio (tau_kill/tau0)"},
            "NOT_total_delay": "tau0 is NOT the total FIRE-to-terminal-resolution delay. "
                               "tau0 = 0.30 (viability/deployment) · q_race*tau0 = 0.10 "
                               "(application + race) · TOTAL pending = (1+q_race)*tau0 = 0.40 s "
                               "= 8 ticks. Always state all three.",
            "W_net": "vacuous — capture is a single fire-time frozen predicate, so there is no "
                     "capture-capable lifetime channel. omega_net is NOT promoted.",
            "canonical_claim_form": "For the sealed reduced-order world at fixed "
                                    "temporal-resolution conditioning q_dec = 1/6 and fixed "
                                    "timer ratios (q_race = 1/3, q_kill = 1/2), the net-capture "
                                    "boundary is characterized in (chi, eta, lambda).",
            "forbidden_interpretations": [
                "causal reading of q_dec (cadence and numerical resolution move together)",
                "smooth extrapolation to tau0 -> 0 (singular instantaneous-effector limit)",
                "decomposition of a 'sensing' latency component (none exists)"],
        },

        "observation": "noiseless, zero-latency: defender observation and the FIRE decision "
                       "inputs are computed from the current-tick TRUE state (t_obs == t_fire, "
                       "so tau_real == tau_deploy by construction). Sensor noise / latency / "
                       "actuator lag are NOT wired; they are an implementation decision deferred "
                       "to layer-3 (W10+) robustness, outside the nominal world (test t3).",

        "layer1_closure": "Layer-1 physical/environment sensitivity audit completed with no "
                          "clean executable perturbation candidate under the current simulator "
                          "architecture. Candidate effects were either already promoted/pinned, "
                          "absent from the implemented world, physically vacuous, or confounded "
                          "by coupled temporal resolution. No additional physical coordinate was "
                          "promoted before B0 v3. Stratification variables are (chi, eta, lambda, "
                          "A) only. Forbidden wording: 'no further sensitivity', 'robustness "
                          "demonstrated', 'sensitivity verified'.",

        "mission": {
            "states": {"NET_PRE": "FSM LOADED and k >= 1",
                       "NET_PENDING": "FSM DEPLOYING U LOCKED — (1+q_race)*tau0 = 0.40 s (8 ticks)",
                       "KINETIC": "from the control tick AFTER NET_SPENT is confirmed"},
            "mode_bit": "already in the observation (env.py FSM 4-state one-hot + k_norm + timer)",
            "K": 1,
            "fire_transition": "fire_event == (prev LOADED) and (now DEPLOYING); requires "
                               "fire_cmd == 1 AND v_shot_soft >= theta_fire, enforced inside the "
                               "FSM (single gate R2). CommitMeta and the capture value are FROZEN "
                               "at the fire tick: pending_capture = (not boxed_in) and "
                               "(v_shot_worst >= 1.0).",
            "fire_gate": {
                "statement": "Learned fire timing subject to a fixed admissibility gate. The "
                             "Bernoulli fire head selects firing TIMING within the fixed "
                             "theta_fire-admissible region; it does not learn the gate. Where "
                             "v_shot_soft < theta_fire a FIRE command is a no-op (test t9).",
                "forbidden_claim": "any claim that the learned controller relieves or recovers "
                                   "the existing gate's censored region",
                "conservatism_measurement": "forced-fire micro-arm (evaluation/probe only — "
                                            "never inside the training path)"},
            "net_capture_predicate": "NET_CAPTURE == CAPTURED and episode-accumulated contact == "
                                     "empty. This is the AUTHORITATIVE predicate (the one R2a/R2b "
                                     "used). Three non-authoritative copies exist and must never "
                                     "be used for N: env_sys._outcome_label (checks contact only "
                                     "at the terminal tick), RewardSpec.terminal (CWC = +b_net — "
                                     "superseded, see metrics), m4_env.label_rates (p_net lumps "
                                     "NET_CAPTURE + CWC).",
            "net_spent": "real and read directly: FSM SPENT + env_sys.net_spent / net_spent_step. "
                         "No new predictive judge; no fixed T_valid parameter. NET_SPENT => "
                         "NET_FAIL_shot for the ordinary un-captured shot-exhaustion path only — "
                         "illegal contact / crash / out-of-bounds are H_illegal / F_other "
                         "(test t4).",
            "continuation": "miss_terminates=False suppresses ONLY the spent-fail termination; "
                            "captured / penetrated / hard_kill terminations are never suppressed. "
                            "The scripted PN fallback then takes over.",
            "rl_credit_cut": {
                "rule": "NET_FAIL ends RL CREDIT, not the physical mission. MAPPO "
                        "rollout/GAE/return treat it as terminal; the training wrapper returns "
                        "terminal at net_spent and resets immediately. PN fallback continuation "
                        "lives only in the system-evaluation sidecar.",
                "implementation_trap": "do NOT implement the cut as SystemSpec(miss_terminates="
                                       "True) — that changes the world flags and splits the "
                                       "train/eval manifest hash (test t8). Cut in the TRAINING "
                                       "WRAPPER layer; world flags stay on the F-contract.",
                "fire_gradient": "the fire action's policy gradient uses only pre-NET_FAIL "
                                 "net-task return; post-fail kinetic outcome enters neither "
                                 "reward nor value target."},
            "kinetic_fallback": "scripted PN takeover, called the REFERENCE fallback ('a "
                                "conservative lower bound' is not permitted until learned kinetic "
                                "is shown to beat PN consistently). Kill chain: contact -> "
                                "tau_kill (= q_kill*tau0 = 3 ticks) -> no-kinetic-zone veto -> "
                                "geometry -> Bernoulli(p_kill) -> hard_kill.",
        },

        "contact_semantics": {
            "predicate": "per tick, on the PRE-move state, ||p_att - p_lim_i|| <= kill_radius "
                         "(same predicate as env.py limiter_loss), accumulated over the episode",
            "latch": "Irreversible illegal-substitution latch. The first body contact occurring "
                     "in NET_PRE or NET_PENDING sets C_illegal = 1. The episode's science outcome "
                     "is H_illegal regardless of any subsequent capture, and no later capture may "
                     "be restored as success or reward. The physical rollout continues wherever "
                     "the implemented world continues it — the latch is an OUTCOME/CREDIT rule, "
                     "NOT a termination rule.",
            "why_not_terminal": "termination is region-dependent in the implemented world "
                                "(test t10): outside the no-kinetic zone a contact is consumed -> "
                                "Bernoulli(p_kill=1.0) -> KILL -> terminal; inside it is "
                                "VETO_NO_KINETIC (detonation withheld, limiter not consumed) and "
                                "does NOT terminate, so a later capture can still occur. Writing "
                                "'illegal contact is immediately terminal' would be false.",
            "vocabulary": "'contact' here is a close-in kinetic ENGAGEMENT OPPORTUNITY, not a "
                          "physical collision (kill_radius is the execution radius of an "
                          "explosive intercept; docs/57 audit B). An NK veto is a withheld "
                          "detonation, so it is still a doctrine violation and still latches.",
            "legitimate": "contact while m == KINETIC is part of the kinetic success predicate, "
                          "not a penalty",
        },

        "metrics": {
            "partition": "exactly one bin per episode: N (clean net capture) | H_fb (post-"
                         "NET_FAIL legitimate kinetic neutralization) | H_illegal (kinetic "
                         "contact during NET_PRE/NET_PENDING) | F_other (timeout, crash, "
                         "out-of-bounds, ...)",
            "science": "chi50^net(eta, lambda | A2-nominal); N = 1, H_illegal = 0, H_fb = 0, "
                       "abstention = 0. NO censoring correction — not firing is a failure.",
            "system": "P_U = P_N + P_{H_fb} (H_illegal excluded)",
            "safety": "P_{H_illegal} reported separately as a doctrine-violation rate, split "
                      "into (i) actual KILL and (ii) NK-veto withheld detonation (veto_events) — "
                      "operationally different events, never reported as one number",
            "cwc_reward_supersede": "For the hybrid mission, the ratified CAPTURE_WITH_CONTACT = "
                                    "+b_net terminal (docs/66 r1 Q1) is SUPERSEDED. CWC and any "
                                    "illegal pre-net contact receive no clean-capture reward; the "
                                    "magnitude of r_illegal is sealed in the training contract.",
            "no_summation": "the two layers are never summed into a learning objective",
        },

        "grid": build_grid(),

        "boundary_rule": {
            "form": "row / slice / global, inheriting the R2b P1 rule form",
            "row": "row-positive requires >= 2/3 seeds with paired Delta > 0 (seed majority is "
                   "applied ONCE, at the row level)",
            "row_gate": "at least ceil(6G/7) = 12 of G = 14 rows are row-positive",
            "slice_gate": "within each lambda slice, at least 5 of 7 rows are row-positive",
            "global": "seed-preserving hierarchical paired summary with a positive effect; with "
                      "only 3 clusters this is NOT presented as a precise 95% frequentist "
                      "guarantee — it is supporting evidence. Real robustness is read from "
                      "2/3-seed consistency + effect size + paired scenario evidence together.",
            "operational_order": ["per seed: scenario-paired row Delta",
                                  "row-positive flag if >= 2/3 seeds positive",
                                  "count row / slice gates on those flags",
                                  "global effect computed separately"],
            "rejected": "seed-pooled point estimates for the row/slice gates — (+0.30, -0.02, "
                        "-0.02) averages positive, letting one seed's success mask two failures",
            "decomposition_log": "per-cell P(FIRE|chi) and P(N|FIRE, chi) are logged for every "
                                 "arm; with a fixed gate, P(FIRE|chi) is WHEN the policy fired "
                                 "inside the admissible region, never gate movement",
            "sealed_before": "learned results are read",
        },

        "same_tick_precedence": {
            "1": "raw CAPTURED resolution AND body contact -> H_illegal (clean capture requires "
                 "contact == 0; 'NET_CAPTURE and contact' is definitionally impossible wording)",
            "2": "NET_SPENT and same-tick capture -> N",
            "3": "KINETIC starts the control tick AFTER NET_SPENT (off-by-one guard so the last "
                 "valid tick's limiter contact is not misread as legitimate)",
            "4": "Same-tick capture-penetration precedence. During NET_PENDING, penetration "
                 "occurring BEFORE the capture-resolution tick terminates the episode as "
                 "PENETRATED. If the delayed capture resolves on the SAME DISCRETE TICK on which "
                 "the penetration predicate becomes true, CAPTURE takes precedence. This is a "
                 "sealed discrete-time tie rule; it does NOT claim continuous-time physical "
                 "ordering.",
            "counter": "capture_penetration_same_tick is logged always, and NEVER used to decide "
                       "the precedence. If it turns out frequent, that is attacked as a "
                       "dt-sensitivity / continuous-event-resolution question in layer-3.",
            "single_definition": "mission_rollout.terminal_label() — run_episode and "
                                 "recoverability_probe._Driver both route through it (test t5)",
            "sham_note": "env_sys's 'penetration first' clause is sham-net only "
                         "(capture_terminates=False) and does not apply here",
        },

        "R_rec": {
            "definition": "R_rec = (p_learned - p_A) / (p_C - p_A), same S_C, same world, same "
                          "success semantics (NET_CAPTURE only)",
            "naming": "p_C is NOT an upper bound, so R_rec > 1 is possible — the name 'fraction "
                      "of upper bound recovered' is FORBIDDEN",
            "status": "descriptive secondary metric, not a gate",
            "evaluation_set": "computed ONLY on the secondary R2b exact S_C replay set (28 cells "
                              "x 100 scenarios); computing it from the primary grid is forbidden, "
                              "and the two sets are never averaged together",
        },

        "non_claims": [
            "no 6DOF / real-airframe transportability claim (docs/93 is a separate gate)",
            "no boundary collapse across all latency scales",
            "no causal claim about decision cadence (q_dec is conditioning)",
            "no net-persistence physics (W_net is vacuous; implementing it would be B0 v4)",
            "no observation noise / latency / actuator lag (absent; measured in layer-3 as "
            "departures from nominal, not folded into nominal)",
            "no cooperation-necessity claim (R2b showed only that a limiter-control opportunity "
            "exists)",
            "no learned kinetic (KINETIC is a scripted reference fallback)",
            "no learned firing gate (theta_fire is a fixed admissibility constraint)",
            "no rescue after the C_illegal latch",
            "no mixing of primary-grid and S_C-replay numbers",
        ],

        "decisions": {
            "1_same_tick_precedence": "CAPTURE first, as a sealed discrete-time tie rule",
            "2_seed_rule": "per-seed majority (>= 2/3) AND global positive effect; "
                           "seed-preserving hierarchical paired CI",
            "3_f1_freeze_exception": "comment-only hygiene fix in env.py L305-308; executable "
                                     "semantics unchanged; registered in docs/09",
            "4_cwc_reward": "APPROVE supersede of docs/66 r1 Q1 for the hybrid mission",
            "5_c_illegal": "irreversible failure latch, NOT immediate termination",
            "6_fire_gate": "retain the hard theta_fire gate as an admissibility constraint",
            "7_grid": "G = 14, base 4 chi/row (symmetric), n = 300/cell/seed, A2-nominal only, "
                      "censoring-triggered +/-0.04 extension up to twice per direction; "
                      "lambda = 3.574 retained with explicit scout provenance",
        },

        "gates": [
            "contract tests tests/test_b0_v3_contract.py (11) must pass before any B2 / MARL run",
            "q_dec = 1/6 and timer ratios q_race = 1/3, q_kill = 1/2 asserted from the manifest",
            "train/eval resolved-contract manifest hashes identical",
            "B0 v3 seal timestamp must precede every B2 / MARL execution",
            "no cooperative learning experiment before this seal (docs/89 sect-2)",
        ],
        "exit": "B2_WORLD_CONTRACT_FROZEN",
    }
    payload["b0_hash"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    out = ROOT / "artifacts/b0/b0_v3_world_contract.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
    return payload


if __name__ == "__main__":
    p = build()
    g = p["grid"]
    print(f"B0 v3 sealed  b0_hash {p['b0_hash']}  exit {p['exit']}")
    print(f"  grid: G={g['G']} rows x {g['base_points_per_row']} chi "
          f"x n={g['n_per_cell_per_seed']} x {len(g['arms'])} arms x {g['seeds_min']} seeds "
          f"= {g['G'] * g['base_points_per_row'] * g['n_per_cell_per_seed'] * len(g['arms']) * g['seeds_min']:,} base episodes")
    print(f"  inherits: {p['world']['inherits']}")
