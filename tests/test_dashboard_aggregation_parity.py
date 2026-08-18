"""R-012 · R-013 회귀 게이트 — dashboard 집계가 정본과 갈라지지 않는가 (Stage 3).

WHY (감사 Session 2 X-005 · X-006)
----------------------------------
`viz/build_results_dashboard.py` 는 docstring 에 *"분석 로직을 새로 만들지 않는다"*
라고 적어 두고 실제로는 Wilson · bin 격자 · 경계 상수를 전부 다시 구현했다.

  X-005  네 번째 Wilson 구현. z 가 다르다
         shepherd/stats.py     Z_TWO_SIDED_95 = 1.959964
         build_results_dashboard  z = 1.959963984540054      (차 ~5e-10)
         ★ `test_p44j_wilson_has_exactly_one_definition` 이 바로 이 재발을 막으려고
           있는데, `sweep_m4` 와 `curve_sweep` 만 보고 `viz/` 는 못 본다.
           2026-08-03 에 한 번 겪은 사고가 게이트 사각지대에서 되살아났다.

  X-006  최상단 bin 경계 누락.
         curve_sweep  a <= r < b  or  (b == edges[-1] and r == b)
         dashboard    lo <= a < hi                      (top-edge 절 없음)
         `a_att == 78.0` 인 판이 정본에서는 마지막 칸에 들어가고 dashboard 에서는
         **조용히 사라진다**. 현 아티팩트에는 그런 판이 없어 잠복 상태였다.

★ 격리 원칙 (Stage 1-2 교훈)
---------------------------
이 파일의 비교는 **커밋된 아티팩트를 입력으로 고정**한다. 프로세스 상태나 작업
트리 상태에 의존하지 않는다 -- 그 부류로 이번 세션에 세 번 걸렸다.

torch-free.
"""
from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import re

import pytest

from shepherd.scripts.curve_sweep import summarize_curve
from shepherd.stats import Z_TWO_SIDED_95

ROOT = pathlib.Path(__file__).resolve().parents[1]
DASH = ROOT / "viz" / "build_results_dashboard.py"
ARTIFACT = ROOT / "results" / "curve_intercept_reactive.json"

#: 정본이 포획으로 세는 라벨 (curve_sweep._CAPTURE 와 같은 집합)
CAPTURE = ("NET_CAPTURE", "CAPTURE_WITH_CONTACT")


