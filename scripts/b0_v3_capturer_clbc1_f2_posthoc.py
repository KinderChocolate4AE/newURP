"""Read-only paired and authoritative-FIRE analysis for harvested CLBC1-F2."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
from statistics import median


ROOT = Path("artifacts/marl/b0_v3_capturer_clbc1_f2")
ARMS = ("control", "f2_low_std")
CONTROL, F2 = ARMS


def _median(events: list[dict], key: str) -> float | None:
    values = [float(e[key]) for e in events if math.isfinite(float(e[key]))]
    return float(median(values)) if values else None


def fire_groups(records: list[dict]) -> dict:
    fired = [r for r in records if r.get("accepted_fire_judge") is not None]
    groups = {
        "N": [r for r in fired if r["bin"] == "N"],
        "SPENT_FAIL": [r for r in fired if r["outcome"] == "SPENT_FAIL"],
    }
    out = {}
    for name, rows in groups.items():
        events = [r["accepted_fire_judge"] for r in rows]
        out[name] = {
            "n": len(rows),
            "robust_ready": sum(bool(e["robust_ready"]) for e in events),
            "v_shot_soft_p50": _median(events, "v_shot_soft"),
            "attitude_to_teacher_deg_p50": _median(events, "ang_att_teacher_deg"),
            "command_to_teacher_deg_p50": _median(events, "ang_cmd_teacher_deg"),
            "fire_step_p50": _median(events, "t"),
            "boxed_in": sum(bool(e["boxed_in"]) for e in events),
        }
    robust = [r for r in fired if r["accepted_fire_judge"]["robust_ready"]]
    mismatches = [r["scenario_id"] for r in fired
                  if (r in robust) != (r["bin"] == "N")]
    obs_actual = Counter()
    soft_diffs = []
    input_by_terminal = Counter()
    for row in fired:
        observed = row.get("policy_input_at_fire") or {}
        input_robust = float(observed.get("v_shot_worst", 0.0)) >= 1.0
        actual_robust = bool(row["accepted_fire_judge"]["robust_ready"])
        obs_actual[(input_robust, actual_robust)] += 1
        input_by_terminal[(row["outcome"], input_robust)] += 1
        if "v_shot_soft" in observed:
            soft_diffs.append(abs(float(observed["v_shot_soft"])
                                  - float(row["accepted_fire_judge"]["v_shot_soft"])))
    return {
        "accepted_FIRE": len(fired),
        "capture_per_FIRE": len(groups["N"]) / len(fired) if fired else None,
        "robust_ready_matches_N": not mismatches,
        "mismatch_scenario_ids": mismatches,
        "policy_input_vs_authoritative_robust": {
            "neither": obs_actual[(False, False)],
            "input_only": obs_actual[(True, False)],
            "authoritative_only": obs_actual[(False, True)],
            "both": obs_actual[(True, True)],
            "policy_input_robust_in_N": input_by_terminal[("CAPTURED", True)],
            "policy_input_robust_in_SPENT_FAIL": input_by_terminal[("SPENT_FAIL", True)],
            "v_shot_soft_abs_diff_p50": float(median(soft_diffs)) if soft_diffs else None,
        },
        "by_terminal": out,
    }


def paired(control: list[dict], f2: list[dict]) -> dict:
    c = {r["scenario_id"]: r for r in control}
    f = {r["scenario_id"]: r for r in f2}
    if c.keys() != f.keys():
        raise ValueError("arms are not paired")

    def discordance(predicate) -> dict:
        counts = Counter((predicate(c[sid]), predicate(f[sid])) for sid in c)
        return {"neither": counts[(False, False)],
                "control_only": counts[(True, False)],
                "f2_only": counts[(False, True)], "both": counts[(True, True)]}

    transitions = Counter(f"{c[sid]['outcome']}->{f[sid]['outcome']}" for sid in c)
    f2_only_fire = [f[sid] for sid in c if not c[sid]["fire"] and f[sid]["fire"]]
    return {
        "N_discordance": discordance(lambda r: r["bin"] == "N"),
        "FIRE_discordance": discordance(lambda r: bool(r["fire"])),
        "crossing_discordance": discordance(lambda r: r["clean_crossings"] > 0),
        "terminal_transitions": dict(sorted(transitions.items())),
        "f2_only_FIRE_outcomes": dict(sorted(Counter(
            r["outcome"] for r in f2_only_fire).items())),
    }


def analyze(root: Path = ROOT) -> dict:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    readout = json.loads((root / "readout.json").read_text(encoding="utf-8"))
    seeds = {}
    valid = readout["manifest_hash"] == manifest["manifest_hash"]
    for seed in (0, 1):
        payloads = {arm: json.loads(
            (root / f"seed{seed}" / f"evaluation_{arm}.json").read_text(encoding="utf-8"))
                    for arm in ARMS}
        valid &= all(p["manifest_hash"] == manifest["manifest_hash"]
                     and p["code_commit"] == "549a4fa"
                     and p["actor_seed"] == seed and p["arm"] == arm
                     for arm, p in payloads.items())
        records = {arm: payloads[arm]["records"] for arm in ARMS}
        seeds[str(seed)] = {
            "fire_judge": {arm: fire_groups(records[arm]) for arm in ARMS},
            "paired": paired(records[CONTROL], records[F2]),
        }
    return {
        "schema": "b0-v3-capturer-clbc1-f2-posthoc-v1",
        "manifest_hash": manifest["manifest_hash"],
        "sealed_decision": readout["decision"],
        "read_only": True,
        "lineage_and_pairing_valid": bool(valid),
        "scope": "mechanism readout only; sealed gate and decisions unchanged",
        "seeds": seeds,
    }


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    text = json.dumps(analyze(args.root), indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
