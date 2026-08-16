"""R-001 회귀 게이트 — 커밋 기하 margin 의 **단일 정의원** (Session 4 Stage 1).

계약: 커밋 기하 판정 반경

    margin = r_commit + 0.5*(a_lim_max - a_att_max)*tau_kill^2
    r_commit = spec.r_commit if spec.r_commit is not None else inner.kill_radius

은 `env_sys` 가 권위 소스이고, limiter 의 커밋 비트를 세우는
`mission_rollout._limiter_actions` 는 **같은 값**을 써야 한다.

WHY (감사 Session 2 §C.5)
-------------------------
현재 두 곳이 독립적으로 계산한다.

    env_sys.py:327-329        r_commit (spec 인지)      <- 권위
    mission_rollout.py:192    env.kill_radius (spec 무시)

`ratified_system()` 은 `r_commit=None` 이라 둘이 우연히 같은 값이 되고, 비준 운용점
실측으로도 bit-identical 이다 (0.42797472527106606). 그래서 지금까지 아무 테스트도
안 깨졌다. 그러나 `SystemSpec.r_commit` 은 **살아 있는 필드**다 — `env_sys` 가
"반경 3종 의미 분리" 를 위해 일부러 배선해 뒀고 (`r_shape`/`r_commit`/`r_contact`),
문서가 "수치 calibration 은 별도 실험 후" 라고 예고했다. 그 실험을 여는 순간
limiter 의 **결정** 반경과 env 의 **해소** 반경이 조용히 갈라진다.

그 필드가 결과를 바꾼다는 것은 이 파일의 `test_r001_r_commit_is_outcome_material`
이 직접 보인다 (같은 seed 에서 HARD_KILL <-> PENETRATED 가 뒤집힌다). 즉 cosmetic
파라미터가 아니라 outcome-material 파라미터이며, 그래서 등급이 P0-LATENT 다.

판정 규율 (Session 4 R-001)
---------------------------
    현 HEAD 에서 RED   -> finding 확정, 최소 helper patch 진행
    현 HEAD 에서 GREEN -> finding 폐기. 고치지 말고 보고할 것.

`r_commit=None` cell 과 `tau_kill` cell 은 **대조군**이라 patch 전에도 GREEN 이다
(divergence 축이 아님을 고정한다). RED 여야 하는 건 `r_commit` 이 실제 값인 cell 뿐.

측정 방식 (공식 복제 금지)
--------------------------
두 값을 **관측**한다 — 테스트가 어느 쪽 공식도 다시 쓰지 않는다.

    mission_rollout 쪽: `intercept_limiter` 로 넘어가는 `margin` 인자를 spy 로 포착
    env_sys 쪽:        커밋이 해소한 `CommitRecord.margin` (step() 이 쓴 바로 그 값)

`contact_resolver=False` 로 두어 모든 record 가 `source="commit"` 이 되게 한다
(접촉 record 는 `margin=r_contact` 라 다른 양이다).

★ 공회전 방지 (첫 초안이 두 번 걸렸다 — 기록으로 남긴다)
--------------------------------------------------------
1. **상수 충돌**: 이 fixture 의 `inner.kill_radius` 는 2.0 이다 (m4_config 의 0.75 가
   아니다). 처음에 `r_commit=2.0` 을 하드코딩했더니 kill_radius 와 같아져 divergence
   가 상쇄됐고 cell 이 통과해 버렸다. 이제 r_commit 값을 **fixture 에서 유도**한다.
2. **퇴화 항**: 이 fixture 는 기본적으로 `a_lim_max == a_att_max == 30.0` 이라 가속
   항이 **정확히 0** 이다. 그러면 `tau_kill` 이 0 에 곱해져 tau 대조군이 무엇을 넣든
   통과한다. 그래서 `SystemSpec.a_lim_max` 로 비대칭을 만들고, 가속 항이 0 이 아님을
   `_parts()` 가 **강제**한다.

torch-free.
"""
from __future__ import annotations

import pytest

from shepherd.env_sys import ModeSystemEnv, SystemSpec
from shepherd.params import as_config
from shepherd.scripts import mission_rollout
from shepherd.scripts.mission_rollout import run_episode
from shepherd.train.make_env import make_train_env

