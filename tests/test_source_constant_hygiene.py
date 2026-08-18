"""R-018 회귀 게이트 — 소스 주석의 파생 상수가 config 와 갈라지지 않는가 (Stage 4).

WHY (감사 Session 3 C-008)
--------------------------
활성 소스 네 곳이 `a* = 44.4 m/s^2` 을 단언하고 있었다. 실제 값은 config 에서
계산하면 **39.33** 이다 -- 44.4 는 `net_radius = 2.0` 시절 값이고 rho 가 1.77 로
바뀐 뒤 고아가 됐다 (2*2.0/0.3^2 = 44.4 vs 2*1.77/0.3^2 = 39.33).

    shepherd/m4_env.py            regime_of docstring
    shepherd/obs_threat.py        모듈 docstring (부등식 예시 두 줄 포함)
    shepherd/scripts/train_m4.py  운용점 선택 근거
    shepherd/scripts/curve_sweep.py  "붕괴 50% 교차 = 24.06" (legacy 캠페인 값)

계산 경로는 전부 `a_star(cfg)` 를 쓰므로 **실행에는 영향이 없었다**. 그러나
docs/81 §1 항목 4 가 이것을 제출 전 처리 대상으로 이미 지목했고, 주석을 읽고
운용점을 고르는 사람에게는 근거가 된다.

★ 이 게이트가 막는 것은 "누가 값을 다시 하드코딩하는 것" 이다. 이력 서술
  (`44.4 는 rho=2.0 시절 값이다`) 은 허용한다 -- append-only 정정 규율과 같다.
  판별은 **단언형 패턴**(`a* = 44.4`, `a*=44.4`)만 잡는 것으로 한다.

torch-free.
"""
from __future__ import annotations

import io
import pathlib
import re

import pytest

from shepherd.m4_config import m4_config
from shepherd.scripts.curve_sweep import a_star

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCAN_ROOTS = ("shepherd",)

#: `a* = <값>` 형태의 **단언**. 이력 서술("44.4 는 ... 고아값") 은 안 걸린다.
_ASSERTION = re.compile(r"a\*\s*(?:=|는)\s*(?:2\s*[*rρ][^=]{0,24}=\s*)?"
                        r"\*{0,2}(\d+\.\d+)\*{0,2}")


def _expected_a_star() -> float:
    cfg = m4_config()
    return a_star(cfg["physics"]["net_radius"], cfg["physics"]["tau_deploy"])


def test_r018_scan_is_not_vacuous():
    """전제 -- 스캐너가 실제로 파일과 후보를 보고 있는가."""
    files = [p for base in SCAN_ROOTS for p in (ROOT / base).rglob("*.py")
             if "__pycache__" not in p.parts]
    assert len(files) > 50, f"스캔 대상이 {len(files)} 개뿐"
    hits = sum(len(_ASSERTION.findall(io.open(p, encoding="utf-8",
                                              errors="replace").read()))
               for p in files)
    assert hits > 0, "a* 단언 패턴을 한 건도 못 찾았다 -- 정규식이 죽었다"


def test_r018_asserted_a_star_matches_the_config():
    """★ 소스가 단언하는 `a*` 가 config 계산값과 일치한다.

    실행 경로는 언제나 `a_star(cfg)` 를 쓴다 -- 이 게이트는 **주석이 코드와
    다른 이야기를 하는 것**을 막는다.
    """
    want = _expected_a_star()
    bad = []
    for base in SCAN_ROOTS:
        for p in (ROOT / base).rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            src = io.open(p, encoding="utf-8", errors="replace").read()
            for m in _ASSERTION.finditer(src):
                got = float(m.group(1))
                if abs(got - want) > 0.01:
                    line = src[:m.start()].count("\n") + 1
                    bad.append(f"{p.relative_to(ROOT).as_posix()}:{line} "
                               f"a*={got} (config {want:.2f})")
    assert not bad, ("소스 주석의 a* 가 config 와 갈라졌다 (Session 3 C-008):\n  "
                     + "\n  ".join(bad))


def test_r018_curve_docstring_carries_the_current_crossing():
    """`curve_sweep` 모듈 docstring 의 50% 교차가 T1 canonical 값이다.

    옛 값 24.06 은 legacy 구계약 캠페인 산물이고, 그 자리에서 *"두 값이 6.6 %
    안에서 만난다 = 두 번째 경계의 **검증**"* 이라는 registry C031 **금지 문구**가
    함께 살아 있었다. 숫자와 주장 둘 다 정정한다.
    """
    from shepherd.scripts import curve_sweep
    doc = curve_sweep.__doc__ or ""
    assert "22.45" in doc, "T1 canonical 교차(22.45)가 docstring 에 없다"
    assert "12.4" in doc, "정정된 편차(12.4 %)가 병기되지 않았다"
    # C031 금지 문구가 **단언으로** 남아 있으면 안 된다 (금지 목록 인용은 허용)
    assert "두 번째 경계의 검증" not in doc.replace("두 번째 경계의 검증\" 은", ""), \
        "철회된 인과 주장이 docstring 에 단언으로 남아 있다 (registry C031)"


def test_r021_outcome_label_docstring_states_the_scope_difference():
    """`_outcome_label` 이 `mission_rollout` 과의 **범위 차이**를 밝힌다.

    종전 주석은 "같은 술어를 쓴다" 뿐이라 감사자가 결함으로 재유도했다
    (Session 3 C-017). divergence 는 비준된 것이고 test_row12 가 고정한다.
    """
    from shepherd.env_sys import ModeSystemEnv
    doc = ModeSystemEnv._outcome_label.__doc__ or ""
    assert "B1" in doc or "divergence" in doc, "비준된 divergence 언급이 없다"
    assert "test_row12" in doc, "고정 회귀 참조가 없다"


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
