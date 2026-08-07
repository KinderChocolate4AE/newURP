"""Scripted policies + baselines for the M2 shaping env (pure numpy, no torch).

Exercised in M2/L1:
  - hold_position_limiter   : the FIXED u_L^0 baseline (limiter does nothing).
                              This is the headline + COMA counterfactual baseline.
  - scripted_shaping_limiter: drives limiter i onto its escape-ring slot on the
                              attacker's ACTIVE lateral escape route (channel (i)).
  - scripted_finisher       : point the net axis at the predicted attacker endpoint;
                              fire ONLY on a clean v_shot threshold crossing.

Stubs (declared for the exchange-frontier comparison, NOT exercised in M2):
  no_shaping / selection_only / buy_nets -> raise NotImplementedError (S9/M3).
"""
from __future__ import annotations
import numpy as np

_EPS = 1e-12


def _unit(v, fallback=None):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    if n < _EPS:
        return np.zeros(3) if fallback is None else np.asarray(fallback, float)
    return v / n


def _perp_basis(axis):
    """Two unit vectors spanning the plane perpendicular to `axis`."""
    a = _unit(axis, [1.0, 0.0, 0.0])
    ref = np.array([0.0, 0.0, 1.0]) if abs(a[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = _unit(np.cross(a, ref), [0.0, 1.0, 0.0])
    w = _unit(np.cross(a, u), [0.0, 0.0, 1.0])
    return u, w


def hold_position_limiter():
    """u_L^0: no acceleration, hold heading. The fixed baseline action (Box(4))."""
    return np.zeros(4, dtype=np.float32)            # accel(3)=0, pressure(1)=0

# ── 제4병목 계측용 단순 컨트롤러 (docs/20 §6 · docs/21) ─────────────────────
#   왜 여기 있나: "정책이 zero 만 이기고 이 선 아래면 학습 가능성 증거이지
#   RL-필요성 증거가 아니다" -- 논문 클레임 트리에 **정책 vs 단순 컨트롤러
#   비교 보고가 의무**로 등재돼 있다 (docs/20 §6 제4병목, docs/21 sealed 진단 arm).
#   2026-07-19 구 캠페인 실측: brake+guard .858 ≒ lam20+guard .858 > learned .775.
#
#   정의는 `train/pfc.py` 의 것을 **그대로** 옮긴다 (docs/48 §3.1 한 곳 원칙과
#   같은 이유 -- 두 벌이 되면 비교가 "두 구현의 차이" 가 된다). 다만 `pfc` 는
#   구 환경 상수(A_MAX=30.0, 63차원 관측)에 묶여 있어 import 하지 않고, 식만
#   옮기고 상한은 **호출부의 `a_max`** 를 받는다.
#
#   ★ 구 캠페인의 절대 수치(.858 등)는 다른 환경(A-3d/A-3e, a_max=30.0)에서
#   난 것이다. M4 에서 같은 값이 나올 이유가 없다. 여기서 재는 것은 **순서**
#   (단순 컨트롤러 대 학습) 이지 수치 재현이 아니다.
LAM_GAIN = 20.0                 # lam20 의 감쇠 이득. 구 캠페인 선언값 그대로


def brake_limiter(v_self, a_max: float):
    """`a = -a_max * unit(v)`. 자기 속도 반대로 **최대 감속**. 관측 전용."""
    v = np.asarray(v_self, float)
    n = float(np.linalg.norm(v))
    a = (-a_max * v / n) if n > 1e-6 else np.zeros(3)
    return np.concatenate([a, [0.0]]).astype(np.float32)


def lambda_brake_limiter(v_self, a_max: float, lam: float = LAM_GAIN):
    """`a = clip(-lam * v, a_max)`. 비례 감쇠. 관측 전용."""
    a = -float(lam) * np.asarray(v_self, float)
    n = float(np.linalg.norm(a))
    if n > a_max and n > 0.0:
        a = a * (a_max / n)
    return np.concatenate([a, [0.0]]).astype(np.float32)



def ring_slot(i, n_limiters, center, approach_dir, r_ring):
    """Slot for limiter i on the escape ring: a circle of radius r_ring in the
    plane perpendicular to the attacker's approach, centered at `center`."""
    u, w = _perp_basis(approach_dir)
    ang = 2.0 * np.pi * (i / max(n_limiters, 1))
    return np.asarray(center, float) + r_ring * (np.cos(ang) * u + np.sin(ang) * w)


def scripted_shaping_limiter(i, n_limiters, p_lim, v_lim, p_att, v_att, *, tau, a_max,
                             r_ring, dt, pressure=1.0, kp=8.0, kd=4.0):
    """Drive limiter i onto its slot on the predicted-ENDPOINT escape shell (where
    the lateral escapes land), closing channel (i). PD control (kd damps overshoot
    so the limiter SETTLES on the shell instead of orbiting). Returns a Box(4)
    action: accel(3) + kill-radius pressure(1)."""
    endpoint = np.asarray(p_att, float) + np.asarray(v_att, float) * tau
    slot = ring_slot(i, n_limiters, endpoint, v_att, r_ring)
    err = slot - np.asarray(p_lim, float)
    a_cmd = kp * err - kd * np.asarray(v_lim, float)        # PD toward the slot
    nrm = np.linalg.norm(a_cmd)
    if nrm > a_max and nrm > _EPS:
        a_cmd = a_cmd * (a_max / nrm)
    return np.array([a_cmd[0], a_cmd[1], a_cmd[2], float(pressure)], dtype=np.float32)


def scripted_finisher(p_fin, p_att, v_att, *, tau, clean_threshold_crossed):
    """Point the net axis at the predicted attacker endpoint; fire (logit>0.5)
    ONLY when the env reports a CLEAN v_shot threshold crossing. The FSM still
    enforces irreversibility + the single fire gate. Returns Box(5):
    net-axis target(3) + slew(1) + fire-logit(1)."""
    endpoint = np.asarray(p_att, float) + np.asarray(v_att, float) * tau
    axis = _unit(endpoint - np.asarray(p_fin, float), [1.0, 0.0, 0.0])
    fire_logit = 1.0 if clean_threshold_crossed else 0.0
    return np.array([axis[0], axis[1], axis[2], 1.0, fire_logit], dtype=np.float32)


# ── docs/63 r2 scripted baseline — bearing-aware arc redeployment ──────────
#   family = reactive arc (예측 lead·CPA·v_shot 소비·z 배치 금지, §2).
#   kp/kd 는 선언값 (params scripted.limiter_kp/kd = 8.0/4.0) 재사용 — 재튜닝
#   금지. 자유도는 (r_d, dphi) grid 2축뿐 (F4).
def arc_slots(target, p_att, r_d: float, dphi: float, n: int = 4):
    """docs/63 §2-1: 공격자 현재 bearing 중심, 반경 r_d 수평 호 위 slot n개.

    z = 0 은 scope limitation (수평 섹터 last-mile, docs/61 §4)이다.
    """
    import math
    d = np.asarray(p_att, float) - np.asarray(target, float)
    phi = math.atan2(d[1], d[0])
    return [np.asarray(target, float) + float(r_d) * np.array(
                [math.cos(phi + (k - (n - 1) / 2.0) * float(dphi)),
                 math.sin(phi + (k - (n - 1) / 2.0) * float(dphi)), 0.0])
            for k in range(n)]


def min_cost_assignment(positions, slots):
    """docs/63 §2-2 (r1): permutation 전수에서 이동거리 제곱합 최소를 고른다.

    4기 → 24개 전수. parameter-free (oracle·예측·신규 hyperparameter 없음).
    동률 = 사전순 첫 permutation (strict < 비교 — 결정론).
    """
    import itertools
    best, best_c = None, None
    for perm in itertools.permutations(range(len(slots))):
        c = sum(float(np.sum((np.asarray(positions[i], float)
                              - np.asarray(slots[perm[i]], float)) ** 2))
                for i in range(len(positions)))
        if best_c is None or c < best_c:
            best, best_c = perm, c
    return best


def arc_redeploy_limiter(p_lim, v_lim, slot, *, a_max, kp=8.0, kd=4.0):
    """docs/63 §2-3: 선언 PD 로 배정 slot 호밍. Box(4), idx3 = 0 (commit 금지
    — `_zero_commit` 이 한 번 더 누르지만 여기서도 0 을 낸다)."""
    err = np.asarray(slot, float) - np.asarray(p_lim, float)
    a_cmd = kp * err - kd * np.asarray(v_lim, float)
    n = float(np.linalg.norm(a_cmd))
    if n > a_max and n > _EPS:
        a_cmd = a_cmd * (a_max / n)
    return np.array([a_cmd[0], a_cmd[1], a_cmd[2], 0.0], dtype=np.float32)


# --- stubs (exchange-frontier comparison; NOT exercised in M2) --------------
def no_shaping(*a, **k):
    raise NotImplementedError("no_shaping is an S9/M3 exchange-frontier baseline (not M2).")


def selection_only(*a, **k):
    raise NotImplementedError("selection_only is an S9/M3 exchange-frontier baseline (not M2).")


def buy_nets(*a, **k):
    raise NotImplementedError("buy_nets is an S9/M3 exchange-frontier baseline (not M2).")