def _dashboard():
    spec = importlib.util.spec_from_file_location("_dash", DASH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def dash():
    return _dashboard()


@pytest.fixture(scope="module")
def records():
    assert ARTIFACT.exists(), f"{ARTIFACT.name} 이 없어 비교 불가"
    return json.loads(io.open(ARTIFACT, encoding="utf-8").read())["records"]


# ------------------------------------------------------- R-012 정의 단일화 ---
def test_r012_no_second_wilson_z_constant_in_active_code():
    """★ 활성 코드에 `Z_TWO_SIDED_95` 아닌 z 리터럴을 쓰는 Wilson 이 없다.

    `test_p44j` 를 **경로 스캔으로 확장**한 것이다 -- 그 테스트는 두 모듈을
    이름으로만 확인해서 `viz/` 를 못 봤다.

    범위는 활성 표면(`shepherd/`, `viz/`)이다. `docs/ppt/` 는 Session 1 이
    AMBIGUOUS 로 분류한 레거시 발표 스크립트라 제외한다 -- 거기 사본은 주석에
    스스로 사본임을 밝히고 있고, 활성 결과 경로에 닿지 않는다.
    """
    offenders = []
    for base in ("shepherd", "viz"):
        for p in (ROOT / base).rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            src = io.open(p, encoding="utf-8", errors="replace").read()
            for m in re.finditer(r"def\s+wilson\s*\([^)]*?z\s*=\s*([0-9.]+)", src,
                                 re.S):
                if float(m.group(1)) != Z_TWO_SIDED_95:
                    offenders.append(f"{p.relative_to(ROOT).as_posix()}: z={m.group(1)}")
    assert not offenders, (
        "Wilson 이 다른 z 로 재구현돼 있다 (2026-08-03 사고 재발): " + str(offenders))


def test_r012_dashboard_consumes_the_canonical_wilson(dash):
    """dashboard 의 `wilson` 이 정본과 **같은 객체**이거나 같은 값을 낸다."""
    from shepherd.stats import wilson as canonical
    for n in (1, 5, 182, 292, 512, 1598):
        for k in (0, 1, n // 2, n):
            assert dash.wilson(k, n) == canonical(k, n), \
                f"wilson({k},{n}) 이 정본과 다르다"


# ------------------------------------------------- R-012+R-013 집계 동등성 ---
def test_r013_bin_edges_come_from_the_canonical_grid(dash):
    """격자가 정본 `bin_edges` 와 정확히 같다 (경계가 격자선 위에 있어야 한다)."""
    from shepherd.m4_config import THREAT_BRACKET, m4_config
    from shepherd.scripts.curve_sweep import a_star, bin_edges
    cfg = m4_config()
    lo, hi = THREAT_BRACKET["physics.a_att_max"]
    want = bin_edges(float(lo), float(hi),
                     a_star(cfg["physics"]["net_radius"],
                            cfg["physics"]["tau_deploy"]))
    assert list(dash.EDGES) == want, f"격자 불일치\n  dash {dash.EDGES}\n  정본 {want}"


def test_r012_aggregation_matches_the_module_exactly(dash, records):
    """★ 본 게이트 — 같은 아티팩트에서 bin 별 n · k · Wilson 이 **정확히** 같다."""
    got = dash.curve(records, lambda r: r["label"] in CAPTURE)
    want = summarize_curve({"mode": "intercept", "records": records})["bins"]
    assert len(got) == len(want), f"칸 수 {len(got)} != {len(want)}"
    bad = []
    for g, w in zip(got, want):
        c = w["net_capture"]
        if (g["lo"], g["n"], g["k"]) != (w["lo"], w["n"], c["k"]):
            bad.append(f"  [{w['lo']:.2f}) n {g['n']}/{w['n']} k {g['k']}/{c['k']}")
        elif (g["wl"], g["wh"]) != (c["lo"], c["hi"]):
            bad.append(f"  [{w['lo']:.2f}) Wilson {g['wl']},{g['wh']} != "
                       f"{c['lo']},{c['hi']}  (차 {g['wl'] - c['lo']:+.3e})")
    assert not bad, "dashboard 집계가 정본과 갈라졌다:\n" + "\n".join(bad)


def test_r013_top_edge_episode_is_not_dropped(dash):
    """★ `a_att` 가 상단 경계와 정확히 같은 판이 사라지지 않는다 (X-006 잠복 결함).

    현 아티팩트에는 그런 판이 없어 자연 관측이 불가능하다 -- 합성 판으로 만든다.
    """
    hi = float(dash.EDGES[-1])
    rec = [{"episode": 0, "label": "NET_CAPTURE", "regime": "SHAPING_NEEDED",
            "a_att": hi, "att_speed": 20.0, "net_radius": 1.77, "tau": 0.3}]
    got = dash.curve(rec, lambda r: r["label"] in CAPTURE)
    want = summarize_curve({"mode": "hold", "records": rec})["bins"]
    assert sum(b["n"] for b in got) == 1, \
        f"a_att={hi} 인 판이 dashboard 집계에서 사라졌다 (정본은 유지)"
    assert sum(b["n"] for b in want) == 1, "정본 쪽 전제가 깨졌다"


def test_r012_comparison_is_not_vacuous(dash, records):
    """반-theatre — 비교가 실제로 여러 칸·표본을 지나갔는가."""
    got = dash.curve(records, lambda r: r["label"] in CAPTURE)
    assert len(got) >= 6, f"칸이 {len(got)} 개뿐이면 비교가 약하다"
    assert sum(b["n"] for b in got) == len(records), "표본 일부가 누락됐다"
    assert any(b["k"] > 0 for b in got), "포획이 0 이면 Wilson 비교가 퇴화한다"


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
