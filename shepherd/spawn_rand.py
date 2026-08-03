"""초기조건(스폰) 랜덤화 — 주장 등급의 FIXED_CONDITION 천장을 걷어내는 배선.

문제 (docs/36 §4)
-----------------
`sim/analytic.py` L97-107 은 **결정론적 리셋**이다:

    def reset(self, seed):
        \"\"\"Deterministic reset to (p0, v0, e0). seed only seeds an (unused-by-
        default) RNG so a later env can add seeded jitter without breaking this
        backend's determinism contract.\"\"\"

즉 훅은 애초에 이 용도로 남겨져 있었고, 한 번도 쓰이지 않았다. `make_env.py` 는
공격자를 `p0 = [24, 0, 0]`, `v0 = [-speed, 0, 0]` 로 **축 위에 정면으로** 고정 배치한다.
결과적으로 **모든 에피소드의 초기조건이 비트 단위로 같다.** 에피소드 간 유일한
변동은 viability 샘플러의 `step_seed` 뿐이다.

이건 값 문제가 아니라 **주장 등급 상한 문제**다. 클레임 거버넌스 사다리
(FIXED_CONDITION -> MULTI_RESET -> DISTRIBUTION_LEVEL)에서 스폰 랜덤화 없이는
FIXED_CONDITION 을 영원히 못 벗어난다.

채택한 해법 -- p0/v0/e0 재기입 (프록시조차 불필요)
--------------------------------------------------
`AgentKin.p0/v0/e0` 는 평범한 dataclass 필드이고 `reset()` 은 거기서 복사한다.
`layout.adversary_p0/v0` 는 **생성 시점 이후 아무도 읽지 않는다**(env.py 에서
소비되지 않음을 확인). 따라서 리셋 직전에 공격자 AgentKin 의 초기상태를 다시 쓰면
동결 파일을 한 줄도 건드리지 않고 스폰이 바뀐다.

    apply_spawn(env, draw)      # AgentKin.p0/v0/e0 재기입 (+ layout 동기화)
    env.reset(seed)             # 동결 reset 이 그 값을 복사한다

**공격자만 흔든다.** limiter 는 건드리지 않는다 -- `layout.limiter_p0` 가
hold_position 기준선이자 COMA 반대사실이라(env.py `cf[i] = layout.limiter_p0[i]`)
스폰을 흔들면 기준선과 실제 배치가 어긋난다. finisher 도 건드리지 않는다 --
`spawn_bank.check_frame` 이 apex==(2,0,0) 를 STRICT 로 강제하고 v_shot 콘의
꼭짓점이다. 게다가 **우리 배치는 설계 선택이고 위협이 분포**라는 것이
방어 가능한 프레이밍이다(docs/36 §5).

선언 규율
---------
`SpawnSpec` 의 모든 값은 **선언값이며 결과를 본 뒤 바꾸지 않는다**(착취 방지 규칙과
동일 정신). 기본 범위의 근거는 `SpawnSpec` docstring 에 적었다. `enabled=False` 는
동결 경로와 bit-identical 이며 P19 가 강제한다.

torch-free.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

import numpy as np

__all__ = ["SpawnSpec", "SpawnDraw", "derive_spawn_u", "sample_spawn",
           "apply_spawn", "spawn_for_episode", "randomized_config"]

_EPS = 1e-12


# --------------------------------------------------------------------- spec ---
@dataclass(frozen=True)
class SpawnSpec:
    """공격자 초기조건 분포. **전부 선언값.**

    기본값 근거 (임의로 고른 숫자가 아니라는 것이 요점):

    `dx = 2.0 m`
        회랑축 방향 ±2 m -> x in [22, 26]. 도달 시간을 ±0.1 s 흔든다
        (v=20 기준). 정책이 "몇 스텝째에 무엇을 한다"를 외우지 못하게 하는
        최소 폭이며, 회랑 기하(ring x=8, finisher x=2)를 바꾸지 않는다.

    `r_lat = 5.0 m`  (= `ring_radius`)
        **방어 개구 전체.** limiter 링 반경과 같게 잡는다 -- "위협은 방어 개구
        어디로든 올 수 있다"는 위협모형 진술이지 튜닝값이 아니다. 이보다 크면
        공격자가 링 바깥으로 접근해 문제의 성격이 바뀌고(포위가 아니라 우회),
        이보다 작으면 링 일부가 영영 안 쓰인다. **경계값이 자연스러운 선언이다.**
        면적 균일 샘플링(sqrt(u))이라 중심 과표집이 없다.

    `psi = 0.0 rad`
        초기 속도는 표적 정조준. 횡오프셋 자체가 이미 방위각 다양성을 만든다
        (r_lat=5, x=24 -> atan(5/24) = 0.21 rad = 12도). 그 위에 각오차를 더하는
        것은 2차 효과이고 동결 공격자의 호밍이 몇 스텝 안에 지운다. 축은 열어 둔다.

    `speed_frac = 0.0`
        초기 속력 지터. 동결 공격자는 `v_nominal` 로 되돌아가 조절하므로
        과도현상일 뿐이다. **의미 있는 속도 축은 `v_nominal` 자체**이고 그건
        config 레벨(`randomized_config`)에서 다룬다 -- docs/36 C-2(FPV 스펙) 대기.
    """
    dx: float = 2.0             # m. 회랑축 방향 ±
    r_lat: float = 5.0          # m. y-z 횡오프셋 반경 (면적 균일)
    psi: float = 0.0            # rad. 초기 속도 방향 각오차 (0 = 표적 정조준)
    speed_frac: float = 0.0     # 초기 속력 비율 지터 (0 = v_nominal)
    enabled: bool = True
    seed_ns: str = "m4_spawn"

    def label(self) -> str:
        if not self.enabled:
            return "SPAWN_FIXED"
        return (f"SPAWN(dx={self.dx:g},r_lat={self.r_lat:g}"
                f",psi={self.psi:g},sf={self.speed_frac:g})")


@dataclass(frozen=True)
class SpawnDraw:
    """한 에피소드의 초기조건. `p`,`v`,`e` 는 백엔드에 그대로 기입된다."""
    p: Tuple[float, float, float]
    v: Tuple[float, float, float]
    e: Tuple[float, float, float]
    u: Tuple[float, ...]          # 사용된 균일난수 (감사용)


# ------------------------------------------------------------- determinism ---
def derive_spawn_u(seed: int, episode: int, ns: str = "m4_spawn",
                   k: int = 6) -> Tuple[float, ...]:
    """(seed, episode) -> [0,1) 균일난수 k개. SHA-256 기반.

    파이썬 `hash()` 금지 -- 프로세스마다 salt 가 달라 재현 불가
    (`attacker_ladder.derive_phase` 와 동일 규약).
    """
    out = []
    for i in range(int(k)):
        h = hashlib.sha256(
            f"{ns}|{int(seed)}|{int(episode)}|{i}".encode()).digest()
        out.append(int.from_bytes(h[:8], "big") / 2 ** 64)
    return tuple(out)


# ----------------------------------------------------------------- sampling ---
def _orthonormal_pair(axis: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """axis 에 직교하는 정규직교 2벡터. 결정론적(임의 seed 사용 안 함)."""
    a = np.asarray(axis, float)
    n = np.linalg.norm(a)
    a = a / n if n > _EPS else np.array([1.0, 0.0, 0.0])
    ref = np.array([0.0, 0.0, 1.0]) if abs(a[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = np.cross(a, ref); u /= max(np.linalg.norm(u), _EPS)
    w = np.cross(a, u);   w /= max(np.linalg.norm(w), _EPS)
    return u, w


def sample_spawn(spec: SpawnSpec, *, base_p: Sequence[float],
                 target: Sequence[float], speed: float,
                 seed: int, episode: int) -> SpawnDraw:
    """순수 함수. 동일 (spec, seed, episode) -> 동일 결과.

    `spec.enabled=False` 면 `base_p` / 표적 정조준 / `speed` 그대로 (동결 경로).
    """
    # u[0] 축방향 | u[1] 횡반경 | u[2] 횡방위 | u[3] 콘방위 | u[4] 콘극각 | u[5] 속력
    # **인덱스를 공유하지 않는다** -- 축끼리 상관이 생기면 분포가 무너진다.
    base = np.asarray(base_p, float)
    tgt = np.asarray(target, float)
    u = derive_spawn_u(seed, episode, spec.seed_ns, 6)

    if not spec.enabled:
        # 동결 경로 재현: p0=[adv_x,0,0], v0=[-speed,0,0], e0=[-1,0,0]
        d = tgt - base
        n = np.linalg.norm(d)
        dir0 = d / n if n > _EPS else np.array([-1.0, 0.0, 0.0])
        v0 = float(speed) * dir0
        return SpawnDraw(tuple(base), tuple(v0), tuple(dir0), u)

    # --- 위치: 축방향 ± dx, 횡방향 면적균일 원판 ---------------------------
    axis = tgt - base
    na = np.linalg.norm(axis)
    axis = axis / na if na > _EPS else np.array([-1.0, 0.0, 0.0])
    e1, e2 = _orthonormal_pair(axis)

    dx = (2.0 * u[0] - 1.0) * spec.dx
    rad = spec.r_lat * math.sqrt(u[1])          # sqrt -> 면적 균일
    ang = 2.0 * math.pi * u[2]
    p = base - axis * dx + e1 * (rad * math.cos(ang)) + e2 * (rad * math.sin(ang))
    #        ^ -axis*dx: 양수 dx = 표적에서 더 멀리 (직관 일치)

    # --- 속도: 표적 정조준 + psi 각오차, 속력 speed_frac 지터 --------------
    d = tgt - p
    nd = np.linalg.norm(d)
    dir_t = d / nd if nd > _EPS else axis
    if spec.psi > 0.0:
        f1, f2 = _orthonormal_pair(dir_t)
        cone_ang = 2.0 * math.pi * u[3]
        # 입체각 균일: cos(theta) in [cos(psi), 1]
        ct = 1.0 - u[4] * (1.0 - math.cos(spec.psi))
        st = math.sqrt(max(0.0, 1.0 - ct * ct))
        dir_t = (ct * dir_t
                 + st * (math.cos(cone_ang) * f1 + math.sin(cone_ang) * f2))
        dir_t /= max(np.linalg.norm(dir_t), _EPS)
    sp = float(speed) * (1.0 + (2.0 * u[5] - 1.0) * spec.speed_frac)
    v = sp * dir_t
    return SpawnDraw(tuple(p), tuple(v), tuple(dir_t), u)


# ------------------------------------------------------------------ apply ---
def apply_spawn(env, draw: SpawnDraw):
    """공격자 AgentKin 의 초기상태를 재기입한다. **`env.reset()` 전에 호출.**

    `env.backend` 가 `AdversaryOverrideBackend` 로 감싸져 있어도 `__getattr__`
    위임 덕분에 그대로 동작한다.
    """
    agent = env.backend.by_name(env.adversary_id)
    agent.p0 = list(map(float, draw.p))
    agent.v0 = list(map(float, draw.v))
    agent.e0 = list(map(float, draw.e))
    # layout 동기화 -- env.py 는 생성 후 읽지 않지만 어긋난 상태를 남기지 않는다
    env.layout.adversary_p0 = list(map(float, draw.p))
    env.layout.adversary_v0 = list(map(float, draw.v))
    return env


def spawn_for_episode(env, spec: SpawnSpec, *, seed: int, episode: int,
                      base_p: Optional[Sequence[float]] = None,
                      speed: Optional[float] = None) -> SpawnDraw:
    """샘플 + 적용을 한 번에. 학습 루프에서 `env.reset()` 직전에 부른다.

    `base_p` 기본값은 **최초 호출 시점의** 공격자 p0 를 기억해 쓴다 -- 이미 적용된
    스폰 위에 또 적용해서 랜덤워크가 되는 것을 막는다.
    """
    if base_p is None:
        if not hasattr(env, "_spawn_base_p"):
            env._spawn_base_p = list(map(float, env.backend.by_name(env.adversary_id).p0))
        base_p = env._spawn_base_p
    if speed is None:
        speed = float(env.sc.adversary.speed)
    draw = sample_spawn(spec, base_p=base_p, target=env.layout.target,
                        speed=speed, seed=seed, episode=episode)
    apply_spawn(env, draw)
    return draw


# ------------------------------------------------------- config-level axis ---
def randomized_config(cfg: dict, *, seed: int, episode: int,
                      att_speed_range: Optional[Tuple[float, float]] = None,
                      a_att_range: Optional[Tuple[float, float]] = None,
                      tau_range: Optional[Tuple[float, float]] = None,
                      ns: str = "m4_cfg") -> dict:
    """에피소드마다 env 를 재구성해야 하는 축(속도/가속/tau)의 딥카피 헬퍼.

    **범위 인자에 기본값을 주지 않는다** -- 선언되지 않은 범위로 실수로 도는 것을
    막기 위해서다. `None` 이면 그 축은 건드리지 않는다.

    `att_speed` / `a_att_max` 는 docs/36 C-2(FPV 스펙시트) 대기 상태이므로
    범위를 여기 하드코딩하지 않는다. `tau` 는 발사 설계점에서 파생되므로
    (docs/33 §4) 독립 sweep 이 아니라 설계점 선택으로 다루는 것이 원칙이고,
    이 인자는 폴백이다.
    """
    import copy
    out = copy.deepcopy(cfg)
    u = derive_spawn_u(seed, episode, ns, 3)
    if att_speed_range is not None:
        lo, hi = att_speed_range
        out["physics"]["att_speed"] = float(lo + u[0] * (hi - lo))
    if a_att_range is not None:
        lo, hi = a_att_range
        out["physics"]["a_att_max"] = float(lo + u[1] * (hi - lo))
    if tau_range is not None:
        lo, hi = tau_range
        out["physics"]["tau_deploy"] = float(lo + u[2] * (hi - lo))
    return out
