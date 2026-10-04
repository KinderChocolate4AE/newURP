"""Seal FS1 평가 계약 v1 (docs/123 §8) + 판독.

    python scripts/fs1_eval_manifest.py                      # manifest v1 + v2 addendum 기록 (봉인)
    python scripts/fs1_eval_manifest.py --readout artifacts/fs1/run3/eval_v1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "fs1" / "eval_v1_manifest.json"
SEED0 = 261000
N = 240                                   # (방어, 그룹) 셀당 episode
MARGIN = 24                               # +10%p of 240
TRAIN_STEPS_MIN = 1.1e8
EX_STEPS = 1e7
DEFENDERS = ["learned_det", "learned_sto", "fin12", "fin12_fb", "kfirst50"]
SCRIPTED = ["fin12", "fin12_fb", "kfirst50"]
GROUPS = ["ladder", "rl_latest", "pool", "ex_learned", "ex_kfirst50"]


def build() -> dict:
    body = {
        "schema": "fs1-eval-manifest-v1",
        "status": "sealed before the run3 harvest (training outcome unseen except the in-training log and the iter-119 ad hoc probe recorded in note 2026-10-04e)",
        "design_doc": "docs/123_fs1_full_stack_cotraining.md section 8",
        "scope": {
            "question": ("does the FS1 co-trained defense (final checkpoint, deterministic actions) "
                         "defend more often than the best scripted defense against adaptive attackers "
                         "(attacker-pool snapshots and a fresh exploiter trained against it)"),
            "not_evidence_for": ["6DOF or plant transfer", "optimality of any policy",
                                 "B0 v3 / P1 / P2 claims (new world, never pooled)",
                                 "JAX-port results (parity unsealed)",
                                 "cooperation (vocabulary: limiter-control opportunity)"],
        },
        "checkpoint": f"final ckpt.pt of the training run (total_steps >= {TRAIN_STEPS_MIN:.1e}); no iteration selection",
        "defenders": {
            "learned_det": "ckpt defense team, deterministic (mean action, p>0.5 arm) - GATED",
            "learned_sto": "ckpt defense team, stochastic - reported",
            "fin12": "scripted: hold start station, finisher armed r_fire 12 m, limiters never armed",
            "fin12_fb": "fin12 + limiters armed after net spent (= training pool scripted_fin12)",
            "kfirst50": "fin12_fb + limiters armed when attacker within 50 m of asset (= training pool scripted_kfirst50)",
        },
        "opponent_groups": {
            "ladder": "P1a ladder 24 configs, episode i uses config i mod 24 (10 each)",
            "rl_latest": "final attacker team of the same ckpt (co-training partner) - reported only",
            "pool": "8 attacker-pool nn snapshots evenly spaced (np.linspace, rounded) over the final pool, episode i uses snapshot i mod 8 (30 each)",
            "ex_learned": (f"fresh attacker trained from scratch against frozen learned_det only, "
                           f"{EX_STEPS:.0e} env steps, seed {SEED0 + 100}"),
            "ex_kfirst50": (f"fresh attacker trained from scratch against kfirst50 only, "
                            f"{EX_STEPS:.0e} env steps, seed {SEED0 + 200}"),
            "attacker_actions": "RL attackers act stochastically (as in training)",
        },
        "evaluation": {
            "namespace": "fs1_eval_v1", "seed0": SEED0, "episodes_per_cell": N,
            "paired": "episode i of every group uses seed seed0 + i for every defender (identical placements)",
            "tool": "python -m shepherd.fs1.eval run (scripts/run_fs1_eval_server.sh)",
            "defended": "label in {NET_CAPTURE, CAPTURE_WITH_CONTACT, HARD_KILL, K_FIRST}",
        },
        "gate": {
            "invalid": ["manifest hash recorded in summary", "lineage: ckpt total_steps >= 1.1e8",
                        f"completion: every (defender, group) cell n = {N}",
                        "paired: identical seed lists across defenders within each group",
                        f"exploiter budget: both exploiter logs reach total_steps >= {EX_STEPS:.0e}"],
            "invalid_decision": "INVALID_FS1E",
            "classification": (
                f"counts out of {N}: D_pool = L(pool) - max_s S_s(pool); D_ex = L(ex_learned) - "
                f"S_kfirst50(ex_kfirst50) (each defense vs its own exploiter, equal budget); "
                f"D_ladder = L(ladder) - max_s S_s(ladder); L = learned_det defended, s over "
                f"{SCRIPTED}. If D_pool >= +{MARGIN} and D_ex >= +{MARGIN}: FS1_POSITIVE, "
                f"relabelled FS1_POSITIVE_NARROW when D_ladder <= -{MARGIN} (gain on adaptive "
                f"attackers only; degeneration warning). Else FS1_NULL (this training seed)."),
            "reported_not_gated": ["learned_sto", "rl_latest", "cross-exploiter cells",
                                   "net / K_FIRST / fallback / penetrated per cell",
                                   "mode-rank reversal: K_FIRST share ladder vs adaptive groups (docs/123 section 7)",
                                   "arm distance and fire distance medians", "trajectory figures (viz-first)"],
        },
        "replication": ("run3 = training seed 0 -> provisional. Confirmed FS1_POSITIVE requires >= 2 of 3 "
                        "training seeds {0, 1, 2} (same r3 design and budget) classified POSITIVE or "
                        "POSITIVE_NARROW under this manifest; label NARROW if >= 2 of the passing seeds are NARROW."),
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data != build():
        raise ValueError(f"FS1 eval manifest drift: {MANIFEST}")
    return data


# ---------------------------------------------------------------- v2 addendum ---
MANIFEST_V2 = ROOT / "artifacts" / "fs1" / "eval_v2_addendum_manifest.json"


def build_v2() -> dict:
    body = {
        "schema": "fs1-eval-manifest-v2-addendum",
        "status": ("sealed before the run3 harvest; addendum to v1 (not a replacement) after the "
                   "ladder-spec bug report 2026-10-05 (JAX session, verified by main)"),
        "design_doc": "docs/123_fs1_full_stack_cotraining.md section 8.1",
        "v1_manifest_hash": build()["manifest_hash"],
        "v1_deviation": ("v1 'ladder' group was built as AttackerSpec(level=A2, **overrides) on the "
                         "dataclass defaults, not on the cell nominal spec as P1a did: all 24 configs "
                         "have jink_amp 0 (nominal 0.6), t0_route0 == a1_pure, and under lean "
                         "depth_bait_priv == depth_bait_fair. v1 is run exactly as sealed "
                         "(eval --ladder legacy) and reported with this deviation."),
        "v2_ladder": ("eval --ladder nominal: replace(FS1 cell resolve() attacker spec, "
                      "sense_range=inf, **P1a overrides) (overrides win, so P1a sense 15/30 kept); "
                      "jink phase = derive_phase(0, episode seed); depth_bait_priv kept as a labelled "
                      "duplicate of depth_bait_fair (24 configs, 10 each)"),
        "evaluation": {"cells": f"{DEFENDERS} x ladder_v2", "episodes_per_cell": N, "seed0": SEED0,
                       "paired": "same seeds as v1 (seed0 + i)"},
        "classification": (
            "v2 decision = v1 rule with D_ladder recomputed on ladder_v2 (D_pool, D_ex from v1 "
            "unchanged — those groups do not use the ladder). INVALID if v1 is INVALID or the "
            "ladder_v2 cells fail completion/paired. Both v1 and v2 decisions are reported; where "
            "they differ, v2 governs (v1 ladder did not match its declared population). "
            "The replication rule of v1 applies to the v2 decision."),
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def load_v2() -> dict:
    data = json.loads(MANIFEST_V2.read_text(encoding="utf-8"))
    if data != build_v2():
        raise ValueError(f"FS1 eval v2 manifest drift: {MANIFEST_V2}")
    return data


# ---------------------------------------------------------- r4 replication ---
MANIFEST_R4 = ROOT / "artifacts" / "fs1" / "r4_replication_manifest.json"
R4_SEEDS = [0, 1, 2]


def build_r4() -> dict:
    body = {
        "schema": "fs1-r4-replication-manifest-v1",
        "status": "sealed before any r4 training (user decision 2026-10-05: option (a))",
        "design_doc": "docs/123_fs1_full_stack_cotraining.md section 9",
        "v1_manifest_hash": build()["manifest_hash"], "v2_manifest_hash": build_v2()["manifest_hash"],
        "design_r4": ("r3 + (1) ladder attackers on the cell nominal spec (train.ladder_attacker) in pool "
                      "and BC, (2) attacker diversity penalty off (LAMBDA_DIV 0, discriminator kept as "
                      "monitor), (3) KL-targeted lr (target 0.01, x/÷1.5 per own iter, bounds 1e-5..3e-4, "
                      "start def 3e-5 / att 1e-4), (4) worker torch seeding per rollout job. Everything "
                      "else as r3; batch 49152 steps per iter (6 workers x 8192); budget 1.1e8 env steps."),
        "seeds": {"training_and_bc": R4_SEEDS, "out": "artifacts/fs1/r4_s{seed}",
                  "orchestrator": "scripts/run_fs1_r4_server.sh (3 seeds in parallel)"},
        "per_seed_evaluation": "scripts/run_fs1_eval_server.sh: v1 procedure + v2 addendum; the seed's decision = v2 decision",
        "confirmation": ("FS1_CONFIRMED if >= 2 of the 3 r4 seeds are FS1_POSITIVE or FS1_POSITIVE_NARROW; "
                         "labelled FS1_CONFIRMED_NARROW if >= 2 of the passing seeds are NARROW. "
                         "Else FS1_NOT_CONFIRMED. An INVALID seed is re-evaluated (evaluation only, after "
                         "fixing an evaluation-side cause); training is never rerun to change a decision."),
        "pilot": ("run3 (r3, legacy ladder, seed 0) is a pilot: evaluated and reported under v1/v2, "
                  "never counted toward confirmation and never pooled with r4."),
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {**body, "manifest_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def confirm(decisions: list) -> str:
    """r4 seed 별 v2 판정 리스트 → 확정 판정 (build_r4 'confirmation')."""
    passing = [d for d in decisions if d.startswith("FS1_POSITIVE")]
    if len(passing) < 2:
        return "FS1_NOT_CONFIRMED"
    return "FS1_CONFIRMED_NARROW" if sum(d.endswith("NARROW") for d in passing) >= 2 else "FS1_CONFIRMED"


def readout_v2(d: pathlib.Path, v1: dict) -> dict:
    m = load_v2()
    s = json.loads((d / "eval_v2" / "summary.json").read_text(encoding="utf-8"))
    cell = {r["defender"]: r for r in s["rows"] if r["group"] == "ladder"}
    seeds = {}
    for l in (d / "eval_v2" / "episodes.jsonl").read_text(encoding="utf-8").splitlines():
        e = json.loads(l)
        seeds.setdefault(e["defender"], []).append(e["seed"])
    inv = [f"v1 {x}" for x in v1["invalid"]]
    if s["meta"].get("manifest") != m["manifest_hash"] or s["meta"].get("ladder") != "nominal":
        inv.append("manifest/ladder")
    inv += [f"completion {x}" for x in DEFENDERS if cell.get(x, {}).get("n") != N]
    if len({tuple(sorted(v)) for v in seeds.values()}) != 1:
        inv.append("paired")
    out = {"manifest_hash": m["manifest_hash"], "invalid": inv, "v1_decision": v1["decision"]}
    if inv:
        out["decision"] = "INVALID_FS1E"
        return out
    out["D_ladder_v2"] = cell["learned_det"]["defended"] - max(cell[x]["defended"] for x in SCRIPTED)
    pos = v1["D_pool"] >= MARGIN and v1["D_ex"] >= MARGIN
    out["decision"] = ("FS1_NULL" if not pos else
                       "FS1_POSITIVE_NARROW" if out["D_ladder_v2"] <= -MARGIN else "FS1_POSITIVE")
    return out


def _last_steps(log):
    lines = pathlib.Path(log).read_text(encoding="utf-8").strip().splitlines()
    return json.loads(lines[-1])["total_steps"] if lines else 0


def readout(d: pathlib.Path) -> dict:
    m = load()
    s = json.loads((d / "eval" / "summary.json").read_text(encoding="utf-8"))
    meta, cell = s["meta"], {(r["defender"], r["group"]): r for r in s["rows"]}
    seeds = {}
    for l in (d / "eval" / "episodes.jsonl").read_text(encoding="utf-8").splitlines():
        e = json.loads(l)
        seeds.setdefault(e["group"], {}).setdefault(e["defender"], []).append(e["seed"])
    inv = []
    if meta.get("manifest") != m["manifest_hash"]:
        inv.append("manifest")
    if (meta.get("ckpt_total_steps") or 0) < TRAIN_STEPS_MIN:
        inv.append("lineage")
    inv += [f"completion {k}" for k in ((x, g) for x in DEFENDERS for g in GROUPS)
            if cell.get(k, {}).get("n") != N]
    inv += [f"paired {g}" for g in GROUPS
            if len({tuple(sorted(v)) for v in seeds.get(g, {}).values()}) != 1]
    inv += [f"exploiter budget {x}" for x in ("learned", "kfirst50")
            if _last_steps(d / f"exploit_{x}" / "log.jsonl") < EX_STEPS]
    D = lambda d_, g: cell[(d_, g)]["defended"]
    out = {"manifest_hash": m["manifest_hash"], "invalid": inv}
    if inv:
        out["decision"] = "INVALID_FS1E"
        return out
    best = lambda g: max(D(x, g) for x in SCRIPTED)
    out.update(D_pool=D("learned_det", "pool") - best("pool"),
               D_ex=D("learned_det", "ex_learned") - D("kfirst50", "ex_kfirst50"),
               D_ladder=D("learned_det", "ladder") - best("ladder"))
    pos = out["D_pool"] >= MARGIN and out["D_ex"] >= MARGIN
    out["decision"] = ("FS1_NULL" if not pos else
                       "FS1_POSITIVE_NARROW" if out["D_ladder"] <= -MARGIN else "FS1_POSITIVE")
    out["kfirst_share"] = {g: round(cell[("learned_det", g)]["k_first"] / max(D("learned_det", g), 1), 3)
                           for g in GROUPS}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--readout", default=None, help="평가 디렉터리 (exploit_*/, eval/ 포함)")
    a = ap.parse_args()
    if a.readout:
        d = pathlib.Path(a.readout)
        r = readout(d)
        if (d / "eval_v2").exists():
            r = {"v1": r, "v2": readout_v2(d, r)}
        (d / "readout.json").write_text(json.dumps(r, indent=2), "utf-8")
        print(json.dumps(r, indent=2))
        return
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    for path, body in ((MANIFEST, build()), (MANIFEST_V2, build_v2()), (MANIFEST_R4, build_r4())):
        path.write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{path} {body['manifest_hash']}")


if __name__ == "__main__":
    sys.exit(main())
