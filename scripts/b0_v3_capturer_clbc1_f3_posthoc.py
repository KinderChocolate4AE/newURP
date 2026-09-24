"""Read-only paired and observation/judge analysis for harvested CLBC1-F3."""
from __future__ import annotations

from collections import Counter
import argparse
import json
from pathlib import Path


ROOT = Path("artifacts/marl/b0_v3_capturer_clbc1_f3")
ARMS = ("f2_control", "f3_robust_fire_bc")
CONTROL, F3 = ARMS


def _input_robust(record: dict) -> bool | None:
    event = record.get("policy_input_at_fire")
    if event is None:
        return None
    return bool(float(event["p_feasible"]) > 0.0 and float(event["v_shot_worst"]) >= 1.0)


def _discordance(control: dict, f3: dict, predicate) -> dict:
    counts = Counter((predicate(control[sid]), predicate(f3[sid])) for sid in control)
    return {"neither": counts[(False, False)], "control_only": counts[(True, False)],
            "f3_only": counts[(False, True)], "both": counts[(True, True)]}


def analyze_seed(control_rows: list[dict], f3_rows: list[dict]) -> dict:
    control = {int(r["scenario_id"]): r for r in control_rows}
    f3 = {int(r["scenario_id"]): r for r in f3_rows}
    if control.keys() != f3.keys():
        raise ValueError("F3 arms are not paired")
    transitions = Counter(f"{control[s]['outcome']}->{f3[s]['outcome']}" for s in control)
    f3_fires = [r for r in f3_rows if r.get("accepted_fire_judge") is not None]
    f3_draw_flips = [r for r in f3_fires
                     if _input_robust(r) != bool(r["accepted_fire_judge"]["robust_ready"])]
    lost_n = [s for s in control if control[s]["bin"] == "N" and f3[s]["bin"] != "N"]
    gained_n = [s for s in control if control[s]["bin"] != "N" and f3[s]["bin"] == "N"]
    lost_details = []
    for sid in lost_n:
        c, f = control[sid], f3[sid]
        lost_details.append({"scenario_id": sid, "cell_id": c["cell_id"],
                             "control_policy_input_robust": _input_robust(c),
                             "control_authoritative_robust": bool(
                                 c["accepted_fire_judge"]["robust_ready"]),
                             "f3_outcome": f["outcome"]})
    return {
        "N_discordance": _discordance(control, f3, lambda r: r["bin"] == "N"),
        "FIRE_discordance": _discordance(control, f3, lambda r: bool(r["fire"])),
        "terminal_transitions": dict(sorted(transitions.items())),
        "gained_N_scenarios": gained_n, "lost_N": lost_details,
        "pairwise_equal_clean_crossings": sum(
            control[s]["clean_crossings"] == f3[s]["clean_crossings"] for s in control),
        "f3_accepted_FIRE": len(f3_fires),
        "f3_input_vs_authoritative_draw_flips": [{
            "scenario_id": int(r["scenario_id"]), "cell_id": r["cell_id"],
            "outcome": r["outcome"], "policy_input_robust": _input_robust(r),
            "policy_input": r["policy_input_at_fire"],
            "authoritative": r["accepted_fire_judge"],
        } for r in f3_draw_flips],
        "f3_nonrobust_FIRE_all_explained_by_draw_flip": all(
            _input_robust(r) is True for r in f3_fires
            if not r["accepted_fire_judge"]["robust_ready"]),
    }


def analyze(root: Path = ROOT) -> dict:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    readout = json.loads((root / "readout.json").read_text(encoding="utf-8"))
    valid = (manifest["manifest_hash"] == readout["manifest_hash"]
             and readout["decision"] == "PASS_F3_TO_CAPTURER_ONLY_RL_CONTRACT_DRAFT")
    seeds = {}
    for seed in (0, 1):
        payloads = {arm: json.loads(
            (root / f"seed{seed}" / f"evaluation_{arm}.json").read_text(encoding="utf-8"))
                    for arm in ARMS}
        valid &= all(p["manifest_hash"] == manifest["manifest_hash"]
                     and p["code_commit"] == "09f3e0b"
                     and p["actor_seed"] == seed and p["arm"] == arm
                     for arm, p in payloads.items())
        seeds[str(seed)] = analyze_seed(payloads[CONTROL]["records"], payloads[F3]["records"])
    return {"schema": "b0-v3-capturer-clbc1-f3-posthoc-v1",
            "manifest_hash": manifest["manifest_hash"], "sealed_decision": readout["decision"],
            "read_only": True, "lineage_and_pairing_valid": bool(valid),
            "scope": "mechanism readout only; sealed gate and decisions unchanged",
            "seeds": seeds}


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
