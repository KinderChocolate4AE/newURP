"""R-010 회귀 게이트 — 접촉 계수의 accounting 불변식 (Session 4 Stage 2).

WHY (감사 Session 2 X-013)
--------------------------
`mission_rollout` 의 모듈 docstring 은 이 등식을 **자기 correctness 논거**로 내세운다:

    "술어는 env 와 동일하고(||p_att - c|| <= kill_radius), env 와 같은 **이동 전**
     상태에서 평가한다 -- 그래서 누적 `contact_steps` 가 env 의 `limiter_loss`
     합과 일치해야 한다(자체 검사)."

`MissionResult` 는 두 값을 다 기록하는데 **어디서도 assert 되지 않았다.** 두 필드는
테스트에서 arm 간 bit-exactness 비교의 재료로만 쓰였을 뿐이다.

두 계측이 진짜 독립인가 (전제 확인)
-----------------------------------
같은 내부 flag 에서 파생되면 함께 틀려도 서로 같아 보인다. 실제로는 독립이다:

    env.py:360-361            sum(1 for c in lim_pos if |p_att - c| <= kill_radius)
    mission_rollout.py:311    for i, s in enumerate(lims): if |p_att - _p(s)| <= ...

같은 술어·같은 (이동 전) 상태를 **서로 다른 코드**가 센다 (env.py:236·238 이
이동 전, post 는 :353 의 `p_att2` 로 분리돼 있다). 가중치 없는 순수 카운트라
값이 정확히 같아야 한다.

★ 판정 계약 (Stage 2 규율)
--------------------------
    No parity without discriminating coverage.
    No configured knob without resolved-value verification.

    A. contact-rich fixture 가 **독립 경로**로 접촉을 증언한다 (resolver event >= 1)
    B. contact_steps > 0
    C. env_limiter_loss_sum > 0
    D. **episode-wise** contact_steps == env_limiter_loss_sum
    E. resolved config 가 의도한 값인가 (contact_resolver / kill_radius)

D 를 총합이 아니라 **에피소드 단위**로 보는 이유: 30 판에서 `17 == 17` 만 보면
한 판의 +1 과 다른 판의 -1 이 상쇄된다.

A 가 별도로 필요한 이유: B·C 는 둘 다 "접촉 계수" 라는 같은 범주의 양이다.
그 둘이 함께 0 이면 D 가 자명하게 성립한다 (`0 == 0` 은 evidence 가 아니다).
그래서 **다른 코드 경로**인 `env_sys._resolve_contacts` 의 event 로 기하 자체에
접촉이 실재함을 따로 증언시킨다. 이 resolver 는 swept 거리 + `r_contact` 를 쓰므로
술어가 달라 값은 같지 않다 -- 같을 필요도 없고, 여기서는 **존재 증언**만 쓴다.

세계 선택
---------
동결 params (kill_radius 2.0) + intercept 추격. T1 canonical 세계는 접촉이 희소해
(canonical 곡선 2700 판에서 CAPTURE_WITH_CONTACT 0 건) 게이트가 공회전한다.
이 테스트가 검증하는 것은 T1 의 과학 결과가 아니라 `mission_rollout <-> env` 의
accounting 이므로 contact-rich fixture 가 올바른 선택이다.

★ stop rule: 접촉이 있는데 등식이 깨지면 assertion 을 완화하거나 fixture 를 바꾸지
   않는다. **새 P0 finding 으로 승격하고 Stage 2 를 중단한다.**

torch-free.
"""
from __future__ import annotations

import pytest

from shepherd.env_sys import ModeSystemEnv, RewardSpec, SystemSpec
from shepherd.params import as_config
from shepherd.scripts.mission_rollout import run_episode
from shepherd.train.make_env import make_train_env

SLOW_LIMITER = {"train.limits.limiter_v_max": 21.0}
N_EPISODES = 8
MODE, FIRE, COMMIT = "intercept", "clean", False


def _world(spec: SystemSpec):
    inner, scn, lay = make_train_env(as_config(SLOW_LIMITER))
    env = ModeSystemEnv(inner, lay, scn, spec, RewardSpec(w_kill=0.5, enabled=True))
    return env, scn, lay


@pytest.fixture(scope="module")
def accounting():
    """resolver off — 접촉이 종료를 일으키지 않아 여러 스텝에 걸쳐 누적된다."""
    rows = []
    for ep in range(N_EPISODES):
        env, scn, lay = _world(SystemSpec(enabled=True, contact_resolver=False))
        r = run_episode(env, scn, lay, seed=ep, limiter_mode=MODE,
                        fire_mode=FIRE, baseline_commit=COMMIT)
        rows.append({"episode": ep, "label": r.label,
                     "contact_steps": int(r.contact_steps),
                     "loss_sum": float(r.env_limiter_loss_sum),
                     "n_contact": int(r.n_contact),
                     "kill_radius": float(env.kill_radius),
                     "contact_resolver": bool(env.spec.contact_resolver)})
    return rows


