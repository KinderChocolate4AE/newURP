"""R-014 회귀 게이트 — 뷰어가 **권위 근접거리**를 싣는가 (Stage 3).

WHY (감사 Session 2 X-007 · Session 3 §I)
-----------------------------------------
`dump_trajectory` 는 스텝마다 `d_lim_min` 을 실었다. 그 값은

    min over lim_pos of  |p_att_post - q|          (q = **화면 보정 좌표**)

즉 (a) post-step **끝점** 거리이고 (b) 은퇴한 limiter 는 마지막 실좌표에 고정된
표시용 좌표를 쓴다. 이는 R4 가 superseded 로 선언한 계열의 측정이다 -- 해소기가
쓰는 swept `_seg_min_dist` 도, R4 권위값 `_Driver.d_min` 도 아니다. 그런데 뷰어는
그것을 *"최근접 limiter (m)"* 로, `<= r_contact` 면 *"(접촉권)"* 까지 붙여 보여줬다.
권위값은 같은 driver 위에 있으면서 덤프되지 않았다.

이 파일이 중요한 이유: `results/viz_traj_t1_hk.json` 은 **claim registry C033 의
증거 아티팩트**다. C033 이 실제로 인용하는 필드(`commits[].source`, `d_nom`)는
해소기 산물이라 영향이 없지만, 같은 파일을 열어 본 사람은 권위값이 아닌 수를
"최근접" 으로 읽게 된다.

★ 아티팩트 정책: 기존 덤프는 덮지 않는다. 새 이름으로만 만든다 (docs/81 §1-2).

torch-free.
"""
from __future__ import annotations

import numpy as np
import pytest

from shepherd.env_sys import _seg_min_dist
from shepherd.scripts.dump_trajectory import dump_episode

#: 접촉이 실제로 나는 하드킬 판 (C033 증거와 같은 세계 · 같은 에피소드)
HK_EPISODES = (3, 9, 12)


@pytest.fixture(scope="module")
def dumps():
    return {ep: dump_episode(ep, t1=True, limiter_mode="intercept", commit=True)
            for ep in HK_EPISODES}


def test_r014_display_field_is_renamed(dumps):
    """표시용 양이 이름으로 자기 성격을 밝힌다 -- 권위값으로 오독되지 않게."""
    for ep, d in dumps.items():
        s0 = d["steps"][0]
        assert "d_lim_min_display" in s0, f"ep{ep}: 표시 필드가 개명되지 않았다"
        assert "d_lim_min" not in s0, \
            f"ep{ep}: 옛 이름이 남아 있다 (뷰어가 권위값으로 읽는다)"


def test_r014_authoritative_proximity_is_dumped(dumps):
    """★ `_Driver.d_min` (R4 권위) 이 에피소드·스텝 양쪽에 실린다."""
    for ep, d in dumps.items():
        prox = d.get("proximity")
        assert prox, f"ep{ep}: proximity 블록이 없다"
        assert prox["contract"].startswith("R4"), prox["contract"]
        assert len(prox["d_min"]) == len(d["steps"][0]["lims"]), \
            f"ep{ep}: d_min 길이가 limiter 수와 다르다"
        assert any(s.get("d_swept_min") is not None for s in d["steps"]), \
            f"ep{ep}: 스텝별 권위 누적값이 하나도 없다"


def test_r014_authority_agrees_with_the_resolver(dumps):
    """★ 본 게이트 — 접촉 record 가 있으면 권위값이 그 사건을 가리킨다.

    `test_r4b_contact_records_match_authoritative` 와 같은 불변식을 **덤프 산물
    위에서** 다시 건다: 접촉한 limiter 의 `d_min` 은 `r_contact` 이하이고
    해소기가 기록한 `d_nom` 을 넘지 않는다.
    """
    checked = 0
    for ep, d in dumps.items():
        r_contact = float(d["static"]["r_contact"])
        dmin = d["proximity"]["d_min"]
        for c in d["commits"]:
            if c["source"] != "contact":
                continue
            i = c["limiter"]
            assert dmin[i] is not None, f"ep{ep} limiter{i}: 권위값이 없다"
            assert dmin[i] <= r_contact + 1e-9, (
                f"ep{ep} limiter{i}: 접촉했는데 d_min {dmin[i]} > r_contact {r_contact}")
            # * 허용오차 근거 (느슨하게 한 것이 아니다): 두 필드는
            #   아티팩트에서 **서로 다른 자릿수로 반올림**된다 --
            #   commits[].d_nom 은 3 자리, proximity.d_min 은 4 자리
            #   (0.709 vs 0.7094). exact 비교는 수학적으로 성립하지
            #   않으므로 3 자리 반올림의 half-ulp 를 허용한다.
            assert dmin[i] <= c["d_nom"] + 5e-4, (
                "ep%s limiter%s: d_min %s > 해소기 d_nom %s "
                "(반올림 허용오차 밖)" % (ep, i, dmin[i], c["d_nom"]))
            checked += 1
    assert checked >= 3, f"접촉 record 를 {checked} 건밖에 못 봐 게이트가 약하다"


def test_r014_display_value_can_disagree_with_the_authority(dumps):
    """★ 반-theatre — 두 양이 **실제로 다를 수 있음**을 고정한다.

    항상 같다면 개명도 권위값 추가도 의미가 없다. 은퇴가 일어난 판에서 표시값이
    권위 누적값보다 커지는 지점이 있어야 한다 (주차 보정 좌표가 계속 움직이므로).
    """
    seen = False
    for d in dumps.values():
        for s in d["steps"]:
            a, b = s.get("d_swept_min"), s["d_lim_min_display"]
            if a is not None and abs(a - b) > 1e-6:
                seen = True
                break
    assert seen, ("표시값과 권위값이 어디서도 다르지 않다 -- 두 필드를 나눌 근거가 "
                  "이 fixture 에서는 관측되지 않았다")


def test_r014_existing_evidence_artifact_is_untouched():
    """C033 증거 아티팩트는 이 카드가 덮지 않는다 (docs/81 §1-2)."""
    import io
    import json
    import pathlib
    p = pathlib.Path(__file__).resolve().parents[1] / "results" / "viz_traj_t1_hk.json"
    if not p.exists():                                        # pragma: no cover
        pytest.skip("증거 아티팩트 없음")
    d = json.loads(io.open(p, encoding="utf-8").read())
    eps = d["episodes"]      # {"note": ..., "episodes": [...]} 구조
    assert eps and "steps" in eps[0], (
        "증거 아티팩트 구조가 예상과 다르다")
    assert "d_lim_min" in eps[0]["steps"][0], (
        "기존 증거 아티팩트가 새 스키마로 덮였다 -- provenance 위반")
    assert "proximity" not in eps[0], (
        "기존 증거 아티팩트에 새 블록이 주입됐다 -- backfill 금지")


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
