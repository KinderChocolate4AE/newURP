"""R3 hygiene — 복제된 상수가 authoritative 정의원과 갈라졌는지 잡는다.

docs/81 §R3 의 원칙은 **assert first → deduplicate later** 다. 통합은 나중이고, 지금은
"조용히 갈라지는 것" 부터 막는다. 그래서 본 파일은 코드를 **바꾸지 않고** 대조만 한다.

docs/81 이 지목한 4 대상의 현재 상태 (2026-09-14 실측):

| 대상 | 상태 |
|---|---|
| `ρ·τ·R_NK` 복사 (`coarse_pilot`) | **실재하는 복사** → T1 이 대조 |
| `r_lat ↔ ring_radius` | **실재하는 복사** (같은 5.0 이 두 리터럴) → T3 이 대조 |
| standby R 2중 | **이미 해소** — `scale_v2.V3_STANDBY_R` 단일 정의원 (T4 가 고정) |
| ramp reachability 3중 구현 | **이미 잠김** — `test_union_equiv.py` · `test_batched_eval.py` (각 5 test) 가 세 경로의 수치 동일성을 강제한다. 여기서 중복 assert 를 만들지 않는다 |

가장 큰 노출은 `r2a_lattice._inject` 였다: **A2-nominal 스펙 전체와 물리 상수를 리터럴로
다시 적어 둔다**. 단위 스케일 (s = r = 1) 에서는 authoritative 값과 같아야 하므로 T2 가
그것을 직접 대조한다 — 여기가 갈라지면 R2a 격자의 무차원군이 조용히 어긋난다.

torch-free · 서버 불요.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shepherd.env_sys import SystemSpec                                # noqa: E402
from shepherd.m4_config import M4_OVERRIDES                            # noqa: E402
from shepherd.scripts import coarse_pilot as CP                        # noqa: E402
from shepherd.scripts import r2a_lattice as RL                         # noqa: E402


def test_t1_coarse_pilot_frozen_absolutes_match_authoritative():
    """`coarse_pilot` 이 "동결 절대값 (m4_config)" 이라 주석 달고 복사한 세 값."""
    assert CP.RHO == M4_OVERRIDES["physics.net_radius"], "RHO 가 net_radius 와 갈라졌다"
    assert CP.TAU == M4_OVERRIDES["physics.tau_deploy"], "TAU 가 tau_deploy 와 갈라졌다"
    assert CP.R_NK == SystemSpec().r_nk, "R_NK 가 SystemSpec.r_nk 와 갈라졌다"


def test_t2_lattice_unit_scale_matches_authoritative_spec():
    """`r2a_lattice._inject` 는 s = r = 1 에서 authoritative 값을 그대로 내야 한다.

    이 함수는 A2-nominal 행동 상수와 물리 상수를 **리터럴로 다시 적어 둔다**
    (docs/97 §A.2 가 봉인한 nominal 점). 갈라지면 R2a 격자의 무차원군이 조용히 어긋난다.
    """
    im = {"tau": RL.TAU_REF, "rho": RL.RHO_REF, "k_f": RL.K_F_REF,
          "R_max": RL.R_MAX_REF}
    inj = RL._inject(im)
    assert (inj["dt"], im["tau"] / RL.TAU_REF) == (RL.DT_REF, 1.0), "단위 스케일이 아니다"

    # 물리 — 정의원이 둘로 나뉘어 있다: M4_OVERRIDES 가 덮는 것 / params.py 기본값
    from shepherd.params import PARAMS
    assert inj["kill_radius"] == M4_OVERRIDES["physics.kill_radius"]
    assert inj["tau_lock"] == PARAMS["physics.tau_lock"].value
    assert inj["dt"] == PARAMS["physics.dt"].value

    # A2-nominal 행동 (docs/97 §A.2 봉인 점 — attacker_ladder 기본값이 정의원)
    from shepherd.agents.attacker_ladder import AttackerSpec
    d = AttackerSpec()
    assert inj["jink_freq"] == d.jink_freq, "jink_freq 가 AttackerSpec 기본값과 갈라졌다"
    assert inj["homing_gain"] == d.homing_gain
    assert inj["jink_terminal_r"] == d.jink_terminal_r
    # sense_range 는 nominal 30.0 (spec 기본은 inf — 캠페인이 명시 주입한다)
    assert inj["sense_range"] == 30.0


def test_t3_r_lat_and_ring_radius_share_one_factor():
    """docs/81 이 지목한 `r_lat ↔ ring_radius` — 같은 5.0 이 두 리터럴로 적혀 있다."""
    im = {"tau": RL.TAU_REF, "rho": RL.RHO_REF, "k_f": RL.K_F_REF,
          "R_max": RL.R_MAX_REF}
    inj = RL._inject(im)
    assert inj["spawn_r_lat"] == inj["ring_radius"], (
        "r_lat 과 ring_radius 가 갈라졌다 — 둘은 같은 5.0 을 따로 적어 둔 복사다")
    from shepherd.params import PARAMS
    assert inj["ring_radius"] == PARAMS["train.layout.ring_radius"].value


def test_t4_standby_r_is_single_sourced():
    """standby R 2중 은 이미 해소됐다 — 정의원이 하나뿐임을 고정한다."""
    import re
    src = (ROOT / "shepherd/scale_v2.py").read_text(encoding="utf-8")
    assert len(re.findall(r"^V3_STANDBY_R\s*=", src, re.M)) == 1
    from shepherd.scale_v2 import V3_STANDBY_R
    assert V3_STANDBY_R == (8.0, 16.0)


def test_t5_reachability_equivalence_is_covered_elsewhere():
    """ramp reachability 3중 구현 은 기존 동치 테스트가 잠근다 — 중복 assert 금지."""
    for f in ("test_union_equiv.py", "test_batched_eval.py"):
        p = ROOT / "tests" / f
        assert p.exists(), f"{f} 가 사라지면 R3 의 reachability 커버리지가 비는다"
        assert "def test" in p.read_text(encoding="utf-8")
