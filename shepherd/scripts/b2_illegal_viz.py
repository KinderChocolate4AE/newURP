"""Deterministic replay of representative B2 illegal-engagement cases.

Selection is fixed before plotting: among paired ``SOLO=N`` and
``RULE_COOP=H_illegal`` scenarios, replay the minimum, median-rank, and maximum
scenario IDs.  The script verifies each replay against the stored primary row
and writes one JSON audit plus one static figure.
"""
from __future__ import annotations

import dataclasses
import glob
import json
import pathlib
import subprocess
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.env_sys import _seg_min_dist                              # noqa: E402
from shepherd.m4_env import build_m4_env                               # noqa: E402
from shepherd.provenance import git_commit                             # noqa: E402
from shepherd.scripts.b2_manifest import OUT_DIR, load                 # noqa: E402
from shepherd.scripts.b2_run import (ARM_ORDER, _index, _unit_of,      # noqa: E402
                                     scenario_kwargs)
from shepherd.scripts.mission_rollout import partition_bin, run_episode  # noqa: E402

PRIMARY = OUT_DIR / "primary"
VIZ_DIR = OUT_DIR / "viz"
OUT_JSON = VIZ_DIR / "illegal_replay.json"
OUT_PNG = VIZ_DIR / "illegal_replay.png"


def _primary() -> tuple[dict, dict[int, dict[str, dict]], set[str]]:
    paired: dict[int, dict[str, dict]] = {}
    commits: set[str] = set()
    for path in sorted(PRIMARY.glob("shard*.json")):
        blob = json.loads(path.read_text(encoding="utf-8"))
        commits.add(blob["code_commit"])
        for row in blob["records"]:
            paired.setdefault(row["s"], {})[row["arm"]] = row
    assert paired and all(set(x) == set(ARM_ORDER) for x in paired.values())
    return load(), paired, commits


