"""Seal E10 = 발사 게이트 학습 방어 — docs/146. 격자·생산·판정 규칙의 단일 원천.

    python scripts/fs1_e10_manifest.py     # 결과 보기 전 봉인 (artifacts/fs1/e10_manifest.json)

질문: 발사를 포획 술어로 막은 (FS1Spec.fire_gate="robust") 학습 방어의 확보 포획 수는, 그 방어 전용으로
적응한 레드팀 상대로, χ 가 낮아질수록 오르는가.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fs1_e1_manifest import RHO_B, TAU0, _deploy_ticks  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "fs1" / "e10_manifest.json"

TS = [1.0, 0.6666666667, 0.5]                      # τ = 0.30 / 0.20 / 0.15 s — 정확히 6 / 4 / 3 tick (E8 관례, 반올림 없음)
POINTS = [{"name": f"g{i}", "tau_scale": ts, "tau": round(TAU0 * ts, 6), "deploy_ticks": _deploy_ticks(TAU0 * ts),
           "chi": round(ts ** 2 / RHO_B, 4), "theta_scale": 1.0, "aim": "cv", "mu": 0.35, "fire_gate": "robust"}
          for i, ts in enumerate(TS)]
SEEDS = [40, 41, 42, 43, 44]
N = 240
SEED0, STRIDE = 380000, 1000                       # 평가 seed 대역 (E7-b 276000·E8 360000 과 분리)
JSEED = 335000                                     # 레드팀: + idx*100 + seed (E7 277000·E1 30x000·E1b 310000·E8 315000·R1 32x000 과 분리)
BUDGET, SNAPSHOTS = 3e7, (1e7, 2e7)
THR_OPEN, NEED_OPEN = 29, 3                        # 문턱 29/240 = 기존 등록값 승계 (docs/126·129), seed 5 중 3
ORDER_MARGIN = 13                                  # 2·√2·4.56 = 12.9 (R0 반복성: 정합 det 평가 1 회의 이항 SD 4.56/240 @ 23/240)
BUDGET_D, BUDGET_POS = 4, 10                       # R1 (docs/138) 규칙 승계: 중앙값 ≥ 4 ∧ 15 중 ≥ 10 양수


def verdict(net: dict, net_1e7: dict) -> dict:
    """net[point][seed] = 정합 레드팀 3e7 상대 그물 포획 수 /240 (learned_det). net_1e7 = 같은 레드팀의 1e7 스냅샷 상대.
    P-E10a 열림 / P-E10b 순서 / P-E10c 예산. 라벨의 뜻은 docs/146 §4."""
    names = [p["name"] for p in POINTS]                    # χ 내림차순 (g0 = 0.52 … g2 = 0.13)
    med = {n: statistics.median(net[n][s] for s in SEEDS) for n in names}
    low = names[-1]
    n_open = sum(net[low][s] >= THR_OPEN for s in SEEDS)
    p_a = "GATE_OPENS" if n_open >= NEED_OPEN else "GATE_NULL"
    mono = all(med[a] <= med[b] for a, b in zip(names, names[1:]))
    gap = med[low] - med[names[0]]
    p_b = "ORDER_SUPPORTED" if (mono and gap >= ORDER_MARGIN) else "ORDER_NOT_SUPPORTED"
    d = [net_1e7[n][s] - net[n][s] for n in names for s in SEEDS]
    dm, pos = statistics.median(d), sum(x > 0 for x in d)
    p_c = ("BUDGET_UNDERTRAINED" if (dm >= BUDGET_D and pos >= BUDGET_POS) else
           "BUDGET_CONVERGED" if abs(dm) < BUDGET_D else "BUDGET_MIXED")
    return {"median": med, "P-E10a": {"point": low, "n_open": n_open, "verdict": p_a},
            "P-E10b": {"monotone": mono, "end_gap": gap, "verdict": p_b},
            "P-E10c": {"d_median": dm, "n_positive": pos, "n": len(d), "verdict": p_c}}


def build() -> dict:
    body = {
        "schema": "fs1-e10-manifest-v1",
        "status": ("sealed 2026-11-19 BEFORE any E10 implementation in JAX or production (contract docs/146; user "
                   "approval 2026-11-19 'approved, start sealing'). NOT BLIND: before this seal main re-tabulated the "
                   "episode-level records of the E7-b evaluation (ungated learned defense vs matched 1e7 exploiter: "
                   "robust tick present in 28-56% of episodes, net capture 5-11%) and ran a wiring probe of the gate "
                   "against a non-evading straight-in attacker. Changed from the approved draft before seal: middle "
                   "point chi 0.255 -> 0.231 (tau 0.20 s = exact 4 ticks, E8 convention); scripted reference arm "
                   "dropped (existing scripted defenders fix r_fire = 12 m, which under the gate misses most of the "
                   "base-net window at fire distance ~11-14 m; a handicapped reference row would mislead)"),
        "question": ("with firing gated by the capture predicate itself, does the secured net-capture count of the "
                     "learned defense against its own adapted red team rise as chi falls"),
        "world_change": {"flag": "FS1Spec.fire_gate = 'robust' (default 'off' is bit-identical to the current world)",
                         "semantics": ("in LOADED a fire request is honoured only on a tick where the capture predicate "
                                       "(v_shot_worst >= 1 and not boxed_in — the same predicate that freezes capture "
                                       "at the fire event, shepherd/env.py) is true; a blocked request consumes no "
                                       "shot, no waste, no fire cost. Hence fire == capture by construction. Under the gate "
                                       "the FCS ignores the r_fire action and requests fire whenever armed, LOADED and "
                                       "d <= 16 m (the measurement window): a blocked request is free so the fire-distance "
                                       "choice has no trade-off, and the BC teacher value r_fire = 12 m would otherwise "
                                       "handicap the base net (window at fire distance ~11-14 m) in favour of the "
                                       "registered prediction. Learning decides station, acceleration, arm"),
                         "applies_to": "BC data collection, co-training, exploiter training, evaluation — all stages",
                         "canonical_tests": "tests/test_fs1_e10_gate.py", "jax": "port + parity (McNemar) before production"},
        "points": POINTS, "seeds": SEEDS,
        "held_fixed": "mu 0.35, nu 1.0, theta, R_max, V, a_att (20.45), recipe; only tau (deploy ticks 6/4/3) changes",
        "production": {"per slot": ("NEW BC -> E8 recipe (arm C-1 recipe, 1.1e8) -> det exploiter 3e7 with snapshots at "
                                    f"1e7 and 2e7 (jseed {JSEED} + idx*100 + seed); no sto exploiter"),
                       "slots": len(POINTS) * len(SEEDS),
                       "code": "E8 production pin + fire_gate knob — JAX session confirms pin and parity",
                       "smoke": ("per point: env.tau == fsm.tau, realized deploy ticks 6/4/3; gate: no fire event with a "
                                 "false predicate; training throughput with per-tick judge calls measured before launch")},
        "evaluation": {"n": N, "seed0": SEED0, "stride": STRIDE, "env_seed": 0,
                       "defenders": ["learned_det (judgment, vs det exploiter 3e7)", "learned_sto (report)"],
                       "exploiters": "3e7 (judgment) + 1e7, 2e7 snapshots (budget curve)",
                       "cli": ("--tau-scale per point --fire-gate robust --mu 0.35 --nu 1.0 --stack r4p --coop-window "
                               "--env-seed 0"),
                       "preflight": "the same slot evaluated twice must give identical episodes.jsonl (E9 lesson: torch RNG)"},
        "rule": {"metric": "net = NET_CAPTURE + CAPTURE_WITH_CONTACT (learned_det vs its det exploiter at 3e7), slot level",
                 "P-E10a": (f"at chi {POINTS[-1]['chi']}: >= {NEED_OPEN} of {len(SEEDS)} seeds with net >= {THR_OPEN} -> "
                            "GATE_OPENS, else GATE_NULL"),
                 "P-E10b": ("seed-median net non-decreasing as chi falls over the 3 points AND median(lowest chi) - "
                            f"median(base) >= {ORDER_MARGIN} -> ORDER_SUPPORTED, else ORDER_NOT_SUPPORTED"),
                 "P-E10c": (f"d = net(1e7 snapshot) - net(3e7) per slot ({len(POINTS) * len(SEEDS)} slots): median >= "
                            f"{BUDGET_D} and >= {BUDGET_POS} positive -> BUDGET_UNDERTRAINED; |median| < {BUDGET_D} -> "
                            "BUDGET_CONVERGED (meaning: budget effect < 4/240, not a convergence proof); else BUDGET_MIXED"),
                 "prediction": ("GATE_OPENS and ORDER_SUPPORTED. Basis: head-on window (R/V)(1 - chi/chi*) = 2.5 / 5.1 / "
                                "6.0 ticks at chi 0.52 / 0.231 / 0.13 (E4 N formula); the gate fires on a 1-tick window. "
                                "Base net is predicted LOWEST, not zero. Not blind"),
                 "report": ["share of episodes with a robust tick", "defended (all outcomes)", "penetration",
                            "budget curve 1e7/2e7/3e7", "learned_sto", "arm and station statistics of the defense"]},
        "consequence": {
            "GATE_OPENS + ORDER_SUPPORTED": ("two-sided validation figure: where the analysis says infeasible it stays "
                                             "closed, where it says feasible the analytic gate opens it; win-rate table "
                                             "chi x defense with budget labels"),
            "GATE_NULL": ("the adapted attacker routes around the guaranteed set — the bottleneck is forcing, not window "
                          "existence; next question = path limiters in the regime where a window exists"),
            "BUDGET_UNDERTRAINED": "every number is written as an upper estimate ('<='); opening claims are budget-conditional"},
        "invalid_if": ["any fire event with rob_fire false (gate violation)", "fired but capture unresolved (except "
                       "episode end / finisher loss)", "budget / completion / paired / manifest / variant-flag mismatch",
                       "evaluation preflight not reproducible"],
        "power_memo": ("E7-b seed scatter of the ungated ceiling is large (e.g. 41 / 7 / 19); median of 5 seeds; single "
                       "matched evaluation binomial SD 3.4-4.6/240 (R0). The order margin 13 = 2*sqrt(2)*4.56"),
        "limits": ["the gate is an oracle-type judge (true state, known attacker max acceleration); the deployable "
                   "version narrows the fire condition by the conservative fold chi_eff (E9) — outside this contract",
                   "zero reaction margin (same-tick fire)", "point-mass 3DOF", "red-team budget conditional",
                   "three chi points (no transition-location resolution)", "defense acceleration ratio fixed at 0.35"],
        "pre_seal_checks": ["label semantics unit tests tests/test_fs1_e10_gate.py::test_e10_label_semantics*",
                            "gate semantics tests (default bit-identical, blocked request consumes nothing, fire only "
                            "on predicate, r_fire action ignored under the gate)", "deploy ticks exact (assert)", "measurement window: episode outcomes only"],
        "not_evidence_for": ["pooling with E7-b / R1 / E8 (ungated numbers appear only as 'separate contract' reference)",
                             "deployable fire control", "world ceiling", "blind prediction"],
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data != build():
        raise ValueError(f"E10 manifest drift: {MANIFEST}")
    return data


if __name__ == "__main__":
    for p in POINTS:
        assert abs(p["tau"] / 0.05 - round(p["tau"] / 0.05)) < 1e-6 and p["deploy_ticks"] == round(p["tau"] / 0.05), p
        print(p)
    MANIFEST.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(MANIFEST, build()["manifest_hash"])
