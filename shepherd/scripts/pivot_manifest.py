"""PIVOT LOCK manifest — 전환 시점의 감사 가능성 (리뷰 11 A1 이행).

    python -m shepherd.scripts.pivot_manifest --out artifacts/pivot_lock_2026-08-09.json
    git tag -a PIVOT_LOCK_2026-08-09 -m "..."      # manifest 커밋 뒤

왜: "오늘 이후 생성된 지도만 Phase III" 는 사람의 진술일 뿐이다. 제3자가 확인할 수
있게 (i) 전환 시점의 계약·코드·원자료의 SHA-256 을 한 파일에 모으고 (ii) 그 파일을
커밋·태그하고 (iii) 이후 모든 Phase III 산출물이 `protocol_hash` 를 싣게 한다.

★ 표현 규율 (리뷰 11 A1 넷째): 사람이 결과를 "안 봤다" 는 것은 암호학적으로 증명
불가하다. `unread_claim` 필드에 **과대주장하지 않는 문구**를 고정해 둔다.

torch-free.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess

__all__ = ["PROTOCOL_FILES", "PHASE_FILES", "sha256_of", "build_manifest", "stamp"]

# 전환 계약 본체 (이 파일들의 해시가 protocol_hash 를 만든다)
PROTOCOL_FILES = (
    "docs/73_review10_verdicts.md",
    "docs/74_pivot_protocol.md",
    "docs/75_blueprint.md",
    "docs/review_prompt_design_map_pivot.md",
    "docs/review_prompt_blueprint.md",
)

# Phase I 계약·원자료 + Phase II exploratory 산출물 + 진행 중 블록의 계약·코드
PHASE_FILES = (
    # Phase I 계약
    "docs/63_scripted_baseline_prereg.md",
    "docs/69_train_final_freeze.md",
    "docs/71_ls_commit_ablation_prereg.md",
    "docs/72_iid_eval_protocol.md",
    "configs/l2_mappo.yaml",
    "configs/l2_mappo_nocommit.yaml",
    # judge / env / 평가·판정 코드
    "shepherd/game/viability.py",
    "shepherd/env.py",
    "shepherd/env_sys.py",
    "shepherd/m4_env.py",
    "shepherd/m4_config.py",
    "shepherd/scale_v2.py",
    "shepherd/scripts/train_m4.py",
    "shepherd/scripts/eval_iid.py",
    "shepherd/scripts/analyze_ls_commit.py",
    # Phase II exploratory
    "shepherd/scripts/shaping_ceiling.py",
    "results/shaping_ceiling.json",
    "results/shaping_ceiling.png",
    # Phase I 결과 기록 (있는 것만)
    "temp_research_note/2026-08-08_ll_zero.md",
    "temp_research_note/2026-08-08_ready_for_marl.md",
    "temp_research_note/2026-08-09_ls_off_wired.md",
)

UNREAD_CLAIM = (
    "Results of the in-flight preregistered ablation had not been inspected for "
    "scientific decision-making as of this lock. No stronger claim (e.g. "
    "'verified unread') is made -- that is not cryptographically provable."
)


def sha256_of(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True).strip()
    except Exception:                                        # pragma: no cover
        return "unknown"


def _hashes(names) -> dict:
    out = {}
    for n in names:
        p = pathlib.Path(n)
        out[n] = sha256_of(p) if p.exists() else None
    return out


def build_manifest(*, in_flight: dict | None = None) -> dict:
    protocol = _hashes(PROTOCOL_FILES)
    # protocol_hash = 계약 파일 해시들의 해시 (이후 산출물이 이 값을 싣는다)
    protocol_hash = hashlib.sha256(
        json.dumps(protocol, sort_keys=True).encode()).hexdigest()[:16]
    return {
        "schema": "pivot-lock-v1",
        "lock_name": "PIVOT_LOCK_2026-08-09",
        "protocol_hash": protocol_hash,
        "code_commit": _git("rev-parse", "HEAD"),
        "code_dirty": bool(_git("status", "--porcelain")),
        "protocol_files": protocol,
        "phase_files": _hashes(PHASE_FILES),
        "in_flight": in_flight or {
            "block": "docs/71 r1 LS-COMMIT ABLATION",
            "runs": ["LS-live seeds 1..4 (results/m4_v3_train_LS)",
                     "LS-off seeds 0..4 (results/m4_v3_train_LS_off)"],
            "launcher": ("CUBLAS_WORKSPACE_CONFIG=:4096:8 python -m "
                         "shepherd.scripts.train_m4 [--config configs/"
                         "l2_mappo_nocommit.yaml] --threat-layer train "
                         "--seeds ... --finisher-policy scripted --device cuda "
                         "--output results/m4_v3_train_LS[_off]"),
            "primary": ("ablation IID 10300..10599 paired Delta p_net in the "
                        "pre-treatment SHAPING label; confirmatory training "
                        "seeds {1,2,3,4}; two-sided 95% bootstrap CI lower > 0"),
            "distribution_hash": "efeffcbf2e24d807",
            "train_contract_hash": "e275ca1cea074bc8",
        },
        "unread_claim": UNREAD_CLAIM,
        "stamp_required_on_phase3_artifacts": [
            "protocol_hash", "code_commit", "judge_commit",
            "scenario_manifest_hash", "map_spec_hash", "generated_at"],
        "note": ("Phase II artifacts are exploratory records only and are not "
                 "used for Phase III confirmatory classification or hypothesis "
                 "testing (docs/74)."),
    }


# ── Phase III 산출물 스탬프 (docs/74 §0-4) ──────────────────────────────────
JUDGE_FILES = ("shepherd/game/viability.py", "shepherd/env.py", "shepherd/env_sys.py")


def stamp(**extra) -> dict:
    """모든 Phase III artifact 가 실어야 하는 provenance 스탬프.

    docs/74 §0-4: `protocol_hash · code_commit · judge_commit ·
    scenario_manifest_hash · map_spec_hash · lattice_hash · generated_at`.
    아직 존재하지 않는 항목(map_spec/lattice)은 None 으로 남기고 호출자가 채운다 --
    **스탬프 없는 artifact 는 무효**이므로 빈 값이라도 키는 반드시 실린다.
    """
    import datetime

    lock = pathlib.Path("artifacts/pivot_lock_2026-08-09.json")
    protocol_hash = None
    if lock.exists():
        protocol_hash = json.loads(lock.read_text(encoding="utf-8")).get("protocol_hash")
    judge = hashlib.sha256()
    for f in JUDGE_FILES:
        fp = pathlib.Path(f)
        if fp.exists():
            judge.update(fp.read_bytes())
    out = {
        "protocol_hash": protocol_hash,
        "code_commit": _git("rev-parse", "HEAD"),
        "code_dirty": bool(_git("status", "--porcelain")),
        "judge_commit": judge.hexdigest()[:16],
        "scenario_manifest_hash": None,
        "map_spec_hash": None,
        "lattice_hash": None,
        "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    out.update(extra)
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="PIVOT LOCK manifest 생성")
    ap.add_argument("--out", default="artifacts/pivot_lock_2026-08-09.json")
    a = ap.parse_args(argv)
    m = build_manifest()
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(m, indent=1, ensure_ascii=False), encoding="utf-8")
    missing = [k for k, v in {**m["protocol_files"], **m["phase_files"]}.items()
               if v is None]
    print(f"protocol_hash = {m['protocol_hash']}  commit = {m['code_commit'][:12]}"
          f"  dirty = {m['code_dirty']}")
    if missing:
        print("[경고] 없는 파일 (해시 null):")
        for k in missing:
            print("   ", k)
    print(f"-> {p}")


if __name__ == "__main__":
    main()
