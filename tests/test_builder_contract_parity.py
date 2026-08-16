"""R-005 회귀 게이트 — 살아 있는 world builder 전부의 **resolved contract** parity.

WHY (감사 Session 2 X-016)
--------------------------
`test_contract_parity.test_current_runners_share_the_ratified_contract` 는
`curve` / `factorial` / `bc` 세 runner 만 훑는다. 그런데 과학 결과를 만드는
builder 는 그보다 많고, ratified 계약을 **세 가지 서로 다른 철자**로 쓴다.

    ratified_system()                                    curve / e1d / lead_time / t1
    SystemSpec(enabled=..., contact_resolver=..., ...)   dump_trajectory v2/v3
    ratified 파생 + p_kill 명시                           recoverability_probe._flags

Session 2 가 HEAD 에서 셋이 같은 값임을 확인했지만, 그건 일회성 관측이고
`SystemSpec` 기본값이 하나만 움직여도 조용히 갈라진다.

★ 이 게이트의 규율 (Stage 2 공통)
---------------------------------
    No parity without discriminating coverage.
    No configured knob without resolved-value verification.

그래서 builder 의 **kwargs 를 비교하지 않는다** -- kwargs 가 같아도 resolve 결과가
다를 수 있고, 무엇보다 kwargs 비교는 "전달 누락(silent legacy fallback)" 을 못 잡는다.
대신 `build_m4_env` 를 spy 로 감싸 **실제로 만들어진 resolved contract manifest**
(`contract_manifest` 산물 + sha256 hash) 를 포착해 비교한다.

theatrical test 방지: `test_r005_comparison_has_discriminating_power` 가 비교
기계 자체가 살아 있는지(= 다른 세계는 실제로 다르게 나오는지) 먼저 확인한다.
전부 같게 나오는 비교는 통과해도 아무것도 증명하지 않는다.

torch-free.
"""
from __future__ import annotations

from dataclasses import asdict

import pytest

import shepherd.m4_env as m4_env
import shepherd.scripts.dump_trajectory as dump_trajectory
import shepherd.scripts.e1d_commit_geom as e1d_commit_geom
import shepherd.scripts.lead_time_diag as lead_time_diag
import shepherd.scripts.recoverability_probe as recoverability_probe
from shepherd.env_sys import ratified_system
from shepherd.m4_env import build_m4_env, manifest_mismatch
from shepherd.scripts.curve_sweep import _default_kw

#: curve_sweep 이 캠페인에서 쓴 값 (T1 reactive). 헤드라인 곡선의 세계.
CURVE_KW = dict(w_kill=0.5, level="A2", jink=0.6,
                route_gain=0.5, sense_range=30.0, capture_terminates=True)


def _contract_of(monkeypatch, builder, *modules):
    """builder 를 호출하고 `build_m4_env` 가 **실제로** 만든 contract 를 포착한다.

    function-level import 를 쓰는 builder(dump_trajectory) 는 `m4_env` 쪽 패치가,
    module-level import 를 쓰는 builder(e1d/lead_time/recoverability) 는 자기
    네임스페이스 패치가 걸린다 -- 둘 다 건다.
    """
    store: dict = {}
    real = m4_env.build_m4_env

    def _spy(*args, **kwargs):
        st = real(*args, **kwargs)
        store.setdefault("contract", st.contract)
        return st

    monkeypatch.setattr(m4_env, "build_m4_env", _spy)
    for mod in modules:
        if hasattr(mod, "build_m4_env"):
            monkeypatch.setattr(mod, "build_m4_env", _spy)
    builder()
    assert "contract" in store, \
        "builder 가 build_m4_env 를 호출하지 않았다 -- resolved contract 관측 불가"
    return store["contract"]


def _curve_contract():
    return build_m4_env(0, 0, **_default_kw(**CURVE_KW)).contract


#: (이름, builder 호출, 패치할 모듈들)
BUILDERS = {
    "dump._build_t1":  (lambda: dump_trajectory._build_t1(0), (dump_trajectory,)),
    "dump._build_v2":  (lambda: dump_trajectory._build_v2(0), (dump_trajectory,)),
    "dump._build_v3":  (lambda: dump_trajectory._build_v3(0), (dump_trajectory,)),
    "e1d._build":      (lambda: e1d_commit_geom._build(0), (e1d_commit_geom,)),
    "lead_time._build": (lambda: lead_time_diag._build(0, 24.0), (lead_time_diag,)),
    "probe._build":    (lambda: recoverability_probe._build(0), (recoverability_probe,)),
}


# --------------------------------------------- 전제: 비교 기계가 살아 있는가 ---
def test_r005_comparison_has_discriminating_power(monkeypatch):
    """★ 반-theatre 전제 — 다른 세계는 실제로 **다르게** 나와야 한다.

    모든 builder 가 같은 hash 를 내면 이 파일의 다른 통과는 전부 공허하다.
    `manifest_mismatch` 가 죽어 있어도 마찬가지다.
    """
    hashes = {}
    for name, (call, mods) in BUILDERS.items():
        hashes[name] = _contract_of(monkeypatch, call, *mods)["hash"]
    assert len(set(hashes.values())) >= 3, (
        f"builder 들이 사실상 한 세계로 붕괴했다 -- 비교가 무의미하다: {hashes}")

    # mismatch 기계 자체도 살아 있어야 한다 (선언된 다른 세계를 실제로 잡는가)
    c_probe = _contract_of(monkeypatch, *(BUILDERS["probe._build"][0],),
                           *BUILDERS["probe._build"][1])
    diffs = manifest_mismatch(c_probe, _curve_contract())
    assert diffs, "manifest_mismatch 가 선언된 다른 세계조차 잡지 못한다"


