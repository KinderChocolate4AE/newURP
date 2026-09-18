"""KSAS 본문이 인용하는 속력 삼분위 수치의 드리프트 게이트.

원고가 0.878 / 0.776 / 0.636 을 사후 민감도로 인용하므로, 재집계 경로가
조용히 바뀌면 인쇄된 숫자가 근거를 잃는다. 동결 아티팩트 위의 재집계이니
값은 상수여야 한다.
"""
import pathlib

import pytest

from shepherd.scripts.eta_sensitivity import run

ROOT = pathlib.Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    not (ROOT / "results/curve_hold_reactive.json").exists(),
    reason="frozen T1 curve artifact not present")


@pytest.fixture(scope="module")
def res():
    return run(ROOT)


def test_easy_terciles_pinned(res):
    """헤드라인 인용값 (hold arm, EASY)."""
    got = [(r["net_capture"], r["n"]) for r in res["arms"]["hold"]["bands"]["EASY"]]
    assert got == [(172, 196), (152, 196), (126, 198)]


def test_terciles_are_not_confounded_by_a_att(res):
    """독립 추출이므로 삼분위 간 a_att 평균이 균형이어야 한다.

    이것이 깨지면 속력 효과 해석 자체가 교락된다 -- 게이트의 존재 이유.
    """
    means = [r["a_att_mean"] for r in res["arms"]["hold"]["bands"]["EASY"]]
    assert max(means) - min(means) < 1.0, means


def test_speed_effect_exceeds_sampling_noise(res):
    """양 끝 삼분위의 Wilson 95% 가 겹치지 않는다 (원고 주장의 근거)."""
    rows = res["arms"]["hold"]["bands"]["EASY"]
    assert rows[0]["wilson95"][0] > rows[-1]["wilson95"][1]


def test_total_is_the_frozen_campaign(res):
    for arm in ("hold", "intercept"):
        assert res["arms"][arm]["n"] == 2700
