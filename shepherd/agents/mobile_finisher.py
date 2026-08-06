"""해석적 병진 제어기 — 이동형 포획기 (docs/51 §2.2).

WHY
---
docs/50 §4 를 쓰다가 `finisher` 가 위치 고정이라는 것이 한계 절에서 빠져 있음을
발견했다. 외부 리뷰 판정은 **(C)** -- 전면 재설계 전에, 고정 가정이 조준 결손을
인위적으로 치명적으로 만든 것인지를 **학습 없이** 먼저 재라는 것이다.

    (1) 알고리즘 설명   희소 종말 보상 -> RL 이 조준을 학습 못 함
    (2) 설계 설명       고정 포획기가 조준 오차를 병진으로 흡수 못 하게 만들어
                        부분 결손을 임무 실패로 증폭

BC 가 조준을 97 % 회복시킨 것은 (1) 을 지지하지만 (2) 를 **제거하지 않는다**.
이 모듈이 (2) 를 재는 도구다.

설계 근거 (실측 기하)
--------------------
    range_min = 0.0     <- ★ 최소 사거리가 없다. 접근에 하한 제약이 없다
    range_max = 8.22       원뿔 반각 12.15 deg, net_radius 1.77
    스폰 시 |p_att - p_fin| = 22.6   <- 사거리 밖에서 시작한다

가까울수록 공격자의 실현 가능 회피 집합이 작아져 **최악 케이스 포획**이
쉬워진다. 따라서 목표점은 예측 그물 중심 `nc` 이고, 제어는 거기로의 임계감쇠
추종이다. 이득은 `tau_deploy` 하나에서 유도한다 -- **튜닝 축이 아니다**
(docs/51 §2.2). 값을 찾기 시작하면 §3.3 의 하한 논리가 깨진다.

이 제어기는 **최적이 아니다.** 묻는 것은 "최적 이동이 얼마나 좋은가" 가 아니라
"이동이 조금이라도 사슬을 바꾸는가" 다. 그래서 음성 결과는 하한으로만 읽는다.
"""
from __future__ import annotations

import numpy as np

__all__ = ["mobile_finisher_accel", "apply_mobility", "MOBILITY_OFF",
           "MOBILE_A_MAX", "MOBILE_V_MAX"]

MOBILITY_OFF = 0.0          # a_max = 0 -> 고정. 기존 모든 결과가 난 조건

# ── docs/51 §2.1 선언 (튜닝 축이 아니다) ────────────────────────────────────
#   limiter 와 **같은 값**을 쓴다. 새 숫자를 만들지 않고, 동시에 이동에 가장
#   관대한 능력을 준다 -- 음성 결과가 하한으로만 읽히므로(§3.3) 관대할수록
#   음성이 강해진다.
MOBILE_A_MAX = 15.413175542581453      # = scn.limiter.a_max
MOBILE_V_MAX = 25.945951115215127      # = v_nominal (limiter v_max 와 같다)


def mobile_finisher_accel(p_fin, v_fin, p_att, v_att, *, tau: float,
                          a_max: float) -> np.ndarray:
    """예측 그물 중심으로의 임계감쇠 추종. `a_max <= 0` 이면 정확히 0 을 낸다.

    입력은 전부 **관측 가능량**이다 (`p_fin`,`v_fin`,`p_att`,`v_att` 는 모두
    관측 벡터에 실려 있다 -- docs/48 §13). 특권 정보를 쓰지 않는다 (P71).

    `nc` 는 `env._net_center` 와 **같은 식**이다. 두 곳에 적지 않으려고 인자로
    받지 않고 여기서 같은 형태로 계산한다 -- 호출부가 `env._net_center` 를
    넘겨도 되게 `net_center` 인자를 열어 둔다.
    """
    a_max = float(a_max)
    if not (a_max > 0.0):                      # 고정 포획기 (기본)
        return np.zeros(3, np.float32)
    p_f = np.asarray(p_fin, float)
    v_f = np.asarray(v_fin, float)
    nc = np.asarray(p_att, float) + np.asarray(v_att, float) * float(tau)
    # 임계감쇠: k_p = 1/tau^2, k_d = 2/tau  (dt 무관, 튜닝 축 아님)
    kp, kd = 1.0 / (tau * tau), 2.0 / tau
    a = kp * (nc - p_f) - kd * v_f
    n = float(np.linalg.norm(a))
    if n > a_max:                              # 상한을 **방향 보존**으로 건다
        a = a * (a_max / n)                    # (성분별 클립은 방향을 바꾼다)
    return np.asarray(a, np.float32)


