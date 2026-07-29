"""공격자 주입 — FROZEN env.py 를 건드리지 않고 사다리 공격자를 끼우는 경로.

문제 (docs/27 §1)
----------------
`shepherd/env.py` L334-339 는 공격자를 하드코딩 호출한다:

    committed = self.fsm.state in (DEPLOYING, LOCKED)
    adv = scripted_adversary_action(p_att, v_att, target=..., committed=committed, ...)
    bk_action[self.adversary_id] = adv
    self.backend.step(bk_action)

dispatch 파라미터가 없고 env.py 는 동결이다. `env_m3.py` L340-345 도 같은 블록을
복사해 갖고 있다.

채택한 해법 -- 백엔드 프록시 (docs/27 §1.3 의 서브클래스 안을 대체)
------------------------------------------------------------------
docs/27 은 `env_m3.py` 처럼 서브클래스 + step() 복사를 제안했다. 실제로 짜 보니
step() 이 **163줄**이고 그러면 리포에 복사본이 3개가 된다(env / env_m3 / env_adv).
드리프트 비용이 이득보다 크다.

대신 **이미 주입식으로 설계된 seam** 을 쓴다. `sim/interface.py` 가 백엔드를
pluggable ABC 로 규정하고(`"backends are swappable"`), `make_env.py` 가 그것을
composition root 에서 주입한다. 그 백엔드를 감싸서 `step()` 이 백엔드에 닿기 직전에
adversary 항목만 교체한다.

    env.backend = attach_attacker(env, attacker)

이것은 몽키패치가 **아니다** -- 주입된 의존성을 데코레이트하는 것이고, 리포가 그
seam 을 그렇게 쓰라고 만들어 뒀다. 코드베이스 어디에도 `isinstance(backend, ...)`
검사는 없다(확인함).

정확성이 왜 보장되는가
---------------------
env.step() 안의 순서:

    L263  self._step_i += 1
    L265  lims, fin, att = self._states()          <- 이동 전 상태
    L308  self.fsm = step_fsm(...)                 <- FSM 갱신
    L333  committed = self.fsm.state in (...)
    L340  bk_action[adversary_id] = adv
    L342  self.backend.step(bk_action)             <- 여기서 프록시가 가로챈다

L342 시점에 백엔드는 **아직 움직이지 않았고** FSM 은 **이미 갱신됐다**. 따라서
프록시가 그 자리에서 읽는 `env._states()` / `env.fsm.state` 는 env.py 가 L334-339
에서 쓴 값과 **정확히 같다**. 근사가 아니라 동일하다.

부수 효과: 동결 공격자는 여전히 계산되고 버려진다(마이크로초 단위). 오히려 좋다 --
`assert_delegation=True` 로 두면 매 스텝 A1 출력이 동결 경로와 같은지 대조하는
연속 점검이 공짜로 생긴다.

이 경로는 `env_m3.py` 에도 그대로 붙는다(M3 도 같은 자리에서 backend.step 을
호출하므로) -- 서브클래스 안에는 없던 이득이다.

torch-free.
"""
from __future__ import annotations

from typing import Callable, Optional

import numpy as np

from shepherd.game.finisher_fsm import FinisherState
from shepherd.sim.interface import EnvBackend

__all__ = ["AdversaryOverrideBackend", "attach_attacker", "detach_attacker"]


class AdversaryOverrideBackend(EnvBackend):
    """주입된 백엔드를 감싸 adversary 행동만 교체한다. 그 외는 전부 그대로 위임."""

    def __init__(self, inner: EnvBackend, env, attacker: Callable,
                 *, assert_delegation: bool = False, atol: float = 0.0):
        self._inner = inner
        self._env = env
        self._attacker = attacker
        self._assert_delegation = bool(assert_delegation)
        self._atol = float(atol)
        self.n_override = 0

    # --- EnvBackend ABC -----------------------------------------------------
    def reset(self, seed: int):
        return self._inner.reset(seed)

    def observe(self):
        return self._inner.observe()

    def step(self, action):
        env = self._env
        aid = env.adversary_id
        if self._attacker is None or action is None or aid not in action:
            return self._inner.step(action)

        kw = self._gather()
        mine = self._attacker(kw.pop("p_att"), kw.pop("v_att"), **kw)

        if self._assert_delegation:
            frozen = np.asarray(action[aid]["a"], float)
            got = np.asarray(mine["a"], float)
            if not np.allclose(frozen, got, rtol=0.0, atol=self._atol):
                raise AssertionError(
                    f"delegation mismatch at step {env._step_i}: "
                    f"frozen={frozen} attacker={got}")

        act = dict(action)
        act[aid] = mine
        self.n_override += 1
        return self._inner.step(act)

    # --- 나머지는 내부 백엔드로 (by_name / agents / dt / state9 ...) ---------
    def __getattr__(self, name):
        return getattr(self.__dict__["_inner"], name)

    # --- helpers ------------------------------------------------------------
    def _gather(self) -> dict:
        """env.py L334-339 가 넘기는 것과 **동일한** 인자 묶음.

        상태 추출은 `env._states()` 를 그대로 재사용한다 -- 따로 짜면 언젠가
        어긋난다.
        """
        env = self._env
        lims, fin, att = env._states()
        p_att, v_att = env._p(att), env._v(att)
        lim_pos = [env._p(s) for s in lims]
        committed = env.fsm.state in (FinisherState.DEPLOYING, FinisherState.LOCKED)
        return dict(
            p_att=p_att, v_att=v_att,
            target=env.layout.target,
            net_center=env._net_center(p_att, v_att),
            finisher_p=env._p(fin),
            limiters=lim_pos,
            kill_radius=env.kill_radius,
            a_att_max=env.adv_a_max,
            omega_att_max=8.0,               # env.py 하드코딩값 (DEAD 이지만 동일하게)
            v_nominal=env.v_nominal,
            dt=env.dt,
            committed=committed,
            repel_margin=1.0,                # env.py 하드코딩값
            t=float(env._step_i) * float(env.dt),
            phase=float(getattr(env, "_attacker_phase", 0.0)),
            # A3-privileged 전용. 루프 구동자가 직전 스텝 info 에서 넣어준다.
            # 없으면 A3-fair 대리량으로 폴백한다(관측 가능량만 사용).
            v_shot_soft=getattr(env, "_last_v_shot_soft", None),
        )


def attach_attacker(env, attacker: Optional[Callable], *,
                    assert_delegation: bool = False, phase: float = 0.0):
    """env 의 백엔드를 프록시로 감싸고 공격자를 주입한다. env 를 그대로 반환.

    이미 붙어 있으면 교체한다(중첩 방지).
    """
    env._attacker_phase = float(phase)
    if isinstance(env.backend, AdversaryOverrideBackend):
        env.backend._attacker = attacker
        env.backend._assert_delegation = bool(assert_delegation)
        env.backend.n_override = 0
        return env
    env.backend = AdversaryOverrideBackend(
        env.backend, env, attacker, assert_delegation=assert_delegation)
    return env


def detach_attacker(env):
    """프록시를 벗겨 동결 경로로 되돌린다."""
    if isinstance(env.backend, AdversaryOverrideBackend):
        env.backend = env.backend._inner
    return env
