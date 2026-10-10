"""Seal E2 = AMI (attacker mechanism intervention) — docs/132.

    python scripts/fs1_ami_manifest.py      # 결과 보기 전 봉인 (artifacts/fs1/ami_manifest.json)
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fs1_e7_manifest import B_SEED0, B_SEEDS, B_STRIDE, B_VARIANTS  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "fs1" / "ami_manifest.json"

ARMS = ["base", "out0", "in0", "zfix", "lat0", "shuf_out", "shuf_in", "in_half"]
LINES = {"det": {"defender": "learned_det", "exploiter": "judge_exploiter", "role": "judgment"},
         "sto": {"defender": "learned_sto", "exploiter": "judge_exploiter_sto", "role": "replication"}}
N, ENV_SEED = 240, 0
LIFT_MED, LIFT_POS = 8, 10            # Δ_net 중앙값 ≥ +8/240 그리고 15 slot 중 ≥ 10 개 양수
ADAPT_FRAC = 0.5                      # shuffle 이 효과의 절반 미만만 재현 → 적응
REPRO_TOL = 6                         # base 중앙값 vs E7-b/b′ net 중앙값 허용 차


def build() -> dict:
    body = {
        "schema": "fs1-ami-manifest-v1",
        "status": ("sealed 2026-10-11 BEFORE any AMI production result (contract: docs/132; user "
                   "approval 2026-10-10 'A', scope amendments by advisor 2026-10-11: shuffle control "
                   "+ alpha 0.5 dose + E6 trigger). Only a 6-episode smoke on the local smoke ckpt "
                   "(wiring) was run"),
        "lineage": {"contract": "docs/132", "e7b": "543cd9e4b3582687", "e7b2": "d25bf6e6dedf31ea",
                    "gap": "docs/131 G1 (plateau cause), hypothesis D3 (window-denial approach geometry)"},
        "question": ("why does the matched-audit net ceiling stay ~8-9% for rho 3.9-11.8: which part of "
                     "the dedicated exploiter's learned residual carries it, and is it state-contingent "
                     "(adaptive) or just maneuver energy"),
        "slots": {"variants": B_VARIANTS, "seeds": B_SEEDS,
                  "checkpoints": "E7-b frozen defense + its dedicated exploiters (no new training)"},
        "lines": LINES,
        "arms": {
            "base": "no intervention (+ records residuals per segment = shuffle donor)",
            "out0": "learned residual = 0 while |p_att - p_fin| > 16 m (pure homing approach)",
            "in0": "learned residual = 0 while |p_att - p_fin| <= 16 m (16 m = existing window def.)",
            "zfix": "skill z frozen at its episode-start draw (rng consumption unchanged)",
            "lat0": "residual projected on the attacker->asset axis (lateral component removed)",
            "shuf_out": "out-segment residual replaced by the base-arm residual sequence of another "
                        "episode (donor = next seed in the slot, cyclic; k-th step uses donor[k mod len])",
            "shuf_in": "same, in-segment",
            "in_half": "in-segment residual x 0.5 (dose)",
        },
        "evaluation": {"n": N, "seed0": B_SEED0, "variant_seed_stride": B_STRIDE,
                       "paired": "same 240 seeds in every arm (= E7-b seeds)",
                       "env_seed": (f"{ENV_SEED} for every worker (--env-seed). FINDING 2026-10-11: the "
                                    "default worker env is built with seed=os.getpid(), which leaks "
                                    "into the m4-stack RNG (v_fire-level differences, same labels in "
                                    "the smoke) -> prior canonical evals are distribution-equivalent "
                                    "but not bit-reproducible; AMI fixes it for cross-arm pairing"),
                       "cli": "E7-b flags (--stack r4p --mu 0.35 --nu 1.0 + variant flags "
                              "--coop-window --groups none) + --att-iv ARM [--att-donor] --env-seed 0"},
        "metric": {"primary": "net = NET_CAPTURE + CAPTURE_WITH_CONTACT of the line defender vs its "
                              "exploiter (ROE A: weaker attackers are also easier kinetic targets -> "
                              "defended total is reported, never judged)",
                   "delta": "Δ_X(slot) = net_X - net_base (paired)",
                   "report": ["defended, K_FIRST, fallback, penetrated", "occupancy: episodes with "
                              ">= 1 robust window tick, total robust ticks (coop-window n_rob)",
                              "fires, net per fire"]},
        "gates": {
            "repro_check": (f"base median net over 15 slots within ±{REPRO_TOL} of the E7-b net_det "
                            "median (det line) / E7-b2 net_sto median (sto line); else INVALID_REPRO "
                            "(pipeline fault, stop)"),
            "LIFT(X)": (f"median_15 Δ_X >= +{LIFT_MED} AND Δ_X > 0 in >= {LIFT_POS} of 15 slots "
                        "(X in out0, in0, zfix, lat0)"),
            "ADAPTIVE_S / ENERGY_S": (f"for S in (out, in) with LIFT(S0): ADAPTIVE_S if median_15(Δ_S0 "
                                      f"- Δ_shufS) >= {ADAPT_FRAC} x median_15 Δ_S0 (shuffled residual "
                                      "of equal energy recovers less than half of the lift), else ENERGY_S"),
            "branch (det line = judgment)": {
                "AMI_ADAPTIVE": "any ADAPTIVE_S -> plateau carried by state-contingent residual in S",
                "AMI_ATTACKER_NONADAPTIVE": "some LIFT but no ADAPTIVE_S",
                "AMI_NOT_ATTACKER": "no LIFT in (out0, in0, zfix, lat0) -> plateau not removable by "
                                    "these attacker-side ablations (defense-side candidate)",
            },
            "sto line": "same rules, replication only; disagreement -> report both as line-dependent",
            "dose": "in_half: Δ reported with its position relative to Δ_in0 (report only)",
        },
        "e6_trigger (pre-registered both ways)": (
            "AMI_ADAPTIVE or AMI_ATTACKER_NONADAPTIVE -> E6 (world a-change point at rho 3.92, a ~ 10.0, "
            "a_def fixed by mu' ~ 0.72, Lambda = V^2/(a R_max) named) becomes a conditional arm of the "
            "E1 contract; AMI_NOT_ATTACKER -> E6 deferred to the journal version. E6 hypotheses and "
            "gates are sealed in that contract before any E6 run; E6 results reported regardless"),
        "not_evidence_for": ["world ceiling", "attacker optimality (1e7 exploiter conditional)",
                             "real-threat behavior", "pooling with E7-b/b2 verdicts (paired re-eval only)",
                             "cooperation vocabulary"],
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data != build():
        raise ValueError(f"AMI manifest drift: {MANIFEST}")
    return data


if __name__ == "__main__":
    MANIFEST.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(MANIFEST, build()["manifest_hash"])
