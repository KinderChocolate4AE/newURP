"""위협 등급 관측 확장 — 정책이 regime 을 구분할 수 있게 한다.

왜 필요한가 (docs/32 [D]-④ 의 갱신된 형태)
--------------------------------------------
M4 는 에피소드마다 위협 등급을 뽑는다(`m4_config.THREAT_BRACKET`):
`a_att ∈ [11, 78]`, `att_speed ∈ [8, 30]`. 그리고 그 축은 **명제 N 의 경계를
가로지른다** (a* = 2ρ/τ² = **39.33** m/s²; 44.4 는 rho=2.0 시절 고아값이다):

    a_att < 39.33  ->  w = 0.5*a*tau^2 < rho  ->  조향 없이도 포획된다
    a_att > 39.33  ->  w > rho               ->  조향이 필요하다

즉 **같은 상태에서 최적 행동이 위협 등급에 따라 달라진다.** MAPPO 액터는
단일 프레임 MLP(순환 없음)라 관측만으로 a_att 를 추론할 수 없다. 관측에 없으면
정책은 regime-blind 가 되어 "평균적으로 무난한" 해로 수렴하고, 그러면
docs/30 §6 의 *"모드 중재를 위협의 함수로 배운다"* 주장이 성립하지 않는다.

이게 반칙이 아닌 이유
--------------------
숨은 환경 파라미터를 훔쳐보는 것이 아니라 **시스템이 실제로 하는 분류**다.
C-UAS 체계는 표적을 탐지·분류한다(Pliska RA-L 의 탐지·추적 파이프라인,
Drones 10(6):420 의 YOLO 분류기 mAP@0.5=0.96). 플랫폼 등급을 아는 것은
설계 전제이지 특권 정보가 아니다.

**한계는 명시한다**: 여기서는 분류가 *무오차*다. 실제 분류는 노이즈가 있고,
오분류 하 강건성은 future work 다. 이 한계는 우리에게 **유리한** 쪽이므로
논문에 반드시 적어야 한다.

정규화
------
브래킷으로 [-1, 1] 선형 사상한다. 브래킷 밖 값은 클립하지 않고 그대로 둔다
(브래킷 밖을 쓰는 것은 일반화 평가이고, 그때 관측이 범위를 넘는 것이 정상이다).

torch-free.
"""
from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple

import numpy as np
from gymnasium import spaces

__all__ = ["ThreatObsEnv", "attach_threat_obs", "threat_features"]

_EPS = 1e-12


def threat_features(values: Sequence[float],
                    bracket: Sequence[Tuple[float, float]]) -> np.ndarray:
    """브래킷 -> [-1, 1] 선형 사상. 클립하지 않는다."""
    out = []
    for v, (lo, hi) in zip(values, bracket):
        span = max(float(hi) - float(lo), _EPS)
        out.append(2.0 * (float(v) - float(lo)) / span - 1.0)
    return np.asarray(out, np.float32)


class ThreatObsEnv:
    """관측 벡터 뒤에 위협 등급 특징을 붙인다. 그 외는 전부 inner 로 위임.

    `enabled=False` 면 관측을 건드리지 않는다 -- ablation(regime-blind) 축이다.
    **이 ablation 이 §6 의 핵심 대조군이다**: 위협을 못 보는 정책이 무엇을
    잃는지가 곧 "위협의 함수로 중재한다"는 주장의 증거다.
    """

    def __init__(self, inner, features: Sequence[float],
                 bracket: Sequence[Tuple[float, float]], *, enabled: bool = True):
        self.inner = inner
        self.bracket = [tuple(map(float, b)) for b in bracket]
        self._enabled = bool(enabled)
        self.set_threat(features)

    # ------------------------------------------------------------------ api
    def set_threat(self, features: Sequence[float]):
        self._raw = tuple(float(x) for x in features)
        self._feat = (threat_features(self._raw, self.bracket) if self._enabled
                      else np.zeros(0, np.float32))
        return self

    @property
    def n_extra(self) -> int:
        return int(self._feat.shape[0])

    def _aug(self, obs: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        if not self._enabled:
            return obs
        return {k: np.concatenate([np.asarray(v, np.float32), self._feat]).astype(np.float32)
                for k, v in obs.items()}

    def reset(self, seed=None, options=None):
        obs, infos = self.inner.reset(seed=seed, options=options)
        return self._aug(obs), infos

    def step(self, actions):
        out = self.inner.step(actions)
        obs, rew, term, trunc, infos = out
        return self._aug(obs), rew, term, trunc, infos

    def observation_space(self, agent):
        sp = self.inner.observation_space(agent)
        if not self._enabled:
            return sp
        n = int(sp.shape[0]) + self.n_extra
        lo = np.concatenate([sp.low, np.full(self.n_extra, -np.inf, np.float32)])
        hi = np.concatenate([sp.high, np.full(self.n_extra, np.inf, np.float32)])
        return spaces.Box(lo.astype(np.float32), hi.astype(np.float32), (n,), np.float32)

    def state(self):
        """중앙 크리틱용 상태에도 같은 특징을 붙인다 (CTDE 일관성)."""
        s = np.asarray(self.inner.state(), np.float32)
        if not self._enabled:
            return s
        return np.concatenate([s, self._feat]).astype(np.float32)

    def __getattr__(self, name):
        return getattr(self.__dict__["inner"], name)


def attach_threat_obs(env, *, a_att: float, att_speed: float,
                      bracket: Optional[Sequence[Tuple[float, float]]] = None,
                      enabled: bool = True) -> ThreatObsEnv:
    """`m4_config.THREAT_BRACKET` 순서(a_att, att_speed)를 기본으로 감싼다."""
    if bracket is None:
        from shepherd.m4_config import THREAT_BRACKET
        bracket = (THREAT_BRACKET["physics.a_att_max"],
                   THREAT_BRACKET["physics.att_speed"])
    return ThreatObsEnv(env, (a_att, att_speed), bracket, enabled=enabled)