SLOW_LIMITER = {"train.limits.limiter_v_max": 21.0}   # test_contact_resolver 와 동일
A_LIM_OVERRIDE = 45.0        # a_att_max(30.0) 와 달라야 가속 항이 살아난다


def _spec(**over) -> SystemSpec:
    """가속 항이 0 이 아닌 계약. `a_lim_max` 를 명시하는 것이 핵심."""
    kw = dict(enabled=True, contact_resolver=False, a_lim_max=A_LIM_OVERRIDE)
    kw.update(over)
    return SystemSpec(**kw)


def _parts():
    """(kill_radius, 가속항) — 테스트 파라미터를 fixture 에서 유도하기 위한 것.

    가속 항이 0 이면 `tau_kill`/`a_lim_max` 축이 죽으므로 여기서 막는다.
    """
    inner, scn, lay = make_train_env(as_config(SLOW_LIMITER))
    env = ModeSystemEnv(inner, lay, scn, _spec())
    accel = 0.5 * (env.a_lim_max - inner.a_att_max) * env.spec.tau_kill ** 2
    assert accel != 0.0, (
        "가속 항이 0 이라 tau_kill/a_lim_max 축이 죽는다 — 게이트 공회전. "
        f"a_lim_max={env.a_lim_max} a_att_max={inner.a_att_max}")
    return float(inner.kill_radius), float(accel)


KILL_RADIUS, ACCEL_TERM = _parts()

#: kill_radius 와 절대 같아질 수 없는 divergent 값 (유도, 하드코딩 금지)
R_COMMIT_CASES = [KILL_RADIUS * 0.5, KILL_RADIUS + 1.0]


def _observed_margins(spec: SystemSpec):
    """(mission_rollout 이 쓴 margin, env_sys 가 쓴 margin).

    같은 세계·같은 seed 의 **한 번의 롤아웃**에서 양쪽을 동시에 관측한다.
    """
    inner, scn, lay = make_train_env(as_config(SLOW_LIMITER))
    env = ModeSystemEnv(inner, lay, scn, spec)

    seen: dict = {}
    original = mission_rollout.intercept_limiter

    def _spy(*args, **kwargs):
        seen.setdefault("margin", float(kwargs["margin"]))
        return original(*args, **kwargs)

    mission_rollout.intercept_limiter = _spy
    try:
        result = run_episode(env, scn, lay, seed=0, limiter_mode="intercept",
                             fire_mode="never", baseline_commit=True)
    finally:
        mission_rollout.intercept_limiter = original

    assert "margin" in seen, "intercept arm 이 호출되지 않아 검정 불가"
    commits = [c for c in env.commits if c.source == "commit"]
    assert commits, "커밋 record 가 없어 게이트가 공회전했다 (fixture 재검토 필요)"
    return seen["margin"], float(commits[0].margin), result


# --------------------------------------------------------------- 대조군 ---
def test_r001_control_default_r_commit_agrees():
    """대조 A — `r_commit=None` (비준 계약) 에서는 두 구현이 같다. patch 전에도 GREEN."""
    mr, env, _ = _observed_margins(_spec())
    assert mr == env, f"기본 계약에서 이미 갈라졌다: mission_rollout {mr} != env_sys {env}"
    # 대조군이 의미를 가지려면 가속 항이 실제로 값에 들어가 있어야 한다
    assert mr == pytest.approx(KILL_RADIUS + ACCEL_TERM), \
        f"margin 이 kill_radius+가속항 이 아니다: {mr}"


@pytest.mark.parametrize("tau_kill", [0.15, 0.20])
def test_r001_control_tau_kill_is_not_the_divergent_axis(tau_kill):
    """대조 B — `tau_kill` 은 양쪽 다 `spec.tau_kill` 을 읽는다. 선언된 sweep 축이
    divergence 원인이 **아님**을 고정한다. patch 전에도 GREEN.

    가속 항이 살아 있어야 이 대조가 공허하지 않다 -- `_parts()` 가 강제한다.
    """
    mr, env, _ = _observed_margins(_spec(tau_kill=tau_kill))
    assert mr == env, f"tau_kill={tau_kill}: {mr} != {env}"
    expect_accel = 0.5 * (A_LIM_OVERRIDE - 30.0) * tau_kill ** 2
    assert mr == pytest.approx(KILL_RADIUS + expect_accel), \
        f"tau_kill={tau_kill} 이 margin 에 반영되지 않았다: {mr}"


