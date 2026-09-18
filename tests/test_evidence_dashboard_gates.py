"""Evidence dashboard 게이트 — 구현 전 RED 로 작성 (docs/85 §7 규율).

대상 = `viz/build_research_evidence_dashboard.py` (research **evidence** dashboard).
기존 `tests/test_dashboard_aggregation_parity.py` 는 results dashboard
(`viz/build_results_dashboard.py`) 용이라 **별개**다 — 이름을 분리한 이유.

무엇을 고정하나
---------------
1. drift check B — claim 의 `Experiment artifact` 셀 4 등급 분류
   (RESOLVED / NOT_FOUND / AMBIGUOUS / NONE). status 는 registry 에서 읽는다 —
   문서 기억으로 하드코딩하지 않는다 (C001·C009 는 DOWNGRADED 다).
2. CONFLICT 배지 — `docs/NN` 존재 대조는 **일반 검사**다. C029 특수 처리 금지.
3. canonical pointer — `results/README.md` 의 supersession 블록이 유일한
   artifact-등급 authority (CANONICAL / SUPERSEDED-FOR-MEASUREMENT / NO-OP /
   PROVENANCE-RETAINED).
4. lineage edge — registry `Superseded by` 열 + README 블록에서만 도출.
   **기대 집합을 정확히 고정**한다: 손으로 edge 를 추가하면 여기서 깨진다.
   그래프가 성긴 것이 현재 리포가 강제하는 관계의 전부다.
5. tracked 판정 — 주변 작업 트리 상태에 의존하지 않도록 임시 저장소로 격리
   (docs/85 §7 #6 재발 방지).
6. snapshot 은 `pivot_manifest.dirty_state()` 를 **호출 시점에** 소비한다
   (R-025 의미론을 재구현하지 않는다 — X-002/X-005 부류 재발 방지).
7. 같은 입력 · 같은 `now` 에서 build 는 bit-동일하다 (결정론 게이트).

torch-free. 커밋된 아티팩트/registry 를 입력으로 고정하고, 판별력이 필요한
곳은 합성 입력을 쓴다 (X-006 방식).
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEN = ROOT / "viz" / "build_research_evidence_dashboard.py"
REGISTRY = ROOT / "artifacts" / "audits" / "claim_registry.tsv"


def _load():
    spec = importlib.util.spec_from_file_location("_red_dash", GEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def m():
    assert GEN.exists(), f"{GEN} 이 없다 (RED 단계면 정상)"
    return _load()


@pytest.fixture(scope="module")
def rows(m):
    return m.load_registry(REGISTRY)


@pytest.fixture(scope="module")
def by_id(rows):
    return {r["CLAIM_ID"]: r for r in rows}


@pytest.fixture(scope="module")
def built(m):
    # 결정론 계약과 같은 고정 now — 전 테스트가 한 번의 build 를 공유한다.
    return m.build(ROOT, now="2026-08-19T00:00:00+09:00")


# ---------------------------------------------------- 1. drift check B 등급 ---
def test_registry_loads_all_rows(rows):
    ids = [r["CLAIM_ID"] for r in rows]
    assert len(ids) == len(set(ids)), "CLAIM_ID 중복"
    assert len(ids) >= 47, f"행 손실: {len(ids)} < 47 (Stage 4 §5.2 기준)"


def test_artifact_cell_grades_pin_known_cases(m, by_id):
    """확인된 사례를 그대로 고정한다. status 는 registry 값이다 — 기억이 아니라."""
    def grade(cid):
        return m.classify_artifact_cell(by_id[cid]["Experiment artifact"], ROOT)["grade"]

    assert grade("C001") == "NOT_FOUND"          # results/m4_roles/*
    assert grade("C004") == "NOT_FOUND"          # results/m4_roles/SL-BC*
    assert grade("C009") == "AMBIGUOUS"          # "oracle 출력(세션 기록)"
    assert grade("C029") == "NONE"               # "—"
    assert grade("C034") == "RESOLVED"           # e3_oracle_r4 + e3_oracle 둘 다 실재

    # ★ 정정 반영 확인: C001·C009 는 ACTIVE 가 아니다.
    assert by_id["C001"]["Status"].startswith("DOWNGRADED")
    assert by_id["C009"]["Status"].startswith("DOWNGRADED")
    assert by_id["C004"]["Status"].startswith("ACTIVE")


def test_artifact_cell_grades_are_not_theatre(m, rows):
    """반-theatre — 4 등급이 실제 registry 위에서 전부 발생해야 분류기가 산 것이다."""
    got = {m.classify_artifact_cell(r["Experiment artifact"], ROOT)["grade"]
           for r in rows}
    assert got == {"RESOLVED", "NOT_FOUND", "AMBIGUOUS", "NONE"}, got


def test_glob_and_docs_tokens_resolve(m):
    """판별 케이스: glob 토큰과 `docs/NN` 토큰은 존재로, 죽은 경로는 부재로."""
    ok = m.classify_artifact_cell("results/boxed_arm_audit*.json", ROOT)
    assert ok["grade"] == "RESOLVED"
    ok = m.classify_artifact_cell("커밋 대장 docs/58 §2", ROOT)   # C018 형태
    assert ok["grade"] == "RESOLVED"
    bad = m.classify_artifact_cell("results/no_such_dir/*.json", ROOT)
    assert bad["grade"] == "NOT_FOUND"


def test_self_reported_uncommitted_flag(m, by_id):
    """C021 · C024 는 미커밋을 자인한다 — 그 자인을 카드에 싣기 위한 필드."""
    for cid in ("C021", "C024"):
        c = m.classify_artifact_cell(by_id[cid]["Experiment artifact"], ROOT)
        assert c["self_reported_uncommitted"] is True, cid
    c = m.classify_artifact_cell(by_id["C034"]["Experiment artifact"], ROOT)
    assert c["self_reported_uncommitted"] is False


# ------------------------------------------------------ 2. CONFLICT 일반 검사 ---
def test_c029_stale_conflict_resolved_on_real_registry(m, rows):
    """2026-09-07 외부감사 M5: C029 의 'docs/63 미작성' 오기는 행 내 정정됐다.
    실제 registry 에서 이 CONFLICT 가 재발하면 안 된다 (검출기 자체의 판별력은
    아래 합성 행 테스트가 보증한다)."""
    conflicts = m.docs_reference_conflicts(rows, ROOT)
    assert not any(c["claim"] == "C029" and c["kind"] == "stale-미작성"
                   for c in conflicts), conflicts


def test_conflict_check_is_generic_not_c029_special_cased(m, tmp_path):
    """판별력 3방향 — 합성 행으로 검사한다 (C029 하드코딩이면 여기서 깨진다)."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "63_synthetic.md").write_text("x", encoding="utf-8")
    fake = [
        {"CLAIM_ID": "Z1", "Current wording": "동결 문서 docs/63 미작성"},
        {"CLAIM_ID": "Z2", "Current wording": "docs/999 에 근거"},
        {"CLAIM_ID": "Z3", "Current wording": "docs/63 §1 에 따라"},
    ]
    kinds = {(c["claim"], c["kind"]) for c in m.docs_reference_conflicts(fake, tmp_path)}
    assert ("Z1", "stale-미작성") in kinds          # 미작성 표기 vs 실재
    assert ("Z2", "referenced-missing") in kinds    # 참조 문서 부재
    assert not any(c == "Z3" for c, _ in kinds)     # 정상 참조는 무죄