# ── ★ 이동성은 세 곳에 걸려 있다 ────────────────────────────────────────────
def apply_mobility(env, a_max: float = MOBILE_A_MAX,
                   v_max: float = MOBILE_V_MAX) -> dict:
    """포획기 이동성을 **한 번에** 켠다. 세 값이 갈라지지 않게 하는 유일한 지점.

    2026-08-05 에 실제로 밟은 함정이라 여기 적어 둔다. `env.py` 의 병진 명령만
    풀고 돌렸더니 60 스텝에 0.40 밖에 못 움직였다. 이유는 **백엔드 클램프**가
    따로 있었기 때문이다:

        FinisherSpec.a_max            <- 명령 (docs/51 에서 새로 추가)
        train.limits.finisher_a_max   <- 백엔드 가속 클램프, 기본 1.0
        train.limits.finisher_v_max   <- 백엔드 속도 클램프, 기본 1.0

    뒤의 둘은 "env 가 어차피 a=0 을 주므로 무의미" 라는 근거로 1.0 이 박혀
    있었다(`params.py` 주석). 명령을 푸는 순간 그 근거가 사라지고 **조용한
    스로틀**이 된다 -- 이 리포가 반복해서 겪은 '선언 그림자' 와 같은 모양이다
    (docs/48 정정 3 · 결함 2).

    그래서 켜는 경로를 하나로 묶고, 어긋나면 **예외를 던진다**. 조용히 클램프
    되는 것보다 죽는 게 낫다.
    """
    import dataclasses

    a_max, v_max = float(a_max), float(v_max)
    fin = [a for a in env.backend.agents if a.role == "finisher"]
    if len(fin) != 1:
        raise ValueError(f"finisher 가 1 기가 아니다: {len(fin)}")
    f = fin[0]
    # 1) 명령 상한 (env 가 mobile_finisher_accel 에 넘기는 값)
    env.sc.__dict__["finisher"] = dataclasses.replace(env.sc.finisher, a_max=a_max)
    # 2)+3) 백엔드 클램프. 명령보다 작으면 조용히 목이 졸린다
    f.limits = dataclasses.replace(f.limits, a_max=max(a_max, f.limits.a_max),
                                   v_max=max(v_max, f.limits.v_max))
    if f.limits.a_max + 1e-9 < a_max:
        raise ValueError(f"백엔드 가속 클램프({f.limits.a_max})가 명령 상한({a_max})보다 낮다")
    return {"a_max": a_max, "v_max": v_max,
            "backend_a_max": float(f.limits.a_max),
            "backend_v_max": float(f.limits.v_max)}


SLEW_UNLIMITED = 1.0e6      # rad/s. dt=0.05 -> 스텝당 5e4 rad = 사실상 무한


def apply_slew_limit(env, omega_max: float) -> dict:
    """조준 슬루 속도 상한을 바꾼다 (무한 슬루 반사실, docs/51 §9).

    `a_max` 와 **같은 함정**이 여기도 있다 -- `omega_max` 는 두 곳에 있다:

        FinisherSpec.omega_max          <- 선언 (params.py 에서 ASSUMED 2.0)
        KinematicLimits.omega_max       <- ★ 실제로 물리는 곳 (analytic.py:130)

    백엔드가 `_slew(e, e_cmd, omega_max*dt)` 로 회전을 깎으므로 **뒤엣것만이
    실효**다. 앞엣것만 바꾸면 아무 일도 안 일어난다. 그래서 둘을 같이 건드리고
    실효값을 돌려준다 -- 호출부가 무엇이 실제로 걸렸는지 볼 수 있게.

    묻는 것: 이동이 나빴던 것이 **슬루 제한 때문인가**. 같은 궤적을 무한 슬루로
    재생해서 회복되면 그렇고, 안 되면 docs/51 §8.3 의 기전 서술이 틀린 것이다.
    """
    import dataclasses

    omega_max = float(omega_max)
    fin = [a for a in env.backend.agents if a.role == "finisher"]
    if len(fin) != 1:
        raise ValueError(f"finisher 가 1 기가 아니다: {len(fin)}")
    f = fin[0]
    env.sc.__dict__["finisher"] = dataclasses.replace(env.sc.finisher,
                                                      omega_max=omega_max)
    f.limits = dataclasses.replace(f.limits, omega_max=omega_max)
    return {"omega_max": omega_max, "backend_omega_max": float(f.limits.omega_max),
            "deg_per_step": float(np.degrees(omega_max * env.dt))}
