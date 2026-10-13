"""Seal E8 = 고정 χ 에서 공격자 가속 스윕 (증거 1-5) — docs/139.

    python scripts/fs1_e8_manifest.py      # 결과 보기 전 봉인 (artifacts/fs1/e8_manifest.json)
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fs1_e1_manifest import RHO_B, TAU0, _deploy_ticks  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "fs1" / "e8_manifest.json"

RHO_T = 3.925                                       # E7-b t0.7 점과 같은 ρ (χ 0.2548)
TS = [1.0, 0.8333333333, 0.6666666667, 0.5]         # τ = 0.30 / 0.25 / 0.20 / 0.15 s — 정확히 6 / 5 / 4 / 3 tick (반올림 없음)
POINTS = [{"name": f"a{i}", "tau_scale": ts, "a_scale": round(RHO_B / (RHO_T * ts ** 2), 6), "mu": 0.35,
           "theta_scale": 1.0, "aim": "cv", "tau": round(TAU0 * ts, 6), "deploy_ticks": _deploy_ticks(TAU0 * ts)}
          for i, ts in enumerate(TS)]
for p in POINTS:
    p["a_att"] = round(20.453333333333333 * p["a_scale"], 3)
    p["rho"] = round(RHO_B / (p["a_scale"] * p["tau_scale"] ** 2), 4)
SEEDS = [20, 21, 22, 23, 24]                         # 1단계
SEEDS_STAGE2 = [25, 26, 27]                          # v1.1: 2단계 (조건부) — 전체 8 seed
CI_Q = (1.25, 98.75)                                 # v1.1: 두 번 보므로 단계마다 97.5% CI
N = 240
SEED0, STRIDE = 360000, 1000
JSEED_DET = 315000                                  # + idx*100 + seed
EQUIV = 8.0 / 1.386294361                           # |β| < 8/240 의 변화 / ln 4 (a 범위 4 배) → 판 수 / ln a
N_BOOT = 2000


def stage2_needed(label, beta) -> bool:
    """v1.1 순차 규칙: 1단계 UNRESOLVED 이고 점추정 |β| < EQUIV 이면 seed 25–27 을 추가해 같은 규칙 (97.5% CI) 을 8 seed 로 다시 적용."""
    return label == "UNRESOLVED" and abs(beta) < EQUIV


def exploiter_budget(r1_label) -> float:
    """v1.1 조건부 예산: R1 (docs/138) = BUDGET_UNDERTRAINED 이면 3e7, 그 밖 1e7. R1 판독 후 착취자 단계에서 적용."""
    return 3e7 if r1_label == "BUDGET_UNDERTRAINED" else 1e7


def slope_label(lo, hi) -> str:
    """β = slot 별 net 을 ln(a_scale) 에 회귀한 기울기의 bootstrap 95% CI. 의미 테스트: tests/test_fs1_eval.py."""
    if lo > 0:
        return "CEILING_RISES_WITH_a"
    if hi < 0:
        return "CEILING_FALLS_WITH_a"
    if -EQUIV < lo and hi < EQUIV:
        return "COLLAPSES_IN_CHI"
    return "UNRESOLVED"


assert [p["deploy_ticks"] for p in POINTS] == [6, 5, 4, 3]
assert all(abs(p["rho"] - RHO_T) < 1e-3 for p in POINTS)


def build() -> dict:
    body = {
        "schema": "fs1-e8-manifest-v1.1",
        "amendment_v1_1": ("2026-10-13, advisor review, BEFORE any E8 production: (1) run order R1 -> E8 and the E8 exploiter "
                           "budget is conditional on the R1 label (3e7 if BUDGET_UNDERTRAINED else 1e7), registered before "
                           "any result; defense training may start before R1 ends, only the exploiter stage waits; (2) the "
                           "label names an AGILITY BUNDLE, not pure Lambda: along iso-chi, Lambda = V^2/(aR), q_dec = dt/tau "
                           "(1/6 -> 1/3) and dt*a/V all change together; (3) strength: w = a tau^2/2 = 0.45 m is constant, so "
                           "kappa = kill radius / w is fixed (limiter geometry held); (4) two-stage sequential design: stage 1 "
                           "seeds 20-24; if UNRESOLVED and |beta_hat| < 5.77, add seeds 25-27 and re-apply to 8 seeds; both "
                           "looks use 97.5% CIs; (5) stage 1 detects >= 12/240 trends over the x4 range but cannot prove "
                           "collapse — UNRESOLVED must not be read as collapse"),
        "status": ("sealed 2026-10-13 BEFORE any E8 production (contract docs/139; user 2026-10-13 'evidence "
                   "collection tonight'). Extends E6 (docs/134 §8: a x 0.49 with ratio fixed raised the ceiling, "
                   "borderline POSITIVE) — E6 data seen before this design"),
        "question": ("at a fixed chi (0.255, plateau), does the learned matched-audit ceiling depend on the attacker "
                     "acceleration itself (with tau adjusted to keep chi), i.e. does the ceiling layer collapse in chi"),
        "points": POINTS, "seeds": SEEDS,
        "held_fixed": ("chi (rho 3.925), mu 0.35 (a_def = 0.35 a_att scales with a), V, theta, R_max, recipe; w = 0.45 m "
                       "constant so kappa = kill radius / w is fixed"),
        "what_changes": ("a_att x4 range (10.0 -> 40.1 m/s^2) with tau 0.30 -> 0.15 s exact tick multiples; head-on "
                         "window in seconds is the same at all points (chi fixed); Lambda = V^2/(a R) changes x4"),
        "production": {"per slot": f"NEW BC -> arm C-1 recipe 1.1e8 -> det exploiter 1e7 (jseed {JSEED_DET} + idx*100 + "
                                   "seed); no sto exploiter", "slots": len(POINTS) * len(SEEDS),
                       "code": "E1 ladder pin 80afb2a + a_scale knob as in E6 (0d36d2b lineage) — JAX session confirms pin",
                       "smoke": "per point: env.tau == fsm.tau, realized deploy ticks 6/5/4/3, a_att as listed"},
        "evaluation": {"n": N, "seed0": SEED0, "stride": STRIDE, "env_seed": 0,
                       "defenders": ["learned_det (judgment, vs det exploiter)", "learned_sto (report)"],
                       "cli": "--tau-scale --a-scale per point, --mu 0.35 --nu 1.0 --stack r4p --coop-window --env-seed 0"},
        "rule": {"metric": "net = NET_CAPTURE + CAPTURE_WITH_CONTACT (learned_det vs det exploiter), slot level",
                 "fit": "OLS slope beta of net on ln(a_scale) over the stage's slots; stratified bootstrap (seeds within "
                        f"point) {N_BOOT}, rng 0, percentile CI at {CI_Q} (97.5%, two looks)",
                 "stage2": f"if stage-1 label is UNRESOLVED and |beta_hat| < {EQUIV:.2f}: add seeds {SEEDS_STAGE2}, same rule on 8 seeds",
                 "exploiter_budget": "3e7 if R1 label == BUDGET_UNDERTRAINED else 1e7 (fs1_e8_manifest.exploiter_budget)",
                 "reading": ("FALLS/RISES = the ceiling at fixed chi depends on the agility bundle (Lambda, q_dec, dt*a/V); "
                             "do not attribute to Lambda alone"),
                 "labels": f"CI > 0 -> CEILING_RISES_WITH_a; CI < 0 -> CEILING_FALLS_WITH_a; CI inside (-{EQUIV:.2f}, "
                           f"{EQUIV:.2f}) (= less than 8/240 change over the x4 range) -> COLLAPSES_IN_CHI; else UNRESOLVED",
                 "prediction": "CEILING_FALLS_WITH_a (from E6: halving a raised the ceiling); not blind",
                 "report": ["seed-median net per point", "rob_fire", "defended", "exploiter final penetration"]},
        "power_memo": ("seed SD 6-9/240 -> slope SE ~ 7/(0.52*sqrt(20)) ~ 3 per ln-unit; a trend of >= ~12/240 over "
                       "the x4 range is detectable, but COLLAPSES_IN_CHI (CI within +-5.8) is rarely reachable with "
                       "5 seeds -> asymmetric test: it can show dependence, it can hardly prove collapse"),
        "confounds_named": ["homing gain K_HOME not normalized by a (E6)", "deploy ticks 6/5/4/3 differ (exact, no "
                            "rounding)", "exploiter difficulty at equal 1e7 budget (R1 tests budget separately)"],
        "pre_seal_checks": ["label semantics unit test tests/test_fs1_eval.py::test_e8_label_semantics",
                            "deploy ticks exact (assert)", "measurement window: episode outcomes only"],
        "not_evidence_for": ["pooling with E6/E7-b/E1", "world ceiling", "blind prediction"],
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data != build():
        raise ValueError(f"E8 manifest drift: {MANIFEST}")
    return data


if __name__ == "__main__":
    MANIFEST.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for p in POINTS:
        print(p)
    print(MANIFEST, build()["manifest_hash"])