# ------------------------------------------------ ratified system 철자 통일 ---
@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_r005_every_builder_resolves_the_ratified_system(monkeypatch, name):
    """세 가지 철자가 **같은 resolved SystemSpec** 으로 수렴하는지.

    `SystemSpec` 기본값이 하나만 움직여도 raw 철자 쪽이 조용히 뒤처진다.
    """
    call, mods = BUILDERS[name]
    got = _contract_of(monkeypatch, call, *mods)["system"]
    want = asdict(ratified_system())
    assert got == want, (
        f"{name} 의 resolved system 이 비준 계약과 다르다:\n"
        f"  차이 { {k: (got.get(k), want.get(k)) for k in want if got.get(k) != want.get(k)} }")


# ----------------------------------------- ★ 문서화된 동치: t1 == curve ---
def test_r005_build_t1_is_the_curve_world(monkeypatch):
    """★ `_build_t1` docstring 의 load-bearing 주장을 contract 수준에서 못 박는다.

    "이 빌더로 덤프해야 `results/curve_intercept_reactive.json` 의 에피소드
    라벨과 1:1 대응한다" -- E3 · E4 · R4 회귀 · 뷰어가 전부 이 빌더를 쓰므로,
    이것이 깨지면 그 산출물 전체가 헤드라인 곡선과 다른 세계가 된다.
    """
    c_t1 = _contract_of(monkeypatch, *(BUILDERS["dump._build_t1"][0],),
                        *BUILDERS["dump._build_t1"][1])
    c_curve = _curve_contract()
    diffs = manifest_mismatch(c_t1, c_curve)
    assert not diffs, f"_build_t1 이 curve_sweep 세계에서 벗어났다: {diffs}"
    assert c_t1["hash"] == c_curve["hash"]


def test_r005_e1d_default_is_the_curve_world(monkeypatch):
    """E1d 의 무개입 기본값도 같은 세계여야 한다 (Pass 1 이 곡선과 비교 가능해야)."""
    c = _contract_of(monkeypatch, *(BUILDERS["e1d._build"][0],),
                     *BUILDERS["e1d._build"][1])
    assert not manifest_mismatch(c, _curve_contract())


def test_r005_e1d_intervention_moves_exactly_two_fields(monkeypatch):
    """개입을 켜면 **정확히** force_commit_step / perfect_aim_at_commit 만 움직인다.

    knob 을 설정했는데 resolved 값이 안 움직이면(또는 다른 것까지 움직이면)
    E1d 의 two-pass replay 전제가 깨진다 -- resolved-value verification.
    """
    c = _contract_of(monkeypatch,
                     lambda: e1d_commit_geom._build(0, force_step=7, ideal=True),
                     e1d_commit_geom)
    diffs = manifest_mismatch(c, _curve_contract())
    assert set(diffs) == {"system.force_commit_step", "system.perfect_aim_at_commit"}, \
        f"개입이 움직인 축: {diffs}"
    assert c["system"]["force_commit_step"] == 7
    assert c["system"]["perfect_aim_at_commit"] is True


# ------------------------------------- 선언된 다른 세계: 차이 집합을 고정 ---
def test_r005_lead_time_differs_only_on_declared_axes(monkeypatch):
    """lead-time 은 **의도적으로** 다른 세계다. 그 차이가 선언된 축뿐인지 고정한다.

    `SENSE = inf` 는 lead_time_diag.py:56 에 "★ 무제한 — 가시성을 교란에서
    제거 (등록 T1 아님)" 로 명시돼 있고, 지평선/시작거리는 arm 정의다.
    선언되지 않은 축이 하나라도 끼면 이 진단은 곡선과 비교 불가가 된다.
    """
    c = _contract_of(monkeypatch, *(BUILDERS["lead_time._build"][0],),
                     *BUILDERS["lead_time._build"][1])
    diffs = set(manifest_mismatch(c, _curve_contract()))
    declared = {"attacker.sense_range", "episode_len",
                "extra_cfg.train.episode_len",
                "extra_cfg.train.layout.adversary_start_x"}
    assert diffs == declared, f"선언되지 않은 축이 갈라졌다: {diffs - declared}"
    assert c["attacker"]["sense_range"] == float("inf")


def test_r005_probe_differs_only_on_declared_attacker_axes(monkeypatch):
    """recoverability probe 는 legacy(비반응형) 공격자 세계다 -- 그 차이만 있어야 한다."""
    c = _contract_of(monkeypatch, *(BUILDERS["probe._build"][0],),
                     *BUILDERS["probe._build"][1])
    diffs = set(manifest_mismatch(c, _curve_contract()))
    assert diffs == {"attacker.route_gain", "attacker.sense_range"}, \
        f"선언되지 않은 축이 갈라졌다: {diffs}"


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