# ------------------------------------------- 3. canonical pointer / 등급 ------
def test_readme_canonical_pointers_resolve(m):
    rm = m.parse_results_readme(ROOT)
    missing = [p for p, g in rm["grades"].items()
               if g == "CANONICAL" and not (ROOT / p).exists()]
    assert not missing, f"README 가 canonical 이라는데 파일이 없다: {missing}"
    assert len([p for p, g in rm["grades"].items() if g == "CANONICAL"]) >= 6


def test_readme_grades_pin_known_cases(m):
    g = m.parse_results_readme(ROOT)["grades"]
    assert g["results/e3_oracle_r4.json"] == "CANONICAL"
    assert g["results/e3_oracle.json"] == "SUPERSEDED-FOR-MEASUREMENT"
    assert g["results/lead_time_r4.json"] == "NO-OP"          # ★ _r4 함정
    assert g["results/lead_time_r4b.json"] == "CANONICAL"
    assert g["results/viz_traj_t1_hk.json"] == "PROVENANCE-RETAINED"
    assert g["viz/trajectory_viewer_t1_hk_r5.html"] == "CANONICAL"


# ---------------------------------------------------------- 4. lineage edge ---
#: 현재 리포가 강제하는 관계의 **전부** (README 6 블록 + registry C034 한 행).
#: 성기게 보이는 것이 정상이다. 여기 없는 edge 를 generator 가 만들면 RED —
#: hand-maintained edge 금지 규율의 집행 지점이다.
EXPECTED_EDGES = {
    ("results/e3_oracle.json", "results/e3_oracle_r4.json",
     "supersedes-for-measurement"),
    ("results/e4_stagger.json", "results/e4_stagger_r4.json",
     "supersedes-for-measurement"),
    ("results/e4b_matched.json", "results/e4b_matched_r4.json",
     "supersedes-for-measurement"),
    ("results/e4c_uniform.json", "results/e4c_uniform_r4.json",
     "supersedes-for-measurement"),
    ("results/lead_time_diag.json", "results/lead_time_r4b.json",
     "supersedes-for-measurement"),
    ("results/viz_traj_t1_hk.json", "results/viz_traj_t1_hk_r5.json",
     "provenance-retained"),
    ("viz/trajectory_viewer_t1_hk.html", "viz/trajectory_viewer_t1_hk_r5.html",
     "provenance-retained"),
    ("C034", "C039", "registry-superseded-by"),
}