# ------------------------------------------- E. resolved-value verification ---
def test_r010_fixture_resolved_config_is_what_we_think(accounting):
    """설정한 knob 이 **resolved 값**을 실제로 만들었는지 먼저 고정한다.

    (Stage 1 교훈: `train.limits.limiter_kill_radius` 는 조용히 무시되는 키였다.
     설정했다고 믿은 값이 실제로 서 있는지 확인하지 않으면 게이트가 통째로 무의미해진다.)
    """
    assert all(r["contact_resolver"] is False for r in accounting), \
        "resolver 가 켜져 있어 접촉이 종료를 일으킨다 -- 누적 계정 검정 불가"
    krs = {r["kill_radius"] for r in accounting}
    assert krs == {2.0}, f"kill_radius 가 예상과 다르다: {krs}"


# ------------------------------------------------ A. 독립 경로의 접촉 증언 ---
def test_r010_contact_is_witnessed_by_an_independent_path():
    """★ 같은 기하에서 `env_sys._resolve_contacts` 가 접촉 event 를 낸다.

    B·C 는 둘 다 "접촉 계수" 라 함께 0 이면 D 가 자명해진다. resolver 는 **다른
    코드·다른 술어(swept + r_contact)** 라 기하에 접촉이 실재한다는 독립 증언이 된다.
    """
    env, scn, lay = _world(SystemSpec(enabled=True, contact_resolver=True,
                                      p_kill=1.0, r_nk=0.0))
    assert env.spec.contact_resolver is True
    run_episode(env, scn, lay, seed=0, limiter_mode=MODE,
                fire_mode="never", baseline_commit=COMMIT)
    events = [c for c in env.commits if c.source == "contact"]
    assert events, "resolver 가 접촉 event 를 하나도 내지 않았다 -- fixture 재검토"


# --------------------------------------------------- B·C. 비자명성 (공회전 차단) ---
def test_r010_counters_are_nonzero(accounting):
    """`0 == 0` 은 evidence 가 아니다. 두 계측 모두 실제로 세고 있어야 한다."""
    tot_steps = sum(r["contact_steps"] for r in accounting)
    tot_loss = sum(r["loss_sum"] for r in accounting)
    assert tot_steps > 0, "접촉이 한 건도 없어 게이트가 공회전했다"
    assert tot_loss > 0, "env 쪽 limiter_loss 가 전부 0 -- 두 계측 중 하나가 죽었다"
    n_eps_with_contact = sum(1 for r in accounting if r["contact_steps"] > 0)
    assert n_eps_with_contact >= 3, (
        f"접촉이 난 에피소드가 {n_eps_with_contact} 개뿐 — 표본이 약하다")


# --------------------------------------------------- D. episode-wise 등식 ---
def test_r010_contact_steps_equal_limiter_loss_per_episode(accounting):
    """★ 본 불변식 — **에피소드 단위**로 두 계측이 일치한다.

    총합만 비교하면 판 사이의 +1 / -1 이 상쇄된다.

    ★ 깨지면: assertion 을 완화하거나 fixture 를 바꾸지 말 것. 새 P0 finding 으로
      승격하고 Stage 2 를 중단한다 (Session 4 R-010 stop rule).
    """
    bad = [r for r in accounting if r["contact_steps"] != r["loss_sum"]]
    assert not bad, (
        "mission_rollout 과 env 의 접촉 계수가 갈라졌다 (docstring 자체검사 위반):\n"
        + "\n".join(f"  ep{r['episode']} ({r['label']}): "
                    f"contact_steps {r['contact_steps']} != "
                    f"limiter_loss {r['loss_sum']}" for r in bad))


def test_r010_set_size_is_bounded_by_step_count(accounting):
    """집합 크기 <= 스텝별 합 (같은 limiter 가 여러 스텝 중복 계수되므로).

    docstring 이 `n_contact` 를 에피소드 라벨용, `contact_steps` 를 대조용으로
    나눈 이유를 고정한다 -- 둘이 같아져 버리면 중복 계수 서술이 거짓이 된다.
    """
    for r in accounting:
        assert r["n_contact"] <= r["contact_steps"], \
            f"ep{r['episode']}: 집합 {r['n_contact']} > 스텝합 {r['contact_steps']}"
    assert any(r["n_contact"] < r["contact_steps"] for r in accounting), \
        "중복 계수가 한 번도 일어나지 않아 두 필드의 구분이 검증되지 않았다"


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
