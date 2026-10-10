"""Seal E1 = 전이 사다리 (+ 계단 쌍, + 조건부 E6 a-arm) — docs/134.

    python scripts/fs1_e1_manifest.py      # 결과 보기 전 봉인 (artifacts/fs1/e1_manifest.json)
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "fs1" / "e1_manifest.json"

TAU0, DT, RHO_B = 0.3, 0.05, 1.9231          # FS1 기준 세계 ρ (E7-a probe consts)


def _deploy_ticks(tau):
    t, n = tau, 0
    while True:                                # finisher_fsm.py:96-101 와 같은 감산 (ε = 1e-9)
        n += 1
        t -= DT
        if t <= 1e-9:
            return n


def _pt(name, ts, role="ladder"):
    return {"name": name, "tau_scale": ts, "theta_scale": 1.0, "aim": "cv", "role": role,
            "rho": round(RHO_B / ts ** 2, 4), "tau": round(TAU0 * ts, 5), "deploy_ticks": _deploy_ticks(TAU0 * ts)}


LADDER = [_pt("r1.92", 1.0), _pt("r2.30", 0.915), _pt("r2.66", 0.85), _pt("r2.93", 0.81),
          _pt("r3.42", 0.75), _pt("r3.92", 0.7), _pt("r7.69", 0.5)]
PAIR = [_pt("p2.75", 0.83624, "tick_pair"), _pt("p2.78", 0.83171, "tick_pair")]
SEEDS = [0, 1, 2, 3, 4]
N = 240
SEED0, STRIDE = 330000, 1000                  # 평가 seed 대역 (미사용 대역)
JSEED_DET, JSEED_STO = 300000, 305000         # 착취자 jseed = 대역 + idx*100 + seed (E7-b/b2/c 대역과 분리)
JUDGMENT = {"defender": "learned_det", "group": "ex_judge"}
BAND = (2.427, 2.813)                         # 등록 ρ* 불확실 대역 (3.5dt, 4dt), 노트 10-08c
FIT_BOUNDS = {"lower": [0.0, 0.0, 0.5, math.log(1.5)], "upper": [1.0, 1.0, 50.0, math.log(8.0)]}
N_BOOT, MIN_STEP = 2000, 4 / 240
E6 = {"name": "e6_a10", "tau_scale": 1.0, "theta_scale": 1.0, "a_scale": 0.49, "mu": round(0.35 / 0.49, 4),
      "rho": round(RHO_B / 0.49, 4), "compare_to": "r3.92"}
# v1.1 amendment (2026-10-11, before any E6 production/data): second a-arm with the relative accel ratio fixed
E6B = {"name": "e6_a10_mu", "tau_scale": 1.0, "theta_scale": 1.0, "a_scale": 0.49, "mu": 0.35,
       "rho": round(RHO_B / 0.49, 4)}
E6_ARMS = [E6, E6B]                                # idx 9, 10
E6_MARGIN, E6_POS, E6_FLOOR = 8, 4, 4              # 중앙값 ±8/240, 5 seed 중 4, 바닥 = A2 net 중앙값 <= 4/240


def e6_label(d_seed, floor=False):
    """seed 짝 차이 d → 갈래. 의미 단위 테스트는 tests/test_fs1_eval.py (라벨 이름이 결론을 가리키는지)."""
    if floor:
        return "UNIDENTIFIABLE_FLOOR"
    d = sorted(d_seed); med = d[len(d) // 2]
    if med >= E6_MARGIN and sum(x > 0 for x in d) >= E6_POS:
        return "POSITIVE"
    if med <= -E6_MARGIN and sum(x < 0 for x in d) >= E6_POS:
        return "NEGATIVE"
    if abs(med) < E6_MARGIN:
        return "NULL"
    return "MIXED"


def build() -> dict:
    body = {
        "schema": "fs1-e1-manifest-v1.1",
        "amendment_v1_1": ("2026-10-11, after the AMI readout (E6 trigger ON) and BEFORE any E6 production or data, "
                           "user question + advisor Q1 = (B): the sealed a-arm (a x 0.49 with a_def fixed, mu 0.7143) "
                           "doubles the defender/attacker accel ratio (0.35 -> 0.71), confounding Lambda with "
                           "relative agility. Added second a-arm e6_a10_mu (a x 0.49, mu 0.35 -> a_def 3.51). Three "
                           "points at rho 3.92: T = r3.92, A1 = e6_a10, A2 = e6_a10_mu. Contrasts: A1 - A2 = "
                           "defender agility at fixed attacker; A2 - T = attacker+defender accel both halved "
                           "(ratio fixed, Lambda moves). Floor rule: if A2 net median <= 4/240 the A2 - T contrast "
                           "is UNIDENTIFIABLE_FLOOR. Original A1 - T rule kept and reported as sealed. Ladder, "
                           "pair and all other rules unchanged; no E1 evaluation data existed at amendment"),
        "status": ("sealed 2026-10-11 BEFORE any E1 production (contract: docs/134; user 'start now, maximize "
                   "evidence' 2026-10-11 — overrides the advisor's 'after 10/26' timing; design = advisor "
                   "2026-10-11 rounds 2-3). No E1 data exists at seal"),
        "lineage": {"contract": "docs/134", "recipe": "E7-b (fs1_e7_manifest e7b 543cd9e4b3582687): arm C-1 "
                    "distilled fire head, ROE A, m0.35_n1", "p_rho2": "rho* 2.813 / 2.427 (note 2026-10-08c)",
                    "ami": "docs/132 (E6 trigger)", "e4": "docs/133"},
        "question": ("does the registered window boundary rho* predict WHERE the learned net-capture ceiling "
                     "(matched dedicated-exploiter audit) turns on"),
        "ladder": LADDER, "tick_pair": PAIR, "seeds": SEEDS,
        "knob": ("tau only (theta 1.0, cv aim) so that the ladder is a single-knob family; E7-b points "
                 "are previous lineage, reported for reproduction only, never fitted"),
        "production": {
            "per point": "NEW BC (canonical bc.py, 3000 eps) -> arm C-1 recipe 1.1e8 -> det exploiter 1e7 "
                         "(jseed 300000 + idx*100 + seed) -> sto exploiter 1e7 (jseed 305000 + idx*100 + seed)",
            "idx": "index in ladder + tick_pair (ladder 0-6, pair 7-8), E6 A1 = 9, E6 A2 = 10",
            "priority": ["ladder det path (train + det exploiter), all 35 slots",
                         "tick pair det path (10 slots)", "E6 a-arms A1 + A2 (10 slots, triggered)",
                         "sto exploiters (report line)"],
            "hardware": "server4 single GPU (server rule); JAX learner (E7-b parity regime)",
        },
        "evaluation": {"n": N, "seed0": SEED0, "stride": STRIDE, "env_seed": 0,
                       "defenders": ["learned_det (judgment, vs ex_judge = det exploiter)",
                                     "learned_sto (report, vs ex_judge_sto)"],
                       "cli": "--tau-scale per point, --stack r4p --mu 0.35 --nu 1.0 --coop-window "
                              "--env-seed 0 --groups none; records rob_fire (first-fire robust judgment)"},
        "metric": {"primary": "net = NET_CAPTURE + CAPTURE_WITH_CONTACT, learned_det vs det exploiter",
                   "secondary": ("rob_fire = episodes whose first fire was robust at the fire instant "
                                 "(capture-scheduled; removes the deploy-tick resolution path)"),
                   "report": ["defended total", "rob_fire but penetrated before resolution", "sto line",
                              "realized deploy ticks per point (6 6 6 5 5 5 3; step at tau 0.25 s = rho 2.769)"]},
        "rho_half": {
            "model": "y = L + (U - L) / (1 + exp(-k (log rho - log rho_half))), y = net/240 per slot",
            "fit": f"least squares (scipy curve_fit), bounds {FIT_BOUNDS}, all 35 ladder slots",
            "ci": f"stratified percentile bootstrap (resample seeds within each rho point), {N_BOOT} reps, "
                  "rng seed 0",
            "no_transition": f"U - L < {MIN_STEP:.4f} (4/240) or fit failure -> NO_TRANSITION",
            "plateau": "nuisance parameter fitted jointly (advisor Q1); sensitivity: external plateau = "
                       "E7-b net_det median (report only)",
        },
        "branches (pre-registered three-way, CI rule)": {
            "EARLY": f"CI95 entirely < {BAND[0]} -> learned capture starts once a window merely exists "
                     "(rho0 side); the 4-step threshold is not needed",
            "AT_BOUNDARY": f"CI95 inside [{BAND[0]}, {BAND[1]}] -> rho* predicts the learned onset "
                           "(strongest result)",
            "LATE": f"CI95 entirely > {BAND[1]} -> the boundary is necessary only; onset set by the adversary",
            "UNDETERMINED": "CI crosses a branch edge",
            "discretization": ("primary and secondary branches differ -> DISCRETIZATION_SENSITIVE, no branch "
                               "claim"),
        },
        "tick_pair": "report: seed-median net(p2.75, 6 ticks) - net(p2.78, 5 ticks) = deploy-tick step effect",
        "e6_conditional_arm": {
            **E6,
            "trigger": "AMI (docs/132) det-line branch AMI_ADAPTIVE or AMI_ATTACKER_NONADAPTIVE; else not run",
            "world": ("requires a NEW FS1Spec a_scale knob (attacker a_att_max x 0.49 = 10.02) with mu' = "
                      "0.7143 so that a_def stays 7.16 m/s^2 (advisor round 2: a_def-absolute primary). "
                      "Default a_scale 1.0 must be bit-exact (test) + JAX parity spot-check before production"),
            "prediction": ("Lambda = V^2/(a R_max) doubles. Seed-paired d = net(e6) - net(r3.92): median d >= "
                           "+8/240 and >= 4 of 5 seeds positive -> LAMBDA_RAISES_CEILING; |median d| < 8 -> "
                           "CEILING_COLLAPSES_IN_RHO; median d <= -8 -> LAMBDA_LOWERS_CEILING; else MIXED"),
            "second_arm_v1_1": {**E6B, "contrasts": {
                "A1 - A2 (defender agility, attacker fixed)": "seed-paired d = net(e6_a10) - net(e6_a10_mu) -> e6_label",
                "A2 - T (Lambda at fixed accel ratio)": "seed-paired d = net(e6_a10_mu) - net(r3.92) -> e6_label, "
                                                      "UNIDENTIFIABLE_FLOOR if A2 net median <= 4",
                "labels": f"POSITIVE: median >= +{E6_MARGIN} and >= {E6_POS}/5 positive; NEGATIVE: median <= -{E6_MARGIN} "
                          f"and >= {E6_POS}/5 negative; NULL: |median| < {E6_MARGIN}; else MIXED",
                "label_semantics_test": "tests/test_fs1_eval.py::test_e6_label_semantics (synthetic ideal data per "
                                        "label, checked before seal — advisor 10-11 template rule)"}},
            "confounds_named": ["homing gain K_HOME not normalized by a (clip binds more often)",
                                "exploiter difficulty at equal 1e7 budget -> exploiter final penetration "
                                "reported as covariate", "ROE A kinetic route -> net metric only"],
        },
        "not_evidence_for": ["world ceiling", "real-net representativeness", "blind prediction (rho* "
                             "registered after the E7-a probe; first registered prediction for the CEILING "
                             "layer)", "positive claims unconditional on the 1e7 exploiter",
                             "pooling with E7-b/b2/c"],
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data != build():
        raise ValueError(f"E1 manifest drift: {MANIFEST}")
    return data


if __name__ == "__main__":
    MANIFEST.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for p in LADDER + PAIR:
        print(p)
    print(MANIFEST, build()["manifest_hash"])
