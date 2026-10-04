"""Seal P1d: 전진 교전 limiter 의 활주로 probe (docs/122 — P1c 설계 결함 보완)."""
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "p1d_runway" / "manifest.json"
SCALES = [1, 2, 4]
ATTACKERS = [
    {"label": "a_r05", "overrides": {"route_gain": 0.5, "sense_range": "inf"}},
    {"label": "a_r08", "overrides": {"route_gain": 0.8, "sense_range": "inf"}},
]
ARMS = ("hold", "c5", "fwd")
RHO = 0.5
EXCURSION_MIN_M = 18.0      # = 2·r_d (c5 호 반경 9 m 의 두 배)


def build() -> dict:
    body = {
        "schema": "p1d-runway-manifest-v1",
        "status": "sealed pre-run; scripted forward-engaging limiter runway probe",
        "design_doc": "docs/122_p1d_forward_limiter_runway_probe.md",
        "scope": {
            "question": ("does a limiter rule that CAN use the added approach "
                         "distance gain over c5 as the attacker start distance "
                         "scales x1 -> x2 -> x4 (defense layout fixed)"),
            "motivation": ("P1c STANDOFF_DOES_NOT_OPEN was structurally foregone: "
                           "c5 is a bearing-only fixed 9 m arc and cannot use "
                           "added distance (P1c note fdffae7). The short-runway "
                           "explanation for P2_NULL remains untested."),
            "not_evidence_for": ["learned anything", "B0 v3 claims at k > 1",
                                 "optimality of the fwd rule or of rho",
                                 "entry-gate distribution design"],
        },
        "world_variants": {
            "rule": ("identical to P1c (manifest 6fc93fde71b38a30): k = 1 is the "
                     "sealed suite world; k > 1 scales only adversary_start_x and "
                     "episode_len by k (episode_len base read from the k = 1 build). "
                     "Never pooled with B0 v3 or P1c results."),
            "scales": SCALES,
        },
        "attackers": ATTACKERS,
        "arms": {
            "hold": "scripted hold limiter",
            "c5": "arc c5 (B2 RULE_COOP kw: r_d 9, dphi 30 deg)",
            "fwd": (f"arc c5 kw + rho {RHO}: slot radius r = max(r_d, rho * R_h), "
                    "R_h = attacker-asset horizontal distance (midpoint screen); "
                    "slot angular spacing dphi * r_d / r keeps the c5 arc-length "
                    "spacing (the c5 formation translated forward); identical to "
                    "c5 once R_h <= r_d / rho = 18 m (shepherd.agents.baselines."
                    "arc_geometry)"),
            "capturer": "scripted launcher (all arms)",
        },
        "evaluation": {
            "namespace": "p1d_runway_v1",
            "seed0": 251000,
            "cells": "28 boundary cells (B2 manifest order)",
            "episodes_per_cell": 10,
            "episodes_per_arm_per_scale_per_attacker": 280,
            "episodes_total": 280 * len(SCALES) * len(ATTACKERS) * len(ARMS),
            "paired": ("within (scale, attacker), all arms share identical draws; "
                       "the same draw stream is reused across scales"),
            "excursion": ("per episode: max over steps of the mean horizontal "
                          "limiter distance from the asset (pre-move state, "
                          "run_episode telemetry)"),
        },
        "gate": {
            "invalid": ["lineage", "completion", "budget", "paired draws",
                        "power: mean steps of the hold arm strictly increase k=1 -> 4",
                        f"mechanism: mean excursion of fwd at k=4 >= {EXCURSION_MIN_M} m "
                        "(the intervention arm must actually use the runway — "
                        "P1b/P1c lesson)"],
            "complete": "COMPLETE_P1D",
            "invalid_decision": "INVALID_P1D",
            "classification": (
                "pre-registered, pooled over both attackers (560 ep per arm per "
                "scale): D(k) = N_fwd - N_c5. If D(4) - D(1) >= +28 (+5%p): "
                "RUNWAY_OPENS_SHAPING, unless H_illegal(fwd, k=4) - "
                "H_illegal(c5, k=4) >= +28, then RUNWAY_GAIN_UNSAFE. Else "
                "RUNWAY_DOES_NOT_OPEN (tested rule, rho, range and scaling model "
                "only). fwd - hold, per-attacker breakdown, D(2), excursion and "
                "step statistics are reported, not gated."),
        },
        "promotion": ("RUNWAY_OPENS_SHAPING reopens the B0 v4 (entry-gate world) "
                      "결재 and the limiter-learning question on a new contract; "
                      "it does not reopen learning by itself. DOES_NOT_OPEN "
                      "rejects the short-runway explanation for this rule family "
                      "and moves limiter questions into the docs/104 section-3 G0 card."),
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data != build():
        raise ValueError(f"P1d manifest drift: {MANIFEST}")
    return data


def main() -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(f"{MANIFEST} {build()['manifest_hash']}")


if __name__ == "__main__":
    main()
