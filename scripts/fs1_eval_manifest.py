"""Seal FS1 평가 계약 v1 (docs/123 §8) + 판독.

    python scripts/fs1_eval_manifest.py                      # manifest 기록 (봉인)
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
        r = readout(pathlib.Path(a.readout))
        (pathlib.Path(a.readout) / "readout.json").write_text(json.dumps(r, indent=2), "utf-8")
        print(json.dumps(r, indent=2))
        return
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{MANIFEST} {build()['manifest_hash']}")


if __name__ == "__main__":
    sys.exit(main())
