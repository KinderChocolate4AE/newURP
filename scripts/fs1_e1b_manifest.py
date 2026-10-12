"""Seal E1b = 전이 구간 조밀화 (ρ 1.92–2.30, 전 구간 6 tick) — docs/137.

    python scripts/fs1_e1b_manifest.py      # 결과 보기 전 봉인 (artifacts/fs1/e1b_manifest.json)
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fs1_e1_manifest import _pt  # noqa: E402  (같은 점 정의: ρ = ρ_B / ts², deploy_ticks = FSM 감산)

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "fs1" / "e1b_manifest.json"

POINTS = [_pt(f"d{i}", round(0.915 ** (i / 4), 5), "densify") for i in range(5)]   # log 4등분, 양 끝 = E1 의 1.92 / 2.30
SEEDS = list(range(10, 18))                     # 8 seed, E1 (0–4) 와 겹치지 않음 → 같은 slot 재현 아님 (pooling 금지)
N = 240
SEED0, STRIDE = 350000, 1000                    # 평가 seed 대역 (E1 = 330000 대역과 분리)
JSEED_DET = 310000                              # det 착취자 jseed = 대역 + idx*100 + seed (E1 300000/305000 과 분리)
JUDGMENT = {"defender": "learned_det", "group": "ex_judge"}
MIN_STEP = 4                                    # 끝점 중앙값 차 (판 수) — 이보다 작으면 NO_STEP
SHARE = 0.90                                    # bootstrap 에서 점추정 라벨이 차지해야 하는 몫
N_BOOT = 2000
ONSET_LABELS = ("ONSET_LOW", "ONSET_MID", "ONSET_HIGH")   # 첫 내부점 d1 / d2 / d3 이상 (d3 못 넘으면 HIGH)


def onset_label(meds) -> str:
    """meds = 5 점의 seed 중앙값 net (ρ 오름차순). 끝점 = 이 계약 안의 바닥 F (d0) · 위 P (d4).
    M = (F + P)/2 를 처음으로 넘는 (≥) 내부점의 위치가 시작점. 의미 테스트: tests/test_fs1_eval.py."""
    f, p = meds[0], meds[-1]
    if p - f < MIN_STEP:
        return "NO_STEP"
    m = (f + p) / 2
    for lab, v in zip(ONSET_LABELS, meds[1:4]):
        if v >= m:
            return lab
    return "ONSET_HIGH"


def build() -> dict:
    body = {
        "schema": "fs1-e1b-manifest-v1",
        "status": ("sealed 2026-10-12 BEFORE any E1b production (contract docs/137). User approval 2026-10-12 "
                   "'run now while the server is idle' — overrides the advisor's 'after 10/27' timing (advisor "
                   "rule: before 10/26 only R0; user decision). Design = advisor 10-12 sketch with two power-driven "
                   "changes (see 'deviations'). E1 data (docs/134 §8) seen before this design — disclosed"),
        "lineage": {"contract": "docs/137", "parent": "E1 docs/134 (manifest 4215cdb837a0307b)",
                    "recipe": "identical to E1 ladder (arm C-1 distilled fire head, ROE A, m0.35_n1, NEW BC -> 1.1e8 "
                              "-> det exploiter 1e7), production code pin = E1 ladder pin 80afb2a"},
        "question": "where (and whether) the learned net-capture ceiling turns on inside rho 1.92-2.30 (E1's one-step rise)",
        "why_this_interval": ("all five points realize 6 deploy ticks (tau 0.300 -> 0.2745 s), so a split between "
                              "metrics cannot come from the tick step (E1's step is at rho 2.769, outside)"),
        "points": POINTS, "seeds": SEEDS,
        "no_pooling": ("endpoints d0 (rho 1.92) and d4 (rho 2.30) are NEW training with seeds 10-17; E1 slots "
                       "(seeds 0-4) are never combined with E1b"),
        "production": {"per slot": f"NEW BC -> 1.1e8 -> det exploiter 1e7 (jseed {JSEED_DET} + idx*100 + seed); "
                                   "no sto exploiter", "slots": len(POINTS) * len(SEEDS),
                       "hardware": "server4 single GPU, JAX learner (E1 regime)"},
        "evaluation": {"n": N, "seed0": SEED0, "stride": STRIDE, "env_seed": 0,
                       "defenders": ["learned_det (judgment, vs ex_judge)", "learned_sto (report, vs ex_judge)"],
                       "cli": "same as E1 (--tau-scale per point, --stack r4p --mu 0.35 --nu 1.0 --coop-window "
                              "--env-seed 0 --groups none); records rob_fire"},
        "metric": {"primary (judgment)": "net = NET_CAPTURE + CAPTURE_WITH_CONTACT, learned_det vs det exploiter",
                   "diagnostic only": ("rob_fire and conversion = net / rob_fire (E1 A2 count: rob_fire = net + "
                                       "robust-fire-then-penetrated exactly; conversion 0.80 at 1.92, 0.83 at 2.30)"),
                   "report": ["seed-median net per point normalized (net - F)/(P - F) = shape (descriptive, no label)",
                              "defended total", "learned_sto line"]},
        "rule": {
            "endpoints": "F = seed-median net at d0, P = seed-median net at d4 (both inside this contract)",
            "no_step": f"P - F < {MIN_STEP}/240 -> NO_STEP (point estimate, no bootstrap): E1's rise did not reproduce",
            "onset": "first interior point (d1, d2, d3) whose seed-median net >= M = (F + P)/2",
            "labels": {"ONSET_LOW": "onset at d1 (rho 2.01)", "ONSET_MID": "onset at d2 (rho 2.10)",
                       "ONSET_HIGH": "onset at d3 (rho 2.20) or no interior point reaches M"},
            "uncertainty": (f"stratified bootstrap (resample seeds within each point incl. endpoints, recompute F, P, "
                            f"M), {N_BOOT} reps, rng seed 0; final = point label if its bootstrap share >= {SHARE}, "
                            "else UNRESOLVED"),
            "diagnostic_flag": ("if the same rule on rob_fire gives a different final label -> CONVERSION_SENSITIVE "
                                "flag with the conversion table attached; the judgment stays the primary label "
                                "(E1's 'no branch claim on disagreement' rule is NOT reused — advisor 10-12)"),
        },
        "prediction (registered, hypothesis formed after seeing E1)": (
            "head-on window N = 3 steps at rho ~ 2.17 -> ONSET_HIGH or ONSET_MID boundary; registered as: onset "
            "label in {ONSET_MID, ONSET_HIGH}. Not blind: E1 data motivated it"),
        "deviations_from_advisor_sketch": [
            "seeds 5 -> 8 (power memo: 5 seeds gave 46-91% correct under seed SD 4-7, 8 seeds 80-100%)",
            "ONSET_GRADUAL label dropped: synthetic power 0-10% (true gradual values sit on the 25%/75% band "
            "edges); a gradual truth yields UNRESOLVED in 86-97% of synthetic runs, which is the honest outcome. "
            "Shape is reported descriptively",
            "bootstrap rule = point-label share >= 0.90 (95% gave 22-62% power at 5 seeds)"],
        "power_memo": ("synthetic (F 3, P 18, endpoint SD 4, plateau SD 4/7, 80 reps): 8 seeds -> step at d1/d2/d3 "
                       "correct 0.80-1.00, wrong label <= 0.02; script = scratch e1b_power2.py (logic copied into "
                       "tests/test_fs1_eval.py semantics test)"),
        "pre_seal_checks": ["label semantics unit test (ideal synthetic data per label -> that label)",
                            "deploy ticks = 6 at all five points (manifest assert)",
                            "measurement window: net/rob_fire are episode outcomes, no 16 m window involved"],
        "not_evidence_for": ["world ceiling", "real-net representativeness", "blind prediction",
                             "pooling with E1 or E7-b", "claims unconditional on the 1e7 exploiter"],
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data != build():
        raise ValueError(f"E1b manifest drift: {MANIFEST}")
    return data


assert all(p["deploy_ticks"] == 6 for p in POINTS), "E1b interval must be single-tick (6)"

if __name__ == "__main__":
    MANIFEST.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for p in POINTS:
        print(p)
    print(MANIFEST, build()["manifest_hash"])