def _select(paired: dict[int, dict[str, dict]]) -> list[int]:
    candidates = sorted(
        s for s, rows in paired.items()
        if rows["SOLO"]["bin"] == "N"
        and rows["RULE_COOP"]["bin"] == "H_illegal")
    assert candidates
    return [candidates[0], candidates[len(candidates) // 2], candidates[-1]]


def _replay(m: dict, blocks: list, stored: dict, s: int, arm: str) -> dict:
    cell, _unit = _unit_of(blocks, s)
    chi, eta, kw = scenario_kwargs(m, cell, s)
    a, common, fallback = m["arms"][arm], m["common"], m["fallback"]
    stack = build_m4_env(m["crn"]["seed0"], s, **kw)
    telemetry: list[dict] = []
    result = run_episode(
        stack.env, stack.scn, stack.lay, seed=m["crn"]["seed0"] + s,
        limiter_mode=a["limiter_mode"], limiter_kw=a["limiter_kw"],
        fire_mode=common["fire_mode"],
        baseline_commit=common["baseline_commit_net_phase"],
        kinetic_fallback={"limiter_mode": fallback["controller"],
                          "baseline_commit": fallback["baseline_commit"]},
        telemetry=telemetry,
    )

    # ModeSystemEnv stores the raw post-step positions before a consumed
    # limiter is parked.  Using env._states() here would corrupt the event path.
    telemetry.append({
        "t": len(telemetry),
        "p_att": np.asarray(stack.env.p_att_post_raw, float).tolist(),
        "p_lims": [np.asarray(p, float).tolist() for p in stack.env.lims_post_raw],
    })
    distances, nearest = [], []
    for t in range(len(telemetry) - 1):
        d = [
            _seg_min_dist(
                np.asarray(telemetry[t]["p_att"]) - np.asarray(telemetry[t]["p_lims"][i]),
                np.asarray(telemetry[t + 1]["p_att"]) - np.asarray(telemetry[t + 1]["p_lims"][i]),
            )
            for i in range(len(telemetry[t]["p_lims"]))
        ]
        nearest.append(int(np.argmin(d)))
        distances.append(float(min(d)))

    replay = {
        "bin": partition_bin(result), "label": result.label,
        "fire_step": result.fire_step, "steps": result.steps,
        "n_contact": result.n_contact,
        "first_engage_t": result.meta["first_engage_t"],
        "n_engage": result.meta["n_engage"],
        "hard_kill": result.meta["hard_kill"],
    }
    expected = {k: stored[k] for k in replay}
    parity = replay == expected

    contacts = [dataclasses.asdict(x) for x in stack.env.commits if x.source == "contact"]
    radius = (stack.env.spec.r_contact if stack.env.spec.r_contact is not None
              else stack.env.kill_radius)
    return {
        "arm": arm, "stored": expected, "replayed": replay,
        "replay_parity": parity,
        "chi": chi, "eta": eta, "cell_id": cell["cell_id"],
        "target": np.asarray(stack.lay.target, float).tolist(),
        "r_contact": float(radius), "contact_events": contacts,
        "min_swept_distance": float(min(distances)),
        "min_swept_step": int(np.argmin(distances)),
        "nearest_limiter_by_step": nearest,
        "min_swept_by_step": distances, "telemetry": telemetry,
    }


def _render(rows: list[dict]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    valid = [x for x in rows if all(x[a]["replay_parity"] for a in ARM_ORDER)]
    assert valid, "no selected case reproduced on this host"
    fig, axes = plt.subplots(len(valid), 3, squeeze=False,
                             figsize=(13.5, 3.7 * len(valid)), constrained_layout=True)
    for ri, case in enumerate(valid):
        rule_event = case["RULE_COOP"]["contact_events"][0]
        event_limiter = int(rule_event["limiter_index"])
        for ci, arm in enumerate(ARM_ORDER):
            d = case[arm]
            tel = d["telemetry"]
            att = np.asarray([x["p_att"] for x in tel])
            lim = np.asarray([x["p_lims"] for x in tel])
            ax = axes[ri, ci]
            for j in range(lim.shape[1]):
                ax.plot(lim[:, j, 0], lim[:, j, 1], color=("tab:red" if j == event_limiter else "0.75"),
                        lw=(2.0 if j == event_limiter else 0.8), alpha=0.9)
            ax.plot(att[:, 0], att[:, 1], color="black", lw=2, label="attacker")
            fs = d["stored"]["fire_step"]
            if fs is not None:
                ax.scatter(att[fs, 0], att[fs, 1], marker="*", s=90,
                           color="gold", edgecolor="black", zorder=4, label="FIRE")
            et = d["stored"]["first_engage_t"]
            if et is not None:
                ax.scatter(att[et, 0], att[et, 1], marker="x", s=75,
                           color="tab:red", linewidth=2.5, zorder=5, label="engagement")
            target = np.asarray(d["target"])
            ax.scatter(target[0], target[1], marker="P", s=55, color="tab:green")
            ax.set_aspect("equal", adjustable="datalim")
            ax.grid(alpha=0.2)
            ax.set_title(f"s={case['s']}  {arm}\n{d['stored']['bin']} · fire={fs} · engage={et}")
            ax.set_xlabel("x [m]")
            ax.set_ylabel("y [m]")

        ax = axes[ri, 2]
        for arm, color, style in (("SOLO", "tab:blue", "--"),
                                  ("RULE_COOP", "tab:red", "-")):
            d = case[arm]
            ax.plot(range(len(d["min_swept_by_step"])), d["min_swept_by_step"],
                    style, color=color, lw=1.8, label=arm)
            fs = d["stored"]["fire_step"]
            if fs is not None:
                ax.axvline(fs, color=color, lw=0.8, alpha=0.25)
        ax.axhline(case["RULE_COOP"]["r_contact"], color="black", lw=1,
                   label=r"$r_{contact}=0.75$ m")
        et = case["RULE_COOP"]["stored"]["first_engage_t"]
        ax.scatter([et], [rule_event["d_nom"]], color="tab:red", marker="x", s=70, zorder=5)
        ax.set_ylim(bottom=0)
        ax.set_xlabel("control step")
        ax.set_ylabel("minimum swept separation [m]")
        ax.grid(alpha=0.2)
        ax.set_title(f"event d={rule_event['d_nom']:.3f} m")
        if ri == 0:
            ax.legend(fontsize=8)

    fig.suptitle(f"B2 replay: SOLO=N → RULE_COOP=H_illegal "
                 f"({len(valid)}/{len(rows)} selected cases reproduced on this host)", fontsize=14)
    fig.savefig(OUT_PNG, dpi=180)
    plt.close(fig)


def main() -> None:
    m, paired, raw_commits = _primary()
    assert len(raw_commits) == 1, raw_commits
    raw_commit = next(iter(raw_commits))
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", raw_commit, "--", "shepherd"],
        cwd=ROOT, text=True).splitlines()
    changed = [p.replace("\\", "/") for p in changed
               if p.replace("\\", "/") != "shepherd/scripts/b2_illegal_viz.py"]
    code_unchanged = not changed
    assert code_unchanged, f"replay code changed since primary commit {raw_commit}: {changed}"
    _, blocks = _index(m)
    selected = _select(paired)
    cases = []
    for s in selected:
        case = {"s": s, "selection_rank": selected.index(s)}
        for arm in ARM_ORDER:
            case[arm] = _replay(m, blocks, paired[s][arm], s, arm)
        cases.append(case)

    illegal = [x["RULE_COOP"] for x in paired.values()
               if x["RULE_COOP"]["bin"] == "H_illegal"]
    passed = [x["s"] for x in cases if all(x[a]["replay_parity"] for a in ARM_ORDER)]
    failed = [x["s"] for x in cases if x["s"] not in passed]
    payload = {
        "schema": "b2-illegal-replay-v1",
        "selection_rule": "minimum, median-rank, maximum scenario ID among SOLO=N and RULE_COOP=H_illegal",
        "candidate_count": sum(x["SOLO"]["bin"] == "N"
                               and x["RULE_COOP"]["bin"] == "H_illegal"
                               for x in paired.values()),
        "selected": selected, "raw_code_commit": raw_commit,
        "replay_head": git_commit(), "replay_code_unchanged_since_primary": code_unchanged,
        "replay_parity": {"passed": passed, "failed": failed},
        "illegal_accounting": {
            "n": len(illegal),
            "n_with_point_contact": sum(x["n_contact"] > 0 for x in illegal),
            "n_with_swept_engagement": sum(x["n_engage"] > 0 for x in illegal),
            "n_hard_kill": sum(bool(x["hard_kill"]) for x in illegal),
        },
        "cases": cases,
        "interpretation_limit": "The 0.75 m swept event is a modelled kinetic-engagement opportunity, not rigid-body collision physics.",
    }
    VIZ_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    _render(cases)
    print(f"selected {selected}; replay parity PASS={passed} FAIL={failed}")
    print(f"illegal: {len(illegal)} total, {payload['illegal_accounting']['n_with_point_contact']} point-contact, "
          f"{payload['illegal_accounting']['n_with_swept_engagement']} swept-engagement")
    print(OUT_JSON.relative_to(ROOT))
    print(OUT_PNG.relative_to(ROOT))


if __name__ == "__main__":
    main()
