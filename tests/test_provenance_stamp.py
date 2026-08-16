"""R-025 회귀 게이트 — provenance stamp 의 dirty 3분할 계약 (Session 4 Stage 2).

WHY (감사 Session 2 X-002 / Session 4 H-2)
------------------------------------------
`results/` 의 stamped artifact **16/16 이 `code_dirty: true`** 였다. 예외가 없었다.
포렌식 결과 원인은 결함이 아니라 **구현**이었다:

    "code_dirty": bool(_git("status", "--porcelain"))

`--porcelain` 은 untracked 를 포함한다. 실행이 자기 출력(`results/*.json`, `*.log`)을
레포 안에 쓰는 순간 참이 된다 -- 모든 실행이 그렇게 한다. 즉 이 플래그는
"실행 코드가 commit 과 다른가" 와 "실행이 파일을 만들었나" 를 **구분할 수 없다**.

H-2 포렌식(각 artifact 의 `code_commit` -> 기록 커밋 사이 `shepherd/` diff):
    14/16  차이 0            -> dirty 는 출력 파일이었다
     2/16  자기 생성기 신규 생성 -> 실행 코드는 `added_in` 시점의 것

3분할 계약
----------
    code_dirty         실험 outcome 을 만드는 **실행 코드**가 stamped commit 과 다른가
    tracked_dirty      tracked snapshot 전체가 clean 했는가 (docs·tests 포함)
    untracked_present  실행 중 생성된 미추적 산출물이 있었는가

세 질문이 분리돼야 artifact 를 나중에 읽을 수 있다. `code_dirty` 하나로는
"결과 JSON 을 썼다" 와 "물리 코드를 고치고 돌렸다" 가 같은 값이 된다.

★ science-code scope 는 **감사로 확인**했다 (편의상 고른 것이 아니다)
--------------------------------------------------------------------
`stamp()` 를 부르는 생성기 21 개를 전부 import 해 `sys.modules` 를 훑은 결과,
리포 안에서 로드된 모듈 중 `shepherd/` 밖은 **0 개**였다 (2026-08-17 실측).
그래서 `SCIENCE_CODE_ROOTS = ("shepherd",)` 로 닫는다. 나중에 root 가 늘면
`test_r025_scope_is_closed_under_the_declared_roots` 가 먼저 깨진다.

tests/ 를 제외하는 이유
-----------------------
테스트는 regression contract 이지 science execution path 가 아니다. 테스트만
수정된 상태로 캠페인을 돌렸다면 그 결과를 "실행 코드가 dirty" 로 표시하는 것은
provenance 의미를 흐린다. `tracked_dirty` 에는 잡힌다.

★ 기존 16 개 artifact 는 backfill 하지 않는다 (docs/81 §1-2). 과거의
  `code_dirty=true` 는 **그때의 stamp 계약 아래에서 사실**이었다.

torch-free.
"""
from __future__ import annotations

import pytest

from shepherd.scripts.pivot_manifest import (SCIENCE_CODE_ROOTS, dirty_state,
                                             stamp)

#: (파일, 기대 code_dirty) — 정책을 미래에 슬쩍 못 바꾸도록 못 박는다
POLICY = (
    ("shepherd/env_sys.py", True),                  # science source
    ("shepherd/scripts/curve_sweep.py", True),      # science source (하위 경로)
    ("docs/83_prereg.md", False),                   # docs
    ("tests/test_curve_sweep.py", False),           # regression contract
    ("README.md", False),                           # 루트 파일
)

#: 임시 저장소 레이아웃 (POLICY 의 경로를 전부 포함)
LAYOUT = tuple(p for p, _ in POLICY)


@pytest.fixture(scope="module")
def repo(tmp_path_factory):
    """정책 검증용 **격리 저장소**.

    주변 작업 트리에 의존하면 개발 중에는 항상 깨지고 CI 에서는 우연히 통과한다
    (첫 초안이 정확히 그랬다). 여기서는 계약 자체만 본다.
    """
    import subprocess

    d = tmp_path_factory.mktemp("r025repo")

    def git(*a):
        return subprocess.run(["git", "-C", str(d), *a], capture_output=True,
                              text=True, check=True)

    git("init", "-q")
    git("config", "user.email", "r025@test")
    git("config", "user.name", "r025")
    for rel in LAYOUT:
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# seed\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "seed")
    return d


