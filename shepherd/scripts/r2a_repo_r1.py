"""repo-R1 provenance pass — R2a 캠페인 사슬 한정 (docs/81 §R1 이행).

    python -m shepherd.scripts.r2a_repo_r1

원칙: historical preservation first — 기존 artifact 는 무수정, **campaign-level
provenance manifest sidecar** 를 생성한다. 각 artifact 에 대해 git 생성 커밋 ·
내장 hash · 소속 계약 · threat class 를 기계 수집하고, 스탬프 누락(고아) artifact
가 0 임을 검사한다. Exit = frozen output 무변경 (git 추적) + 전체 테스트 green.
Stage 3 readout 의 하드 게이트 (protocol eb3a85e702020167 run_lineage).
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
ART = ROOT / "artifacts/r2a"

CAMPAIGNS = {
    "stage0":   {"files": ["stage0_envelope.json", "stage0_rows.png"],
                 "contract": "R2a-L/P design input", "status": "exploratory"},
    "lattices": {"files": ["lattice_R2a_L.json", "lattice_R2a_P.json", "lattice_R2a_P3.json"],
                 "contract": "seal chain (supersession recorded in-file)", "status": "sealed"},
    "provenance": {"files": ["provenance_route_sense.json"],
                   "contract": "D-2 evidence", "status": "verification"},
    "stage1":   {"files": ["stage1_protocol.json", "stage1_feasibility.json",
                           "stage1_pathwise.json", "stage1_dt_check.json",
                           "stage1_dt_review.json", "stage1_readout.json",
                           "stage1_viz_ep0.png", "stage1_viz_ep1.png"],
                 "glob": "stage1/shard*.json", "contract": "1496a4769876b438",
                 "status": "kill screen (falsification)"},
    "stage2":   {"files": ["stage2_protocol.json", "stage2_readout.json"],
                 "glob": "stage2/shard*.json", "contract": "3bc9dba2fe01385f",
                 "status": "lam0 reference slice"},
    "stage4":   {"files": ["stage4_protocol.json", "stage4_readout.json"],
                 "glob": "stage4/shard*.json", "contract": "59c4de1889ed72dc",
                 "status": "orthogonal lambda test (POSITIVE)"},
    "scout_l2": {"files": ["scout_l2_protocol.json", "scout_l2_envelope.json"],
                 "glob": "scout_l2/shard*.json", "contract": "fa3d149eb846c00d",
                 "status": "exploratory"},
    "stage3":   {"files": ["stage3_protocol.json"], "glob": "stage3/shard*.json",
                 "contract": "eb3a85e702020167", "status": "confirmatory (readout pending)"},
}
THREAT = "A2-reactive sealed evasion vector (jink 0.6, route 0.5, sense 30) — see conditioning_vector"


def _git_commit(path: pathlib.Path) -> str:
    r = subprocess.run(["git", "log", "-1", "--format=%h", "--", str(path)],
                       cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip() or "UNCOMMITTED"


def run() -> dict:
    manifest, orphans, uncommitted = {}, [], []
    covered = set()
    for name, c in CAMPAIGNS.items():
        entries = []
        paths = [ART / f for f in c["files"]]
        if "glob" in c:
            paths += sorted(ART.glob(c["glob"]))
        for p in paths:
            assert p.exists(), f"declared artifact missing: {p}"
            covered.add(p.resolve())
            commit = _git_commit(p)
            if commit == "UNCOMMITTED":
                uncommitted.append(str(p.relative_to(ROOT)))
            entries.append({"file": str(p.relative_to(ROOT)).replace("\\", "/"),
                            "git_commit": commit})
        manifest[name] = {"threat_class": THREAT, "contract": c["contract"],
                          "campaign_status": c["status"], "artifacts": entries}
    # 고아 검사: artifacts/r2a 아래 미선언 파일 = 스탬프 누락
    for p in ART.rglob("*"):
        if p.is_file() and p.resolve() not in covered and p.name != "repo_r1_manifest.json":
            orphans.append(str(p.relative_to(ROOT)))
    # frozen output 무변경 (results/ 추적 파일에 로컬 수정 없음)
    dirty = subprocess.run(["git", "status", "--porcelain", "results/"],
                           cwd=ROOT, capture_output=True, text=True).stdout
    frozen_clean = not any(line and not line.startswith("??") for line in dirty.splitlines())
    out = {"pass": "repo-R1 (scoped: R2a campaign chain; docs/81 §R1)",
           "principle": "historical preservation first — sidecar manifest only, no retro-edit",
           "world_lineage": "results/curve_hold_reactive.manifest.json (commit 43acc39) -> "
                            "provenance_route_sense.json CONFIRMED -> sealed conditioning vector",
           "campaigns": manifest, "orphan_artifacts": orphans,
           "uncommitted_artifacts": uncommitted,
           "frozen_results_unmodified": frozen_clean,
           "quarantine_rule": "if this pass had failed, the Stage 3 run would be "
                              "quarantined and re-executed under a new lineage (protocol "
                              "eb3a85e702020167 run_lineage)",
           "note": "repo-R2 (semantic rename) and repo-R3 (derived-assert) remain W2 "
                   "items — NOT prerequisites of this readout gate",
           "verdict": "PASS" if (not orphans and frozen_clean and not uncommitted) else "FAIL"}
    (ART / "repo_r1_manifest.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


if __name__ == "__main__":
    r = run()
    print(f"repo-R1 {r['verdict']}  orphans {len(r['orphan_artifacts'])}  "
          f"uncommitted {len(r['uncommitted_artifacts'])}  "
          f"frozen_clean {r['frozen_results_unmodified']}")
    for o in r["orphan_artifacts"] + r["uncommitted_artifacts"]:
        print("  !", o)
