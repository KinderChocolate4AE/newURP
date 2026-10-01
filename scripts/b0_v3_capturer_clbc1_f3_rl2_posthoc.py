"""Read-only fire-discipline audit for harvested CLBC1-F3-RL2.

Classifies every nonrobust accepted FIRE in both arms as a draw flip
(policy input said robust, authoritative judge said not) or an interior
violation (policy input already said nonrobust). Sealed STOP_RL2 unchanged.
"""
from __future__ import annotations

from collections import Counter
import argparse
import json
from pathlib import Path


ROOT = Path("artifacts/marl/b0_v3_capturer_clbc1_f3_rl2")
ARMS = ("f3_frozen_control", "f3_aim_ppo")
CONTROL, PPO = ARMS


def _input_robust(record: dict) -> bool | None:
    event = record.get("policy_input_at_fire")
    if event is None:
        return None
    return bool(float(event["p_feasible"]) > 0.0 and float(event["v_shot_worst"]) >= 1.0)


def _nonrobust_fires(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        judge = r.get("accepted_fire_judge")
        if judge is None or bool(judge["robust_ready"]):
            continue
        kind = {True: "draw_flip", False: "interior", None: "unknown"}[_input_robust(r)]
        out.append({"scenario_id": int(r["scenario_id"]), "cell_id": r["cell_id"],
                    "outcome": r["outcome"], "kind": kind,
                    "policy_input_robust": _input_robust(r),
                    "policy_input": r["policy_input_at_fire"],
                    "authoritative": judge})
    return out


def _discordance(control: dict, ppo: dict, predicate) -> dict:
    counts = Counter((predicate(control[sid]), predicate(ppo[sid])) for sid in control)
    return {"neither": counts[(False, False)], "control_only": counts[(True, False)],
            "ppo_only": counts[(False, True)], "both": counts[(True, True)]}


def analyze_seed(control_rows: list[dict], ppo_rows: list[dict]) -> dict:
    control = {int(r["scenario_id"]): r for r in control_rows}
    ppo = {int(r["scenario_id"]): r for r in ppo_rows}
    if control.keys() != ppo.keys():
        raise ValueError("RL2 arms are not paired")
    transitions = Counter(f"{control[s]['outcome']}->{ppo[s]['outcome']}" for s in control)
    nonrobust = {arm: _nonrobust_fires(rows) for arm, rows in
                 ((CONTROL, control_rows), (PPO, ppo_rows))}
    spent = {arm: sorted(int(r["scenario_id"]) for r in rows
                         if r["outcome"] == "SPENT_FAIL")
             for arm, rows in ((CONTROL, control_rows), (PPO, ppo_rows))}
    return {
        "N_discordance": _discordance(control, ppo, lambda r: r["bin"] == "N"),
        "FIRE_discordance": _discordance(control, ppo, lambda r: bool(r["fire"])),
        "terminal_transitions": dict(sorted(transitions.items())),
        "gained_N_scenarios": sorted(s for s in control
                                     if control[s]["bin"] != "N" and ppo[s]["bin"] == "N"),
        "lost_N_scenarios": sorted(s for s in control
                                   if control[s]["bin"] == "N" and ppo[s]["bin"] != "N"),
        "nonrobust_FIRE": nonrobust,
        "nonrobust_kind_counts": {arm: dict(Counter(e["kind"] for e in events))
                                  for arm, events in nonrobust.items()},
        "spent_fail_scenarios": spent,
        "spent_equals_nonrobust": {arm: spent[arm] == sorted(
            e["scenario_id"] for e in nonrobust[arm]) for arm in ARMS},
        "all_nonrobust_are_draw_flips": {arm: all(e["kind"] == "draw_flip"
                                                  for e in nonrobust[arm])
                                         for arm in ARMS},
    }


def analyze(root: Path = ROOT) -> dict:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    readout = json.loads((root / "readout.json").read_text(encoding="utf-8"))
    valid = (manifest["manifest_hash"] == readout["manifest_hash"]
             and readout["decision"] == "STOP_RL2")
    seeds = {}
    for seed in (0, 1):
        payloads = {arm: json.loads(
            (root / f"seed{seed}" / f"evaluation_{arm}.json").read_text(encoding="utf-8"))
                    for arm in ARMS}
        valid &= all(p["manifest_hash"] == manifest["manifest_hash"]
                     and p["code_commit"] == "84b4517"
                     and p["actor_seed"] == seed and p["arm"] == arm
                     for arm, p in payloads.items())
        seeds[str(seed)] = analyze_seed(payloads[CONTROL]["records"], payloads[PPO]["records"])
    return {"schema": "b0-v3-capturer-clbc1-f3-rl2-posthoc-v1",
            "manifest_hash": manifest["manifest_hash"], "sealed_decision": readout["decision"],
            "read_only": True, "lineage_and_pairing_valid": bool(valid),
            "scope": "mechanism readout only; sealed gate and STOP_RL2 unchanged",
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
