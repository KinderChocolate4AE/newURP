"""Read-only CLBC1 FIRE-to-capture diagnostic over sealed evaluation JSON.

This script does not run the environment or train a policy.  It checks pairing and
lineage fields, then separates soft-gate FIRE events from robust-ready FIRE events.

    python -m scripts.b0_v3_capturer_clbc1_posthoc
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from statistics import median


ROOT = Path("artifacts/marl/b0_v3_capturer_clbc1")
ARMS = ("replay", "clbc1")


def _median(records: list[dict], key: str) -> float | None:
    values = [float(r["at_fire"][key]) for r in records
              if r.get("at_fire") is not None
              and math.isfinite(float(r["at_fire"][key]))]
    return float(median(values)) if values else None


def summarize(records: list[dict], theta_fire: float = 0.9) -> dict:
    fired = [r for r in records if r.get("fire")]
    input_robust = [r for r in fired if r.get("at_fire") is not None
                    and float(r["at_fire"]["v_shot_worst"]) >= 1.0]
    input_soft_only = [r for r in fired if r.get("at_fire") is not None
                       and float(r["at_fire"]["v_shot_soft"]) >= theta_fire
                       and float(r["at_fire"]["v_shot_worst"]) < 1.0]
    input_other = [r for r in fired
                   if r not in input_robust and r not in input_soft_only]
    captured = [r for r in fired if r["bin"] == "N"]
    spent = [r for r in fired if r["outcome"] == "SPENT_FAIL"]
    return {
        "episodes": len(records),
        "clean_crossing_episodes": sum(r["clean_crossings"] > 0 for r in records),
        "fired": len(fired),
        "captured_N": len(captured),
        "spent_fail": len(spent),
        "policy_input_soft_gate_only": len(input_soft_only),
        "policy_input_robust_ready": len(input_robust),
        "policy_input_other": len(input_other),
        "capture_per_fire": len(captured) / len(fired) if fired else None,
        "policy_input_robust_matches_N": {
            "all": all((r in input_robust) == (r["bin"] == "N") for r in fired),
            "mismatch_scenario_ids": [r["scenario_id"] for r in fired
                                      if ((r in input_robust) != (r["bin"] == "N"))],
        },
        "at_fire_medians": {
            "v_shot_soft": _median(fired, "v_shot_soft"),
            "v_shot_worst": _median(fired, "v_shot_worst"),
            "fire_probability": _median(fired, "fire_prob"),
            "attitude_to_teacher_deg": _median(fired, "ang_att_teacher_deg"),
        },
        "terminal_outcomes": dict(sorted(Counter(r["outcome"] for r in records).items())),
    }


def paired_changes(replay: list[dict], clbc1: list[dict]) -> dict:
    left = {r["scenario_id"]: r for r in replay}
    right = {r["scenario_id"]: r for r in clbc1}
    if left.keys() != right.keys():
        raise ValueError("evaluation arms are not scenario-paired")

    transitions = Counter()
    n_discordance = Counter()
    fire_discordance = Counter()
    for sid in sorted(left):
        a, b = left[sid], right[sid]
        transitions[f"{a['outcome']}->{b['outcome']}"] += 1
        n_discordance[(bool(a["bin"] == "N"), bool(b["bin"] == "N"))] += 1
        fire_discordance[(bool(a["fire"]), bool(b["fire"]))] += 1

    def named(c: Counter) -> dict:
        return {
            "neither": c[(False, False)],
            "replay_only": c[(True, False)],
            "clbc1_only": c[(False, True)],
            "both": c[(True, True)],
        }

    return {
        "terminal_transitions": dict(sorted(transitions.items())),
        "N_discordance": named(n_discordance),
        "FIRE_discordance": named(fire_discordance),
        "clbc1_only_FIRE_outcomes": dict(sorted(Counter(
            right[sid]["outcome"] for sid in left
            if not left[sid]["fire"] and right[sid]["fire"]).items())),
        "replay_only_FIRE_outcomes": dict(sorted(Counter(
            left[sid]["outcome"] for sid in left
            if left[sid]["fire"] and not right[sid]["fire"]).items())),
    }


def analyze(root: Path) -> dict:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    theta = float(manifest["evaluation"].get("theta_fire", 0.9))
    seeds: dict[str, dict] = {}
    lineage = []
    for seed in (0, 1):
        payloads = {}
        for arm in ARMS:
            path = root / f"seed{seed}" / f"evaluation_{arm}.json"
            payloads[arm] = json.loads(path.read_text(encoding="utf-8"))
            p = payloads[arm]
            lineage.append(p["manifest_hash"] == manifest["manifest_hash"]
                           and int(p["actor_seed"]) == seed and p["arm"] == arm)
        seeds[str(seed)] = {
            arm: summarize(payloads[arm]["records"], theta) for arm in ARMS
        }
        seeds[str(seed)]["paired"] = paired_changes(
            payloads["replay"]["records"], payloads["clbc1"]["records"])

    return {
        "schema": "b0-v3-capturer-clbc1-posthoc-v1",
        "source": str(root),
        "manifest_hash": manifest["manifest_hash"],
        "read_only": True,
        "lineage_and_pairing_valid": all(lineage),
        "semantics": {
            "soft_gate": "clean/FIRE gate uses v_shot_soft >= theta_fire",
            "capture": "env freezes pending capture at FIRE from not boxed_in and v_shot_worst >= 1",
            "trace_limit": "at_fire values are the policy-input observation; env.step recomputes the judge with the next step_seed, so they are diagnostic rather than the authoritative FIRE judge",
            "scope": "post-hoc mechanism readout only; no gate or promotion decision",
        },
        "seeds": seeds,
    }


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    result = analyze(args.root)
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
