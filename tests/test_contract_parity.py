"""docs/65 A4a — resolved-contract manifest + 현행 runner parity.

운영 규율 (docs/65 §9): `train`·`eval`·`sweep`·`scripted` 는 코드 entrypoint 가
아니라 **동일한 resolved world contract 를 공유할 때만** 같은 실험 family 다.
여기서 그 규율을 실행 코드로 잠근다 -- manifest 는 호출자의 의도가 아니라
`build_m4_env` 가 실제로 받은 것에서 뽑히므로, 전달 누락(silent legacy
fallback)이 곧 mismatch 로 드러난다.

torch-free 경로(eval/sweep/curve/factorial/bc)는 직접, train_m4(torch)는
importorskip 로 서버에서만 확인한다.
"""
import pytest

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import RewardSpec, SystemSpec, ratified_system
from shepherd.m4_env import (CONTRACT_SCHEMA, build_m4_env, manifest_mismatch,
                             mission_eval)
from shepherd.spawn_rand import SpawnSpec, StandbySpec

KW = dict(system=ratified_system(),
          reward=RewardSpec(w_kill=0.5, enabled=True),
          attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
          spawn=SpawnSpec())


def test_ratified_system_is_the_f_contract():
    """비준 계약 = F-flags (docs/53-54). 필드 기본값(legacy)은 불변이어야 한다."""
    s = ratified_system()
    assert s.enabled and s.contact_resolver and not s.miss_terminates
    d = SystemSpec()
    assert not d.contact_resolver and d.miss_terminates   # legacy 기본값 보존
    assert ratified_system(p_kill=0.7).p_kill == 0.7      # override 통과


def test_manifest_attached_and_stable_across_episodes():
    """에피소드별 위협 draw 는 분포의 표본이지 계약이 아니다 -- hash 동일."""
    a = build_m4_env(0, 0, **KW).contract
    b = build_m4_env(0, 7, **KW).contract
    assert a["schema"] == CONTRACT_SCHEMA
    assert a["system"]["contact_resolver"] is True
    assert a["system"]["miss_terminates"] is False
    assert a["hash"] == b["hash"]


def test_manifest_detects_dropped_standby_and_extra_cfg():
    """전달 누락 = 다른 세계. manifest 가 그것을 보이게 만든다 (A4a 의 존재 이유)."""
    full = build_m4_env(0, 0, standby=StandbySpec(R=12.0),
                        extra_cfg={"train.episode_len": 12}, **KW).contract
    dropped = build_m4_env(0, 0, **KW).contract
    diffs = manifest_mismatch(full, dropped)
    assert "standby" in diffs
    assert "episode_len" in diffs
    assert full["episode_len"] == 12
    assert full["hash"] != dropped["hash"]


def test_manifest_mismatch_allowlist_is_scoped():
    """선언된 축(w_kill 등)만 예외 -- 그 외는 전부 잡힌다."""
    a = build_m4_env(0, 0, **KW).contract
    b = build_m4_env(0, 0, **{**KW, "reward": RewardSpec(w_kill=1.0, enabled=True)}).contract
    assert manifest_mismatch(a, b) == ["reward.w_kill"]
    assert manifest_mismatch(a, b, allow=("reward.w_kill",)) == []


def test_mission_eval_passes_standby_and_extra_cfg_through():
    """docs/65 A3 — 종전에는 둘 다 버려져 조용히 legacy 기하로 평가됐다."""
    r = mission_eval(0, 1, standby=StandbySpec(R=12.0),
                     extra_cfg={"train.episode_len": 12},
                     limiter_mode="hold", **KW)
    c = r["contract"]
    assert c["standby"] is not None and c["standby"]["R"] == 12.0
    assert c["episode_len"] == 12


def test_current_runners_share_the_ratified_contract():
    """docs/65 A2 — sweep/curve/factorial/bc 가 전부 같은 계약에서 파생된다."""
    from shepherd.scripts.curve_sweep import _default_kw
    from shepherd.scripts.mobility_factorial import _kw as factorial_kw
    from shepherd.train.bc_aim import _kw as bc_kw
    ref = ratified_system()
    for name, kw in (("curve", _default_kw(0.5, "A2", 0.6)),
                     ("factorial", factorial_kw()), ("bc", bc_kw())):
        assert kw["system"] == ref, f"{name} runner 가 비준 계약에서 벗어났다"


def test_train_specs_derive_from_ratified_contract():
    """docs/65 A1 — 학습기 CLI 기본이 비준 계약이다 (torch 필요, 서버 검증)."""
    pytest.importorskip("torch")
    from shepherd.scripts.train_m4 import build_parser_defaults, build_specs
    s = build_specs(build_parser_defaults())["system"]
    assert s == ratified_system()