def test_edges_derive_only_from_authority(m, rows):
    got = {tuple(e) for e in m.all_edges(ROOT, rows)}
    assert got == EXPECTED_EDGES, (
        f"\n  잉여: {got - EXPECTED_EDGES}\n  누락: {EXPECTED_EDGES - got}")


# --------------------------------------------------------- 5. tracked 판정 ----
def test_tracked_flag_discriminates_in_isolated_repo(m, tmp_path):
    """주변 트리 상태 오염 격리 (docs/85 §7 #6) — 임시 저장소에서 양방향 판별."""
    def git(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], check=True,
                       capture_output=True)
    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    git("add", "a.txt")
    git("commit", "-q", "-m", "x")
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    ts = m.tracked_set(tmp_path)
    assert "a.txt" in ts and "b.txt" not in ts


def test_tracked_flag_on_real_repo_smoke(m):
    assert "results/e1e.json" in m.tracked_set(ROOT)


# ----------------------------------------------- 6. snapshot = 정본 dirty 소비 ---
def test_snapshot_consumes_canonical_dirty_state(m, monkeypatch):
    """R-025 3분할을 재구현하지 않고 **정본을 호출 시점에** 소비하는지 —
    sentinel 로 knob 의 resolved value 를 검증한다."""
    import shepherd.scripts.pivot_manifest as pm
    sentinel = {"code_dirty": "SENTINEL", "tracked_dirty": False,
                "untracked_present": True}
    monkeypatch.setattr(pm, "dirty_state", lambda *a, **k: sentinel)
    s = m.snapshot(ROOT)
    assert s["dirty"] is sentinel, "dirty_state 가 정본 경유가 아니다 (재구현 의심)"
    assert set(sentinel) == {"code_dirty", "tracked_dirty", "untracked_present"}


# ------------------------------------------------------------- 7. 결정론 ------
def test_build_is_deterministic(m, built):
    html2, _, _ = m.build(ROOT, now="2026-08-19T00:00:00+09:00")
    assert built[0] == html2, "같은 HEAD · 같은 now 에서 출력이 다르다"


# --------------------------------------------------- 통합: model 내용 고정 ----
def test_active_claim_with_missing_artifact_warns(built):
    """drift check B 의 경보 — ACTIVE 인데 artifact 가 NOT_FOUND 면 warning."""
    _, _, warnings = built
    assert any("C004" in w for w in warnings), warnings


def test_open_questions_panel_pairs_h4_with_m4_roles(built):
    """H-4 (docs/85 §8 인용) 와 m4_roles NOT_FOUND 를 같은 패널에 병렬 노출."""
    _, model, _ = built
    joined = " ".join(item["text"] for item in model["open_questions"])
    assert "m4_pilot" in joined, "H-4 인용 누락"
    assert "m4_roles" in joined, "drift check B 계열 병기 누락"


def test_ksas_cards_carry_stale_badge_and_no_numbers(built):
    """KSAS 원고는 나열만 한다 — 'Stage 5 대기 · 숫자 stale' 배지, 수치 미판독."""
    _, model, _ = built
    ks = [c for c in model["docs_assets"] if "KSAS2026" in c["path"]]
    assert len(ks) >= 6, [c["path"] for c in ks]
    assert all(c["badge"] == "Stage 5 대기 · 숫자 stale" for c in ks)


def test_publication_rows_come_from_docs84_frozen_table(built):
    _, model, _ = built
    rows = model["publication"]
    assert len(rows) == 8, [r["verdict"] for r in rows]
    assert {r["verdict"] for r in rows} == {
        "넣음", "압축", "아주 짧게", "appendix 또는 삭제", "뺌"}


def test_html_smoke(built):
    html, _, _ = built
    for needle in ("C042", "e3_oracle_r4.json", "NOT FOUND", "CONFLICT",
                   "Stage 5 대기"):
        assert needle in html, f"HTML 에 {needle!r} 이 없다"


if __name__ == "__main__":                                   # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