# ------------------------------------------------- ★ divergence 노출 ---
@pytest.mark.parametrize("r_commit", R_COMMIT_CASES)
def test_r001_mission_rollout_must_honor_r_commit(r_commit):
    """★ 본 게이트 — `r_commit` 이 실제 값이면 두 구현이 갈라진다.

    **현 HEAD 에서 반드시 RED.** GREEN 이면 R-001 finding 이 틀린 것이므로
    patch 하지 말고 카드를 폐기한다 (Session 4 R-001 판정 규율).
    """
    assert r_commit != KILL_RADIUS, "파라미터가 kill_radius 와 충돌 — cell 이 퇴화한다"
    mr, env, _ = _observed_margins(_spec(r_commit=r_commit))
    assert mr == env, (
        f"r_commit={r_commit}: mission_rollout 이 {mr} 로 커밋을 결정하는데 "
        f"env_sys 는 {env} 로 해소한다 (차이 {env - mr:+.4f}). "
        "limiter 의 결정 반경과 env 의 해소 반경이 갈라졌다.")


@pytest.mark.parametrize("r_commit", R_COMMIT_CASES)
def test_r001_divergence_survives_tau_sweep(r_commit):
    """★ 선언된 sweep 축(tau_kill=0.20)과 결합해도 divergence 가 남는지. 현 HEAD 에서 RED."""
    mr, env, _ = _observed_margins(_spec(r_commit=r_commit, tau_kill=0.20))
    assert mr == env, (
        f"r_commit={r_commit} tau_kill=0.20: {mr} != {env} (차이 {env - mr:+.4f})")


def test_r001_r_commit_is_outcome_material():
    """`r_commit` 이 cosmetic 이 아니라 **결과를 바꾸는** 파라미터임을 고정한다.

    이것이 R-001 을 P0-LATENT 로 두는 근거다 — divergence 가 열리면 바뀌는 것이
    진단값이 아니라 **종말 라벨**이다. (patch 후에도 GREEN 이어야 한다: patch 는
    두 구현을 일치시킬 뿐 `r_commit` 의 물리적 의미를 없애지 않는다.)
    """
    _, _, base = _observed_margins(_spec())
    _, _, tight = _observed_margins(_spec(r_commit=KILL_RADIUS * 0.5))
    assert base.label != tight.label, (
        f"r_commit 을 조여도 라벨이 그대로다 ({base.label}) — "
        "이 fixture 로는 outcome-material 임을 보일 수 없다")


# ------------------------------------------------- magic constant ---
def test_r001_tau_fallback_constant_matches_the_spec_default():
    """`mission_rollout.py:190` 의 `tau_k = 0.1` 이 `SystemSpec.tau_kill` 과 갈라져 있다.

    ★ 정직한 등급 (감사 Session 4, 하향): 이 상수는 **inert** 다 — `spec` 이 없는
    경로는 동결 env 뿐이고, 동결 env 는 limiter 행동 idx3(커밋 비트)을 무시한다
    (`tests/test_contact_resolver.py::test_p78_default_off_bit_identical` 이
    intercept 모드에서 wrapped/frozen 라벨 동일을 이미 강제한다). 따라서 이건
    outcome 을 바꿀 수 있는 latent divergence 가 아니라 **오해를 부르는 magic
    constant** 다. 그래도 `SystemSpec` 이 0.15 를 선언한 뒤 고아로 남은 값이므로
    한 곳으로 모은다.

    현 HEAD 에서 RED.
    """
    import inspect

    src = inspect.getsource(mission_rollout._limiter_actions)
    assert "0.1 if spec is None" not in src, (
        "tau 폴백이 하드코딩 0.1 이다. SystemSpec.tau_kill 기본값 "
        f"{SystemSpec().tau_kill} 과 갈라져 있다")


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
