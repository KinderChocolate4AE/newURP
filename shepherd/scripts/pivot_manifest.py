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

__all__ = ["PROTOCOL_FILES", "PHASE_FILES", "sha256_of", "build_manifest", "stamp",
           "SCIENCE_CODE_ROOTS", "dirty_state"]

#: ★ 실험 outcome 을 만드는 실행 코드의 root (R-025).
#:
#: "편의상 shepherd 만" 이 아니라 **감사로 확인한 scope** 다 -- `stamp()` 를 부르는
#: 생성기 21 개를 전부 import 해 `sys.modules` 를 훑었을 때 리포 안에서 로드된
#: 모듈 중 이 root 밖은 0 개였다 (2026-08-17). scope 가 넓어지면
#: `tests/test_provenance_stamp.py::test_r025_scope_is_closed_under_the_declared_roots`
#: 가 먼저 깨진다.
#:
#: `tests/` 는 **제외한다**: regression contract 이지 science execution path 가
#: 아니다. 테스트만 고친 상태로 캠페인을 돌린 결과를 "실행 코드가 dirty" 로 표시하면
#: provenance 의미가 흐려진다. 그 변경은 `tracked_dirty` 가 잡는다.
SCIENCE_CODE_ROOTS = ("shepherd",)

# 전환 계약 본체 (이 파일들의 해시가 protocol_hash 를 만든다)
PROTOCOL_FILES = (
    "docs/73_review10_verdicts.md",
    "docs/74_pivot_protocol.md",
    "docs/75_blueprint.md",
    "docs/78_gate10_isopi_prereg.md",
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
    # 협력 채널 분해 실측 (r3.3 — docs/74 §3.0 채널 대장이 인용하는 자료)
    "docs/46_channel_split.md",
    "shepherd/scripts/channel_split.py",
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


def dirty_state(repo: str | None = None) -> dict:
    """작업 트리 상태를 **세 질문으로 분리**해 보고한다 (R-025).

        code_dirty         결과를 만든 실행 코드가 stamped commit 과 다른가
        tracked_dirty      tracked snapshot 전체가 clean 했는가 (docs·tests 포함)
        untracked_present  실행 중 생성된 미추적 산출물이 있었는가

    WHY 셋으로 쪼개는가 (감사 Session 2 X-002)
    ------------------------------------------
    종전 구현은 `bool(_git("status", "--porcelain"))` 하나였다. `--porcelain` 은
    untracked 를 포함하므로 **실행이 자기 출력을 레포 안에 쓰는 순간 참**이 된다 --
    모든 실행이 그렇게 한다. 실제로 `results/` 의 stamped artifact 16/16 이
    `code_dirty: true` 였고, 포렌식 결과 14/16 은 `code_commit` 과 기록 커밋 사이
    `shepherd/` diff 가 0 이었다. 즉 플래그가 "코드를 고쳤다" 와 "파일을 만들었다" 를
    구분하지 못해 provenance 신호로서 거의 무의미했다.

    셋을 **독립 명령**으로 계산한다 (한 결과를 재파싱해 나누지 않는다) -- 의미가
    섞이지 않게 하기 위해서다.

    ★ 과거 artifact 는 backfill 하지 않는다. 그때의 `code_dirty=true` 는 그때의
      계약 아래에서 사실이었다 (docs/81 §1-2 historical preservation).

    `repo` 는 테스트용이다 -- provenance 함수가 **주변 작업 트리 상태에 의존해서만**
    검증 가능하면 개발 중에는 항상 깨지고 CI 에서는 우연히 통과한다. 임시 저장소를
    가리켜 정책 자체를 격리 검증할 수 있게 둔다 (기본 None = 현재 리포).
    """
    pre = ("-C", repo) if repo else ()
    tracked = _git(*pre, "status", "--porcelain", "--untracked-files=no")
    code = _git(*pre, "status", "--porcelain", "--untracked-files=no", "--",
                *SCIENCE_CODE_ROOTS)
    untracked = _git(*pre, "ls-files", "--others", "--exclude-standard")
    return {
        "code_dirty": bool(code) and code != "unknown",
        "tracked_dirty": bool(tracked) and tracked != "unknown",
        "untracked_present": bool(untracked) and untracked != "unknown",
    }


def _hashes(names) -> dict:
    out = {}
    for n in names:
        p = pathlib.Path(n)
        out[n] = sha256_of(p) if p.exists() else None
    return out


# ── revision 메타 (docs/74 §0-1 이 manifest 에 요구하는 필드) ────────────────
# ★ 이전 판은 이 넷을 JSON 에 손으로 넣어 두었다 -- 스크립트가 emit 하지 않았으므로
#   재실행하면 **조용히 소실**된다 (docs/73 §1.5 항목 6). 코드가 생성하게 옮긴다.
#   판을 올릴 때 REVISION/SUPERSEDES 만 바꾼다. 태그는 **절대 이동시키지 않는다**.
REVISION = "r3.4"
LOCK_DATE = "2026-08-11"
SUPERSEDES = "r3.3 (PIVOT_LOCK_R33_2026-08-09, protocol_hash e69dab93fb712694)"
TAG_POLICY = ("Tags are never moved. Each revision gets its own tag name "
              "(PIVOT_LOCK_R32_..., PIVOT_LOCK_R33_..., ...). docs/74 §0-2.")
PHASE3_CELLS_GENERATED_SO_FAR = 0


def build_manifest(*, in_flight: dict | None = None) -> dict:
    protocol = _hashes(PROTOCOL_FILES)
    # protocol_hash = 계약 파일 해시들의 해시 (이후 산출물이 이 값을 싣는다)
    protocol_hash = hashlib.sha256(
        json.dumps(protocol, sort_keys=True).encode()).hexdigest()[:16]
    return {
        "schema": "pivot-lock-v1",
        "lock_name": f"PIVOT_LOCK_{REVISION.upper().replace('.', '')}_{LOCK_DATE}",
        "revision": REVISION,
        "supersedes": SUPERSEDES,
        "tag_policy": TAG_POLICY,
        "phase3_cells_generated_so_far": PHASE3_CELLS_GENERATED_SO_FAR,
        "protocol_hash": protocol_hash,
        "code_commit": _git("rev-parse", "HEAD"),
        **dirty_state(),                       # R-025: code / tracked / untracked 분리
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
        **dirty_state(),                       # R-025: code / tracked / untracked 분리
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
