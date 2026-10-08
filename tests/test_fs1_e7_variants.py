"""E7-b 세계 변형 손잡이 (docs/129 §6): 단일 소스 전파 + 기본값 no-op + ma 조준 분기."""
import numpy as np
import pytest

from shepherd.fs1.world import FS1Env, FS1Spec


def _rollout_sig(env, n=40, seed=5, jink=0.0):
    """jink > 0 이면 공격자 횡가속 residual (속도 변화 → â ≠ 0 유도)."""
    obs, _ = env.reset(seed=seed)
    sig = [obs["finisher_0"].copy()]
    for t in range(n):
        acts = {a: np.zeros(env.action_space(a).shape, np.float32)
                for a in list(env.limiter_ids) + ["finisher_0"]}
        acts["adversary_0"] = np.array([0.0, jink * (1 if t % 8 < 4 else -1), 0.0], np.float32)
        obs, _, done, _ = env.step(acts)
        sig.append(obs["finisher_0"].copy())
        if done:
            break
    return np.concatenate(sig)


def test_default_spec_is_noop():
    """기본값 (1.0/1.0/cv) 두 env 가 bit-동일 + 현행 상수 유지."""
    e1, e2 = FS1Env(FS1Spec(), seed=0), FS1Env(FS1Spec(), seed=0)
    assert e1.inner.tau_deploy == pytest.approx(0.30)
    np.testing.assert_array_equal(_rollout_sig(e1), _rollout_sig(e2))


def test_tau_single_source_propagates_both():
    """tau_scale 이 env.tau_deploy 와 scenario(FSM 타이머 원천) 양쪽에 전파 (JAX risk①)."""
    env = FS1Env(FS1Spec(tau_scale=0.5), seed=0)
    inn = env.inner
    assert inn.tau_deploy == pytest.approx(0.15)
    assert float(inn.sc.finisher.tau_deploy) == pytest.approx(0.15)


def test_theta_scale_judge_only():
    base = float(FS1Env(FS1Spec(), seed=0).inner.cone_half_angle)
    env = FS1Env(FS1Spec(theta_scale=1.5), seed=0)
    assert env.inner.cone_half_angle == pytest.approx(base * 1.5)


def test_ma_aim_diverges_cv_identical():
    """같은 seed: cv 변형 == 기본 (bit), ma 변형은 finisher 관측이 어느 tick 에선 달라짐."""
    jk = 10.0                            # 횡 jink: 속도 변화 → â ≠ 0 (등속이면 ma == cv 가 정당)
    s_def = _rollout_sig(FS1Env(FS1Spec(), seed=0), jink=jk)
    s_cv = _rollout_sig(FS1Env(FS1Spec(aim="cv"), seed=0), jink=jk)
    s_ma = _rollout_sig(FS1Env(FS1Spec(aim="ma"), seed=0), jink=jk)
    np.testing.assert_array_equal(s_def, s_cv)
    assert not np.array_equal(s_def, s_ma)


# ---- E7-c (docs/130 §5) ----------------------------------------------------
def _hl(env, arm=1.0):
    hl = {l: np.array([0.0, 0.0, 0.0, arm], np.float32) for l in env.limiter_ids}
    hl["finisher_0"] = np.array([0, 0, 0, 12.0, 0.0], np.float32)
    return hl


def test_limiter_defaults_noop():
    env = FS1Env(FS1Spec(), seed=0)
    env.reset(seed=1)
    assert not env.limiters_harmless()
    assert env.sys.spec.contact_resolver == env._contact0


def test_post_shot_blocks_kinetic_until_first_fire():
    env = FS1Env(FS1Spec(limiter_roe="post_shot"), seed=0)
    env.reset(seed=1)
    assert env.limiters_harmless()
    acts = env.fcs(_hl(env, arm=1.0))
    for l in env.limiter_ids:                          # 발사 전: 무장 채널 0 → PN 커밋 경로 없음
        assert acts[l][3] == 0.0
    env.step({**_hl(env), "adversary_0": np.zeros(3, np.float32)})
    assert env.sys.spec.contact_resolver is False      # 발사 전: 접촉 kinetic 경로 꺼짐
    env._fired = True                                  # 첫 발사 latch 이후
    assert not env.limiters_harmless()
    env.step({**_hl(env), "adversary_0": np.zeros(3, np.float32)})
    assert env.sys.spec.contact_resolver == env._contact0


def test_inert_kill_radius_zero_and_judge_ignores_limiters():
    env = FS1Env(FS1Spec(limiter_inert=True), seed=0)
    env.reset(seed=1)
    inn = env.inner
    assert inn.kill_radius == 0.0 and env.limiters_harmless()
    lims, fin, att = inn._states()
    p, v = inn._p(att), inn._v(att)
    near = [p + np.array([0.3, 0, 0]), p - np.array([0.3, 0, 0])]   # 탈출 구 안쪽에 limiter
    a = inn._vshot(p, v, near, fin, seed=7)
    b = inn._vshot(p, v, [], fin, seed=7)
    assert (a.v_shot_worst, a.v_shot_soft, a.boxed_in) == (b.v_shot_worst, b.v_shot_soft, b.boxed_in)


def test_kill_phase_classification():
    from shepherd.fs1.eval import _kill_phase
    assert _kill_phase("K_FIRST", 0) == "pre_shot"
    assert _kill_phase("K_FIRST", 1) == "shot_window"
    assert _kill_phase("HARD_KILL", 1) == "fallback"
    assert _kill_phase("NET_CAPTURE", 1) is None
