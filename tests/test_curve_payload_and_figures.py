"""R-007 · R-008 회귀 게이트 — 아티팩트 자기서술 + 그림 사슬의 추적 (Stage 2).

R-007 (Session 2 X-004): `run_curve` 의 반환값 ≡ `--out` 저장본
-----------------------------------------------------------------
`_save` 의 payload 와 함수 말미의 return 이 따로 있었고, **반환 쪽에만**
`route_gain` / `sense_range` / `capture_terminates` 가 빠져 있었다. 그래서

    run_curve(...)                 계약을 모르는 요약 (반환)
    run_curve(..., out=path)       계약이 실린 아티팩트 (저장)

가 서로 다른 것을 뜻했다. 헤드라인 곡선 두 개가 계약 필드 없이 남은 사고
(`curve_hold_reactive.json` / `curve_intercept_reactive.json`) 이후 저장 쪽은
고쳐졌지만 반환 쪽은 blind 인 채였다.

★ 기존 `results/curve_*.json` 은 건드리지 않는다 -- persisted schema 는 이미
  맞고, 과거 아티팩트의 backfill 은 docs/81 §1-2 가 금지한다. sidecar 가 그
  역할을 한다.

R-008 (Session 2 X-010): 그림 사슬이 버전 관리 밖에 있었다
----------------------------------------------------------
`shepherd/scripts/paper_figs.py` 와 `figures/` 가 **둘 다 untracked** 였다.
`.gitignore` 에 해당 패턴이 없으므로 정책이 아니라 누락이었다 (`git check-ignore`
exit 1). 그런데 docs/84 는 논문 범위를 정확히 그 그림들로 동결했고, 그 스크립트는
발표 수치 10 개를 assert 하는 **유일한 anti-drift 장치**다. 클론하면 둘 다 없었다.

한쪽만 추적되는 상태는 실패로 본다 -- 생성기 없는 그림은 재현 불가이고,
그림 없는 생성기는 동결 대상이 사라진 것이다.

torch-free.
"""
from __future__ import annotations

import io
import json
import pathlib
import subprocess

import pytest

from shepherd.scripts.curve_sweep import run_curve

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: 계약을 정의하는 필드 -- 아티팩트가 자기 자신을 설명하려면 반드시 실려야 한다
CONTRACT_FIELDS = ("route_gain", "sense_range", "capture_terminates",
                   "baseline_commit", "mode", "seed0", "level", "jink_amp",
                   "w_kill")


# ------------------------------------------------------------------ R-007 ---
@pytest.fixture(scope="module")
def curve_run(tmp_path_factory):
    """작은 캠페인 한 번. 반환값과 저장본을 같이 들고 온다.

    ★ 기본값이 아닌 값을 명시적으로 넘긴다 -- 기본값과 우연히 같으면 "필드가
    실렸다" 와 "값이 전달됐다" 를 구분할 수 없다.
    """
    out = tmp_path_factory.mktemp("r007") / "curve.json"
    returned = run_curve(0, 2, mode="intercept", w_kill=0.5, level="A2",
                         jink=0.6, route_gain=0.5, sense_range=30.0,
                         capture_terminates=False, out=str(out))
    saved = json.loads(io.open(out, encoding="utf-8").read())
    return returned, saved


def test_r007_return_equals_persisted_payload(curve_run):
    """★ 본 게이트 — 같은 invocation 의 반환값과 저장본이 **완전히 동일**하다."""
    returned, saved = curve_run
    assert returned == saved, (
        "반환값과 저장본이 갈라졌다:\n"
        f"  반환에만: {sorted(set(returned) - set(saved))}\n"
        f"  저장에만: {sorted(set(saved) - set(returned))}\n"
        f"  값 불일치: {[k for k in set(returned) & set(saved) if returned[k] != saved[k]]}")


@pytest.mark.parametrize("field", CONTRACT_FIELDS)
def test_r007_contract_field_is_carried_by_both(curve_run, field):
    """계약 필드가 양쪽에 다 실린다. 하나라도 빠지면 아티팩트가 자기서술을 못 한다."""
    returned, saved = curve_run
    assert field in returned, f"반환값에 {field} 가 없다"
    assert field in saved, f"저장본에 {field} 가 없다"


def test_r007_values_are_the_passed_ones_not_defaults(curve_run):
    """★ 반-theatre — 넘긴 값이 실제로 실렸는가 (필드 존재 ≠ 값 전달)."""
    returned, _ = curve_run
    assert returned["route_gain"] == 0.5
    assert returned["sense_range"] == 30.0
    assert returned["capture_terminates"] is False      # 기본 True 와 다른 값
    assert returned["baseline_commit"] is True          # intercept 파생
    assert returned["mode"] == "intercept"


def test_r007_existing_canonical_artifacts_are_untouched():
    """기존 곡선 아티팩트는 이 카드가 건드리지 않는다 (backfill 금지)."""
    for name in ("curve_hold_reactive.json", "curve_intercept_reactive.json"):
        p = ROOT / "results" / name
        if not p.exists():                                  # pragma: no cover
            pytest.skip(f"{name} 없음")
        d = json.loads(io.open(p, encoding="utf-8").read())
        assert "route_gain" not in d, (
            f"{name} 에 route_gain 이 backfill 됐다 -- 과거 아티팩트는 그대로 두고 "
            "sidecar 로 보완하는 것이 규율이다 (docs/81 §1-2)")


# ------------------------------------------------------------------ R-008 ---
def _tracked(rel: str) -> bool:
    r = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--error-unmatch", rel],
                       capture_output=True, text=True)
    return r.returncode == 0


def test_r008_figure_generator_is_tracked():
    """생성기가 버전 관리 안에 있다 -- 클론에서 그림을 재현할 수 있어야 한다."""
    assert _tracked("shepherd/scripts/paper_figs.py"), \
        "paper_figs.py 가 untracked 다 (.gitignore 정책이 아니라 누락이었다)"


def test_r008_figures_are_tracked_with_their_generator():
    """★ 생성기와 산출물이 **함께** 추적된다. 한쪽만이면 실패다."""
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "figures/"],
                         capture_output=True, text=True).stdout.split()
    assert out, "figures/ 에 추적되는 파일이 없다"
    stems = {pathlib.Path(f).stem for f in out}
    assert {"f1_feasibility_modality", "f2_fire_decomposition"} <= stems, \
        f"docs/84 가 동결한 두 그림이 추적되지 않는다: {sorted(stems)}"
    assert _tracked("shepherd/scripts/paper_figs.py"), \
        "그림은 추적되는데 생성기가 없다 -- 재현 불가 상태"


def test_r008_generator_asserts_the_frozen_numbers():
    """생성기가 anti-drift 장치인지 확인한다 (그냥 그림만 그리면 의미가 다르다).

    실제 숫자 검증은 `paper_figs._check` 가 하고 Session 2 가 10/10 재현을
    확인했다. 여기서는 그 장치가 **존재하고 호출되는지**만 고정한다.
    """
    src = io.open(ROOT / "shepherd" / "scripts" / "paper_figs.py",
                  encoding="utf-8").read()
    assert "def _check(" in src, "_check 가 사라졌다"
    assert "_check(f1, f2)" in src, "_check 가 main 에서 호출되지 않는다"
    assert "summarize_curve" in src, \
        "집계를 curve_sweep 에서 가져오지 않는다 -- 표와 그림이 갈라질 수 있다"


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
