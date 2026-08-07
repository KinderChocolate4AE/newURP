"""공격자 사다리 A1–A3 + 손실회피 lambda (docs/27 · docs/28).

WHY
---
논문 명제(docs/28)는 "비손실 격추는 손실 회피형 적응 공격자 위에서 위협-조향으로
성립한다"이다. 따라서 **공격자 난이도가 결과 그림의 x축**이고, 그 축은 두 개의
서로 다른 것으로 이루어진다:

  lambda (손실 회피)   위협을 얼마나·얼마나 미리 피하는가.  현행 하드코딩 = (1.0, 1.0)
                       = 최대 크기 · 최소 예견.  lambda=0 -> 가미카제(음성 대조군).
  행동 등급             A1 반응형 -> A2 지속 회피 + 편대 라우팅 -> A3 발사 유도.

이 둘을 섞으면 안 된다(docs/28 §6): 전자는 "겁의 크기", 후자는 "계획 능력"이다.

단조성(NESTING) 규약
-------------------
A_{k+1}은 파라미터 특수화만으로 A_k를 bit-exact 재현해야 한다. 그래야 "붕괴 지점"에
순서가 생긴다. 이 파일은 두 경로로 그것을 보장한다:

  1. `A1_SPEC` 은 기존 `scripted_adversary_action` 에 **문자 그대로 위임**한다.
     (기본값을 잘 맞춰서가 아니라, 같은 함수를 그대로 호출해서.)
  2. 일반 구현 `_general_action` 은 extras 가 전부 꺼지면 A1 과 동일한 산술을
     동일한 순서로 수행한다. tests/test_attacker_ladder.py P1b 가 1 과 2 를
     대조해 이 충실성을 검증한다 (그래서 P1b 가 자명하지 않다).

`shepherd/agents/adversary.py` 는 건드리지 않는다 -- 그것이 A1 의 정의이고,
변경하면 과거 모든 결과가 무효가 된다.

torch-free. 순수 numpy.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from typing import Optional

import numpy as np

from shepherd.agents.adversary import scripted_adversary_action

__all__ = [
    "AttackerSpec", "A1_SPEC", "LAMBDA_PRESETS", "make_attacker",
    "is_a1_equivalent", "derive_phase", "with_lambda",
]

_EPS = 1e-12

# 사다리 전용 kwarg -- A1 위임 시 걸러낸다. 새 축을 추가하면 **여기에도 추가**해야
# P1(동결 등가)이 깨지지 않는다.
_LADDER_ONLY_KW = ("t", "phase", "v_shot_soft", "v_max")

# 현행 env.py 가 하드코딩으로 넘기는 값 (docs/28 §3). lambda 의 기준점.
_REF_LAM_GAIN = 1.0     # 반발 크기 배수: a_rep = a_att_max * lam_gain * (1 + strength)
_REF_LAM_RANGE = 1.0    # 반발 발동 거리 배수 (= env 가 넘기는 repel_margin)
_REF_DODGE_AMP = 1.8    # 커밋 후 횡회피 진폭 (adversary.py 기본)


def _unit(v, fallback=None):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    if n < _EPS:
        return np.zeros(3) if fallback is None else np.asarray(fallback, float)
    return v / n


# --------------------------------------------------------------------- spec ---
@dataclass(frozen=True)
class AttackerSpec:
    """공격자 한 점(層 × lambda × 행동 파라미터).

    행동 파라미터는 **선언 후 고정**한다 (docs/27 §4 규칙 2). 최적화하지 않는다 --
    최적화되는 층은 A4 하나뿐이며 falsifier 규율 아래에서만 한다.
    """
    level: str = "A1"                  # "A1" | "A2" | "A3"

    # --- lambda: 손실 회피 (조기 손실에 의한 임무 실패 회피) ------------------
    lam_gain: float = _REF_LAM_GAIN    # 0.0 = 가미카제(위협 무시)
    lam_range: float = _REF_LAM_RANGE  # >1.0 = 예견적 회피 (더 멀리서 피함)

    # --- A2: 지속 회피 + 편대 라우팅 -----------------------------------------
    jink_amp: float = 0.0              # x a_lat_max. 커밋 전 지속 횡진동
    jink_freq: float = 1.5             # Hz
    jink_terminal_r: float = 3.0       # m. 목표 이 반경 안에서는 회피 중단(종말 유도)
    route_gain: float = 0.0            # x a_lat_max. angular-gap 회피 편향 (docs/60 §3.2)
    homing_gain: float = 4.0           # 1/s. 횡속도 감쇠 = 회피 후 시선축 복귀
                                       # 값의 근거: params.py `adversary.fwd_gain`(=4.0,
                                       # A1 의 비준된 전진 P-게인)을 그대로 상속. 성능을
                                       # 보고 고른 값이 아니므로 새 자유도가 0 이다.

    # --- v3 (docs/60): 종축 속도 프로파일 + 감지 반경. 전부 기본 off = bit-exact --
    sprint_range: float = 0.0          # m. d_asset <= 이 값 -> v_ref = sprint_frac*v_max
    sprint_frac: float = 1.0           # 능력(v_max) 대비 스프린트 참조속도 비율
    slowdown_range: tuple = (0.0, 0.0) # m (far, near). near < d_asset <= far 에서 저속.
                                       # "기만" 기전 주장 금지 (docs/60 §2.1) -- 비정상
                                       # 종축 속도 프로파일일 뿐이다
    slowdown_frac: float = 1.0         # v_nominal 대비 저속 구간 참조속도 비율
    sense_range: float = float("inf")  # m. limiter 감지 반경 (route 항의 관측 한계.
                                       # inf = legacy 전지 관측 경로)

    # --- A3: 발사 유도 -------------------------------------------------------
    bait_gain: float = 0.0             # x a_lat_max. 횡속도 억제 강도(얌전해 보이기)
    bait_privileged: bool = False      # True = v_shot 직독(상한/positive control)
    bait_threshold: float = 0.5        # readiness 이 값을 넘으면 유도 개시
    bait_range: tuple = (4.0, 16.0)    # m. finisher 로부터 발사가 그럴듯한 사거리대
    bait_enclosure_r: float = 3.0      # x kill_radius. 포위도 판정 반경

    # --- 재현성 ---------------------------------------------------------------
    seed: int = 0                      # jink 위상 유도용 (derive_seed 규약)
    label: str = ""

    def name(self) -> str:
        if self.label:
            return self.label
        return (f"{self.level}(lam={self.lam_gain:g}/{self.lam_range:g}"
                f",jink={self.jink_amp:g},route={self.route_gain:g})")


A1_SPEC = AttackerSpec(level="A1", label="A1")

# lambda 프리셋. 현행(하드코딩) = LAM_REF. **LAM_ZERO 는 현실 위협이 아니라
# C1 기전 증명용 음성 대조군이다** (docs/28 §3.2).
LAMBDA_PRESETS = {
    "LAM_ZERO":  (0.0, 1.0),   # 가미카제 -- 위협 무시. 음성 대조
    "LAM_LOW":   (0.25, 1.0),
    "LAM_MID":   (0.5, 1.5),
    "LAM_REF":   (1.0, 1.0),   # <- 현행 env 하드코딩. 최대 크기 · 최소 예견
    "LAM_ANTIC": (1.0, 2.5),   # 같은 크기, 예견적 (합리적 손실회피 조종자)
}


def is_a1_equivalent(spec: AttackerSpec) -> bool:
    """A1 위임 경로를 쓸 수 있는가 (모든 extras off + lambda 기준점)."""
    return (spec.lam_gain == _REF_LAM_GAIN and spec.lam_range == _REF_LAM_RANGE
            and spec.jink_amp == 0.0 and spec.route_gain == 0.0
            and spec.bait_gain == 0.0
            and spec.sprint_range == 0.0 and spec.slowdown_range[0] == 0.0)


def derive_phase(seed: int, episode: int) -> float:
    """jink 위상 in [0, 2pi). SHA-256 기반 -- 파이썬 hash() 금지
    (프로세스마다 salt 가 달라 재현 불가; c1_governance 규약과 동일 정신)."""
    h = hashlib.sha256(f"attacker_jink|{int(seed)}|{int(episode)}".encode()).digest()
    return 2.0 * np.pi * (int.from_bytes(h[:8], "big") / 2 ** 64)


# ------------------------------------------------------------------ A2 terms ---
def _jink_accel(spec, *, fwd, t, phase, a_lat_max, committed, d_target):
    """커밋 전 지속 횡진동. 전진 성분을 갉아먹지 않도록 fwd 에 직교하는 평면에서만.

    커밋 후에는 끄고 A1 의 dodge 항에 맡긴다 -- 두 항이 겹치면 커밋 후 회피 강도가
    층마다 달라져서 lambda 축과 행동 축이 교란된다.

    **종말 게이트** (`jink_terminal_r`): 목표 근방에서는 회피를 멈춘다. 유도 문헌의
    표준 거동이고(종말 유도 구간에서 회피 기동은 명중을 훼손한다), 물리적으로도
    맞다 -- 끝까지 지그재그하면 표적을 빗나간다. 이 항이 없으면 A2 가 무방어
    상대로도 침투를 못 한다(P2 가 실제로 이것을 잡았다: min_dist 1.26 > 1.0).
    튜닝이 아니라 거동 정의이며, 착취 방지 규칙 2 에 따라 선언 후 고정한다.
    """
    if spec.jink_amp == 0.0 or committed:
        return np.zeros(3)
    if spec.jink_terminal_r > 0.0 and d_target <= spec.jink_terminal_r:
        return np.zeros(3)
    ref = np.array([0.0, 0.0, 1.0]) if abs(fwd[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = _unit(np.cross(fwd, ref), [0.0, 1.0, 0.0])
    w = _unit(np.cross(fwd, u), [0.0, 0.0, 1.0])
    ang = 2.0 * np.pi * spec.jink_freq * float(t) + float(phase)
    d = np.cos(ang) * u + np.sin(ang) * w
    return spec.jink_amp * a_lat_max * d


def _route_accel(spec, *, p_att, v_att, fwd, limiters, kill_radius, repel_margin,
                 a_lat_max, d_target):
    """**instantaneous transverse angular-gap heuristic** (docs/60 §3.2, r3).

    감지된 limiter 들을 진행축 수직 평면에 사영해 각 limiter 가 가리는 각도
    구간(blockage)을 만들고, 가장 넓은 free arc 의 중점 방향으로 횡가속을 낸다.
    probe-circle parametrization (구 route_probe) 은 폐지 -- 신규 상수 없음.

    A1 의 반발(`a_rep`)과 다르다: 저것은 반발 반경에 닿아야 켜지는 접촉 회피이고,
    이것은 개별 구가 아니라 **formation blockage** 를 보고 미리 도는 계획 능력이다.

    주의 (r3 범위 제한): 현재 횡단면의 순간 기하만 본다 -- 종축 거리는 blockage
    반각에 들어가지 않는다. "physical widest escape gap" 이 아니다.

    r_block = repel_margin * lam_range * kill_radius 는 물리적 동일성 주장이
    아니라 신규 자유도를 더하지 않기 위한 nominal modeling choice (docs/60 §3.2).

    거동 정의 (선언 후 고정, jink_terminal_r 전례): 감지 0 -> 0 · 전 원주 봉쇄
    -> 0 (repel 만 남음) · 최대 호 동률 -> 횡속도 bearing 에 가까운 호, 그것도
    동률이면 bearing 0 쪽 · 종말 게이트 상속 · 난수/시간 무관 (결정론).
    """
    if spec.route_gain == 0.0 or limiters is None:
        return np.zeros(3)
    if spec.jink_terminal_r > 0.0 and d_target <= spec.jink_terminal_r:
        return np.zeros(3)                       # 종말 구간에서는 우회도 중단
    L = np.asarray(limiters, float).reshape(-1, 3)
    ahead = [c for c in L
             if float((c - p_att) @ fwd) > 0.0                       # 지나친 것 무시
             and float(np.linalg.norm(c - p_att)) <= spec.sense_range]
    if not ahead:
        return np.zeros(3)
    ref = np.array([0.0, 0.0, 1.0]) if abs(fwd[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = _unit(np.cross(fwd, ref), [0.0, 1.0, 0.0])
    w = _unit(np.cross(fwd, u), [0.0, 0.0, 1.0])
    r_block = float(repel_margin) * spec.lam_range * float(kill_radius)

    # blockage 구간 [beta-alpha, beta+alpha] 수집
    spans = []
    for c in ahead:
        rel = c - p_att
        ox, oy = float(rel @ u), float(rel @ w)
        d = float(np.hypot(ox, oy))
        beta = float(np.arctan2(oy, ox))
        alpha = 0.5 * np.pi if d <= r_block else float(np.arcsin(r_block / d))
        spans.append((beta - alpha, beta + alpha))

    # 원주 위 병합: 시작각 정렬 후 +2pi 복제로 wrap 처리
    two_pi = 2.0 * np.pi
    spans = sorted(((s % two_pi, (s % two_pi) + (e - s)) for s, e in spans))
    if sum(e - s for s, e in spans) >= two_pi:
        return np.zeros(3)                       # 자명 전 원주 봉쇄
    merged = []
    for s, e in spans + [(s + two_pi, e + two_pi) for s, e in spans]:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    # 병합 후에도 전 원주가 덮이면 free arc 없음
    if any(e - s >= two_pi for s, e in merged):
        return np.zeros(3)

    # free arc = 인접 병합구간 사이 틈 (첫 바퀴 시작 구간들만 순회하면 충분)
    gaps = []
    for (s0, e0), (s1, _) in zip(merged, merged[1:]):
        if s0 >= two_pi:
            break
        width = s1 - e0
        if width > _EPS:
            gaps.append((width, (e0 + s1) / 2.0 % two_pi))
    if not gaps:
        return np.zeros(3)

    v_lat = np.asarray(v_att, float) - float(np.asarray(v_att, float) @ fwd) * fwd
    ref_bearing = (float(np.arctan2(float(v_lat @ w), float(v_lat @ u)))
                   if float(np.linalg.norm(v_lat)) > _EPS else 0.0)

    def _angdist(a, b):
        d = abs(a - b) % two_pi
        return min(d, two_pi - d)

    # 동률 tie-break: 폭 최대 -> 횡속도 bearing 근접 (결정론)
    _, mid = min(gaps, key=lambda g: (-g[0], _angdist(g[1], ref_bearing)))
    direction = np.cos(mid) * u + np.sin(mid) * w
    return spec.route_gain * a_lat_max * direction


def _bait_readiness(spec, *, p_att, finisher_p, limiters, kill_radius,
                    v_shot_soft=None):
    """"지금 쏠 만해 보이는가" 추정. 두 변형을 **분리해서** 둔다 (docs/27 §2.4).

    A3-privileged   env 의 v_shot_soft 를 직독 -> 베이팅 능력의 **상한**(positive control)
    A3-fair         관측 가능 대리량만 -> 논문 본문의 주 baseline

    합치면 *"현실 공격자는 발사 조건을 추정 못 한다"* 와 *"추정만 되면 무너진다"* 를
    둘 다 말할 수 없게 된다.

    fair 대리량은 노브를 최소로: **발사가 그럴듯한 사거리대 안 ∧ 포위도**. 둘 다
    공격자가 실제로 관측할 수 있는 양이다(finisher 위치, 주변 limiter 배치).
    """
    if spec.bait_privileged and v_shot_soft is not None:
        return float(v_shot_soft)
    d_fin = float(np.linalg.norm(np.asarray(p_att, float)
                                 - np.asarray(finisher_p, float)))
    lo, hi = spec.bait_range
    if not (lo <= d_fin <= hi):
        return 0.0
    if limiters is None:
        return 0.0
    L = np.asarray(limiters, float).reshape(-1, 3)
    if len(L) == 0:
        return 0.0
    R = spec.bait_enclosure_r * kill_radius
    near = sum(1 for c in L if float(np.linalg.norm(p_att - c)) <= R)
    return float(near) / float(len(L))


def _bait_accel(spec, *, p_att, v_att, fwd, finisher_p, limiters, kill_radius,
                a_lat_max, committed, v_shot_soft=None):
    """발사 유도(feint): 포획 가능해 **보이는** 자세로 접근해 발사를 뽑아낸다.

    `K = 1` 에서 **발사를 유도하고 회피하면 그 뒤는 무방비**이므로 유일한 지배
    전략이다. 커밋 후에는 A1 의 dodge 항이 최대 회피를 담당하므로 여기서는 커밋
    **전**만 다룬다.

    기전: 횡속도를 죽여 얌전해 보이게 만든다(= 회피를 스스로 억제). 그 대가로
    실제 회피 여지를 잠시 포기하므로, 유도가 실패하면 공격자가 손해를 본다 --
    공짜 전략이 아니다.

    반환: (가속 기여, 유도중 여부). 유도중이면 호출부가 jink 를 끈다.
    """
    if spec.bait_gain == 0.0 or committed:
        return np.zeros(3), False
    readiness = _bait_readiness(spec, p_att=p_att, finisher_p=finisher_p,
                                limiters=limiters, kill_radius=kill_radius,
                                v_shot_soft=v_shot_soft)
    if readiness < spec.bait_threshold:
        return np.zeros(3), False
    v = np.asarray(v_att, float)
    v_lat = v - float(v @ fwd) * fwd
    n = float(np.linalg.norm(v_lat))
    if n < _EPS:
        return np.zeros(3), True
    return -spec.bait_gain * a_lat_max * (v_lat / n), True


def _homing_accel(spec, *, v_att, fwd):
    """횡속도 감쇠 = 회피 후 시선축 복귀 (A2 전용).

    A1 의 전진항은 **속도 성분만** 조절하고 횡방향 수렴이 전혀 없다(원본 주석:
    "do NOT cancel lateral velocity -- that would kill the dodge"). 그래서 지속
    회피를 얹으면 횡속도가 누적돼 표적을 빗나간다 -- P2 가 실제로 이것을 잡았다.

    **회피가 가능하려면 유도가 있어야 한다.** 끝까지 지그재그하고 못 맞히는 공격자는
    더 강한 게 아니라 더 약하다. 이 항이 있어야 사다리가 단조가 된다.

    착취 방지 규칙 2 와의 관계: 이 파라미터는 **방어자와 무관한 선언된 성질(P2:
    무방어 상대 침투율 1.0)** 을 만족시키려고 고른 것이지 특정 arm 을 이기려고 고른
    것이 아니다. 전자는 기능 정의, 후자가 착취다.
    """
    if spec.homing_gain == 0.0:
        return np.zeros(3)
    v = np.asarray(v_att, float)
    v_lat = v - float(v @ fwd) * fwd
    return -spec.homing_gain * v_lat


# ----------------------------------------------------------- general action ---
def _general_action(spec, p_att, v_att, *, target, net_center, finisher_p, limiters,
                    kill_radius, a_att_max, omega_att_max, v_nominal, dt,
                    committed=False, react_on_commit=True, a_lat_max=None,
                    repel_margin=1.5, t=0.0, phase=0.0, v_shot_soft=None,
                    v_max=None, diag=None, **_ignored):
    """A1 의 산술을 그대로 재현하고 그 위에 lambda 스케일 + A2/v3 항을 얹는다.

    extras 가 전부 꺼지고 lambda 가 기준점이면 `scripted_adversary_action` 과
    수치적으로 동일해야 한다 (P1b 가 검증).

    `v_max` = 백엔드 속도 클램프 (기 선언 능력 adversary_v_max). sprint 참조속도
    상한으로만 쓴다 -- None 이면 v_nominal 로 폴백 (sprint 무력화, 능력 초과 방지).
    """
    p_att = np.asarray(p_att, float)
    v_att = np.asarray(v_att, float)
    if a_lat_max is None:
        a_lat_max = a_att_max
    fwd = _unit(target - p_att, v_att)

    # --- v3: 종축 속도 프로파일 (docs/60 §2). off 면 산술 자체를 안 탄다 ------
    v_ref = v_nominal
    if spec.sprint_range > 0.0 or spec.slowdown_range[0] > 0.0:
        d_asset = float(np.linalg.norm(np.asarray(target, float) - p_att))
        far, near = spec.slowdown_range
        if spec.sprint_range > 0.0 and d_asset <= spec.sprint_range:
            v_ref = spec.sprint_frac * (float(v_max) if v_max is not None
                                        else float(v_nominal))
        elif far > 0.0 and near < d_asset <= far:
            v_ref = spec.slowdown_frac * float(v_nominal)

    # --- A1: 전진 P-drive (원본과 동일 순서; v3 off 면 v_ref == v_nominal) ----
    v_fwd = float(v_att @ fwd)
    a_fwd = 4.0 * (v_ref - v_fwd) * fwd

    # --- A1: 커밋 후 횡회피 ---------------------------------------------------
    to_net = _unit(net_center - p_att, fwd)
    off = (p_att - net_center)
    lateral = off - (off @ to_net) * to_net
    dodge_dir = _unit(lateral, _unit(np.cross(fwd, [0, 0, 1.0]), [0, 1.0, 0]))
    amp = _REF_DODGE_AMP if (committed and react_on_commit) else 0.0
    a_dodge = amp * a_lat_max * dodge_dir

    # --- lambda: 살상반경 반발 (크기 lam_gain, 발동거리 lam_range) ------------
    a_rep = np.zeros(3)
    if limiters is not None and kill_radius > 0 and spec.lam_gain != 0.0:
        R = (repel_margin * spec.lam_range) * kill_radius
        L = np.asarray(limiters, float).reshape(-1, 3)
        for c in L:
            d = p_att - c
            dist = np.linalg.norm(d)
            if dist <= R:
                strength = (R - dist) / R
                a_rep += a_att_max * spec.lam_gain * (1.0 + strength) * _unit(d, fwd)

    a_cmd = a_fwd + a_dodge + a_rep

    # --- A2/A3 (extras). 꺼져 있으면 덧셈 자체를 하지 않는다 (bit-exactness) --
    a_route = np.zeros(3)
    if spec.jink_amp != 0.0 or spec.route_gain != 0.0 or spec.bait_gain != 0.0:
        d_target = float(np.linalg.norm(np.asarray(target, float) - p_att))
        a_bait, baiting = _bait_accel(
            spec, p_att=p_att, v_att=v_att, fwd=fwd, finisher_p=finisher_p,
            limiters=limiters, kill_radius=kill_radius, a_lat_max=a_lat_max,
            committed=committed, v_shot_soft=v_shot_soft)
        a_cmd = a_cmd + a_bait
        if not baiting:                      # 유도중에는 jink 를 끈다 (얌전해 보이기)
            a_cmd = a_cmd + _jink_accel(spec, fwd=fwd, t=t, phase=phase,
                                        a_lat_max=a_lat_max, committed=committed,
                                        d_target=d_target)
        a_route = _route_accel(spec, p_att=p_att, v_att=v_att, fwd=fwd,
                               limiters=limiters, kill_radius=kill_radius,
                               repel_margin=repel_margin,
                               a_lat_max=a_lat_max, d_target=d_target)
        a_cmd = a_cmd + a_route
        a_cmd = a_cmd + _homing_accel(spec, v_att=v_att, fwd=fwd)

    nrm = np.linalg.norm(a_cmd)
    if diag is not None:                     # P89 계측 싱크 (docs/60 §5) -- 행동 불변
        diag.update(
            a_raw=float(nrm), clipped=bool(nrm > a_att_max),
            route_req=[float(x) for x in a_route], v_ref=float(v_ref),
            speed=float(np.linalg.norm(v_att)),
            v_max=(float(v_max) if v_max is not None else None),
            d_asset=float(np.linalg.norm(np.asarray(target, float) - p_att)),
            committed=bool(committed))
    if nrm > a_att_max and nrm > _EPS:
        a_cmd = a_cmd * (a_att_max / nrm)
    if diag is not None:
        diag["a_final"] = [float(x) for x in a_cmd]

    e_cmd = _unit(v_att + a_cmd * dt, fwd)
    return {"a": a_cmd, "e_cmd": e_cmd}


# --------------------------------------------------------------- factory ------
def make_attacker(spec: AttackerSpec, *, force_general: bool = False):
    """spec -> callable(p_att, v_att, **kwargs) -> {"a", "e_cmd"}.

    A1 등가이고 force_general 이 아니면 **기존 함수에 문자 그대로 위임**한다.
    force_general=True 는 P1b(재현 충실성) 테스트 전용.
    """
    if is_a1_equivalent(spec) and not force_general:
        # 위임 경로는 A1 의 시그니처만 받는다. 사다리 전용 kwarg 는 여기서 걸러야
        # 하며(A1 은 그것들을 모른다), 목록은 _LADDER_ONLY_KW 한 곳에서 관리한다.
        def _a1(p_att, v_att, **kw):
            for k in _LADDER_ONLY_KW:
                kw.pop(k, None)
            return scripted_adversary_action(p_att, v_att, **kw)
        _a1.spec = spec
        return _a1

    def _gen(p_att, v_att, **kw):
        return _general_action(spec, p_att, v_att, **kw)
    _gen.spec = spec
    return _gen


def with_lambda(spec: AttackerSpec, preset: str) -> AttackerSpec:
    """lambda 프리셋 적용 (행동 등급·파라미터는 그대로)."""
    if preset not in LAMBDA_PRESETS:
        raise KeyError(f"unknown lambda preset {preset!r}; "
                       f"allowed: {sorted(LAMBDA_PRESETS)}")
    g, r = LAMBDA_PRESETS[preset]
    return replace(spec, lam_gain=g, lam_range=r,
                   label=f"{spec.label or spec.level}+{preset}")