def test_r025_scope_is_closed_under_the_declared_roots():
    """★ scope 가 선언된 root 로 닫혀 있는지 -- 편의가 아니라 감사 결과여야 한다.

    `stamp()` 를 부르는 생성기 전부의 전이 의존이 `SCIENCE_CODE_ROOTS` 안에
    있는지 실제로 import 해서 확인한다. root 가 부족하면 scope 밖 파일을 고치고
    돌려도 `code_dirty=False` 가 나오는 **false-negative provenance** 가 된다.
    """
    import importlib
    import io
    import pathlib
    import sys

    root = pathlib.Path(__file__).resolve().parents[1]
    gens = []
    for base in ("shepherd", "viz", "scripts"):
        d = root / base
        if not d.exists():
            continue
        for p in d.rglob("*.py"):
            if "__pycache__" in p.parts or p.name == "pivot_manifest.py":
                continue
            try:
                src = io.open(p, encoding="utf-8").read()
            except Exception:                              # pragma: no cover
                continue
            if "stamp(" in src:
                gens.append(p.relative_to(root).as_posix())

    assert gens, "생성기 스캔이 비었다 -- 공허한 통과 방지"
    for rel in gens:
        assert rel.startswith(tuple(r + "/" for r in SCIENCE_CODE_ROOTS)), \
            f"선언된 scope 밖에 stamped-artifact 생성기가 있다: {rel}"
        importlib.import_module(rel[:-3].replace("/", "."))

    outside = set()
    for mod in list(sys.modules.values()):
        f = getattr(mod, "__file__", None)
        if not f:
            continue
        try:
            q = pathlib.Path(f).resolve()
        except Exception:                                  # pragma: no cover
            continue
        if root not in q.parents:
            continue                                       # 서드파티
        rel = q.relative_to(root).as_posix()
        if not rel.startswith(tuple(r + "/" for r in SCIENCE_CODE_ROOTS)):
            outside.add(rel)
    # tests/ 자신은 pytest 가 로드하므로 제외하고 본다
    outside = {r for r in outside if not r.startswith("tests/")}
    assert not outside, (
        f"생성기가 scope 밖 리포 코드를 import 한다 -- SCIENCE_CODE_ROOTS 확장 필요: "
        f"{sorted(outside)}")


# --------------------------------------------------- 3분할 계약 (4-way) ---
def _clean(repo):
    """수정을 되돌려 저장소를 seed 상태로 (파라미터 간 오염 차단)."""
    import subprocess
    subprocess.run(["git", "-C", str(repo), "checkout", "--", "."],
                   capture_output=True, check=True)
    for p in repo.rglob("out_*.json"):
        p.unlink()


def test_r025_baseline_is_clean(repo):
    """전제 — seed 커밋 직후에는 셋 다 False. 아니면 아래 케이스가 무의미하다."""
    _clean(repo)
    assert dirty_state(str(repo)) == {"code_dirty": False, "tracked_dirty": False,
                                      "untracked_present": False}


def test_r025_untracked_output_only_is_not_code_dirty(repo):
    """① 결과 파일만 새로 생성 -> code_dirty=F · tracked_dirty=F · untracked=T.

    ★ 이것이 16/16 `code_dirty: true` 의 진짜 원인이었다. 실행이 자기 출력을
    레포 안에 쓰는 것만으로 종전 플래그가 참이 됐다.
    """
    _clean(repo)
    (repo / "results").mkdir(exist_ok=True)
    (repo / "results" / "out_e3.json").write_text("{}", encoding="utf-8")
    try:
        st = dirty_state(str(repo))
        assert st["untracked_present"] is True
        assert st["tracked_dirty"] is False, "출력 생성이 tracked 변경으로 잡혔다"
        assert st["code_dirty"] is False, \
            "출력 파일 생성만으로 code_dirty 가 참이 됐다 — 종전 결함 재발"
    finally:
        _clean(repo)


@pytest.mark.parametrize("path,expect_code_dirty", POLICY)
def test_r025_policy_by_path(repo, path, expect_code_dirty):
    """②③④ 경로별 정책. **파일을 진짜로 더럽혀서** `git` 이 뭘 보고하는지 본다.

    문자열 규칙만 검사하면 구현이 아니라 표를 테스트하게 된다.
    """
    _clean(repo)
    target = repo / path
    assert target.exists(), f"fixture 레이아웃에 {path} 가 없다"
    try:
        with open(target, "a", encoding="utf-8") as f:
            f.write("# R-025 수정\n")
        st = dirty_state(str(repo))
        assert st["tracked_dirty"] is True, \
            f"{path} 를 수정했는데 tracked_dirty 가 False 다"
        assert st["code_dirty"] is expect_code_dirty, (
            f"{path}: code_dirty 기대 {expect_code_dirty} != 실제 {st['code_dirty']} "
            f"(SCIENCE_CODE_ROOTS={SCIENCE_CODE_ROOTS})")
    finally:
        _clean(repo)


def test_r025_scope_boundary_is_the_discriminator(repo):
    """★ scope 안/밖이 실제로 갈라지는가 (반-theatre).

    POLICY 가 전부 같은 답을 내면 표를 통과시켜도 아무것도 증명하지 않는다.
    """
    ins = [p for p, e in POLICY if e]
    outs = [p for p, e in POLICY if not e]
    assert ins and outs, "scope 안/밖 사례가 둘 다 있어야 판별이 성립한다"


# ------------------------------------ R-006: --out 기본값이 canonical 인가 ---
#: `--out` 기본값이 superseded 경로를 가리키던 생성기들 (Session 2 X-003)
CANONICAL_DEFAULT_GENERATORS = (
    "shepherd/scripts/e3_oracle.py",
    "shepherd/scripts/e4_stagger.py",
    "shepherd/scripts/e4b_matched.py",
    "shepherd/scripts/e4c_uniform_lead.py",
    "shepherd/scripts/lead_time_diag.py",
)


def _readme_canonicals():
    """`results/README.md` 가 canonical 로 선언한 경로 집합."""
    import pathlib
    import re
    p = pathlib.Path(__file__).resolve().parents[1] / "results" / "README.md"
    return set(re.findall(r"canonical:\s+(results/[\w.]+)",
                          p.read_text(encoding="utf-8")))


def test_r006_readme_declares_canonical_artifacts():
    """전제 — README 파싱이 실제로 뭔가를 찾았는가 (공허한 통과 방지)."""
    c = _readme_canonicals()
    assert len(c) >= 5, f"canonical 선언을 {len(c)} 개밖에 못 찾았다: {c}"


@pytest.mark.parametrize("path", CANONICAL_DEFAULT_GENERATORS)
def test_r006_out_default_is_canonical(path):
    """★ `--out` 기본값이 `results/README.md` 의 canonical 과 일치한다.

    종전에는 전부 **superseded** 이름을 가리켰다. 각 모듈의 docstring 이 보여주는
    실행 예시 그대로 돌리면 (a) provenance 보존 파일을 덮어쓰고 (b) canonical
    경로에는 아무것도 안 남았다 -- `results/README.md` 가 "삭제하지 않는다" 고
    선언한 규율과 코드가 정면으로 어긋나 있었다.

    두 곳을 문자열로 묶어 두면 한쪽만 바뀔 때 여기서 깨진다.
    """
    import io
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parents[1]
    src = io.open(root / path, encoding="utf-8").read()
    m = re.search(r'"--out",\s*default="(results/[\w.]+)"', src)
    assert m, f"{path}: --out 기본값을 찾지 못했다"
    default = m.group(1)
    assert default in _readme_canonicals(), (
        f"{path}: --out 기본값 {default} 이 README 의 canonical 목록에 없다 "
        f"(superseded 경로를 덮어쓸 위험)")
    # 모듈 docstring 의 실행 예시도 같은 곳을 가리켜야 한다
    assert default in src.split("\n\n", 1)[0] or f"--out {default}" in src, \
        f"{path}: docstring 실행 예시가 canonical 경로를 가리키지 않는다"


def test_r025_stamp_carries_the_three_fields():
    """stamp() 산물이 세 필드를 전부 싣는다 (빈 값이라도 키는 반드시)."""
    m = stamp(artifact="r025_selftest")
    for k in ("code_dirty", "tracked_dirty", "untracked_present"):
        assert k in m, f"stamp 에 {k} 가 없다"
        assert isinstance(m[k], bool)
    assert "code_commit" in m


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
