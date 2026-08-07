"""교전 스케일 계약 v2 overlay (docs/59, 브랜치 격리).

새 코드 경로가 아니라 **config overlay dict 하나**다 — params 레지스트리의
선언 키만 바꾼다. 하드웨어/안전 절대값(kill_radius·net cone·tau_deploy·
r_nk·dt)은 건드리지 않는다. overlay 미적용 = 기존과 비트 동일 (P85).

    from shepherd.scale_v2 import SCALE_V2_CFG, SCALE_V2_SPAWN
    st = build_m4_env(seed, ep, ..., spawn=SCALE_V2_SPAWN,
                      extra_cfg=SCALE_V2_CFG)

torch-free.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import replace

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.spawn_rand import SpawnSpec, StandbySpec

__all__ = ["SCALE_V2_CFG", "SCALE_V2_SPAWN",
           "A2_V4", "THREAT_V3_NOMINAL", "THREAT_V3_SPAWN", "THREAT_V3_STANDBY",
           "SCALE_V3_FULL_CFG", "V3_ARMS",
           "V3_TRAIN_CELLS_A", "V3_TRAIN_CELLS_B", "V3_STANDBY_R",
           "EPISODE_LEN_TRAIN", "SCALE_V3_TRAIN_CFG", "draw_threat_v3",
           "v3_distribution_hash", "reaction_stratum"]

# docs/59 §1 선언값. 결과를 본 뒤 바꾸지 않는다.
SCALE_V2_CFG = {
    "train.layout.adversary_start_x": 300.0,   # 24 -> 300 (~10 s+ 대응시간)
    "train.episode_len": 800,                  # 80 -> 800 (40 s; docs/59 정정 2 --
                                               # att_speed 하한 8 m/s -> 310/8=38.75 s)
    "train.layout.ring_center": (50.0, 0.0, 0.0),  # 8 -> 50 (NK 밖 + cone 상류)
}

# dx 2 -> 10 (도달시간 지터 ±0.5 s @ v=20). r_lat 은 ring_radius 연동 유지.
SCALE_V2_SPAWN = SpawnSpec(dx=10.0)


# ===========================================================================
# 위협 계약 v3 NOMINAL (docs/60 §7 동결표 -- manipulation-check 대표점.
# "정답값" 아님. 학습은 이 점이 아니라 docs/61 TRAIN 분포로만.)
# ===========================================================================
A2_V4 = AttackerSpec(level="A2", jink_amp=0.6, seed=0)   # V4 baseline 공격자

THREAT_V3_NOMINAL = replace(
    A2_V4,
    sprint_range=60.0,               # #1
    sprint_frac=1.0,                 # #2
    slowdown_range=(90.0, 60.0),     # #3 (기전 주장 보류, docs/60 §2.1)
    slowdown_frac=0.5,               # #4
    route_gain=0.5,                  # #5 (P89 saturation audit 조건부)
    sense_range=30.0,                # #6
    label="A2-v3-nominal")

# #8 r_range + #9 azimuth. dx=0 -- 거리 지터는 r_range 가 담당 (이중계상 방지).
THREAT_V3_SPAWN = SpawnSpec(dx=0.0, r_range=(250.0, 350.0), azimuth=math.pi / 4)

THREAT_V3_STANDBY = StandbySpec(R=12.0)                  # #11~13

# #10 episode_len 1000 (P90 조건부 임시): r_max 350 / v_min 8 + slowdown 지연
# + 전개·lock 여유 = 48.75 s -> 50 s (docs/60 §4.2 산술).
SCALE_V3_FULL_CFG = dict(SCALE_V2_CFG, **{"train.episode_len": 1000})

# ===========================================================================
# THREAT_V3_TRAIN — balanced experimental design distribution (docs/61 r2
# 비준·동결). 셀 경계·범위는 전부 결과 전 선언값 — 변경은 새 사전등록으로만.
# 9셀 균등은 위협 빈도 추정이 아니라 각 regime 동일 실험 가중치 (§0 재명명).
# ===========================================================================
# 층 A — 횡 반응성: (route_gain 범위, sense_range 범위)  [docs/61 §2]
V3_TRAIN_CELLS_A = {
    "weak":   ((0.2, 0.4), (15.0, 25.0)),   # 하한 0.2: 전 위협 반응형 (0 = v2 회귀)
    "medium": ((0.4, 0.6), (25.0, 35.0)),   # nominal (0.5, 30) 포함 셀
    "strong": ((0.6, 0.8), (35.0, 45.0)),   # 비준된 상단 확장
}
# 층 B — 종축 속도 프로파일
V3_TRAIN_CELLS_B = ("cruise", "sprint", "sprint_slowdown")
V3_SPRINT_RANGE = (40.0, 80.0)
V3_SPRINT_FRAC = (0.8, 1.0)
V3_SLOWDOWN_WIDTH = (20.0, 40.0)     # far = near + U[20,40] (near = sprint_range, 연속)
V3_SLOWDOWN_FRAC = (0.4, 0.8)
# R_standby — ★ 위협 파라미터가 아니라 defender initialization uncertainty.
# 에피소드 분포 = P_threat(θ_A) × P_init(θ_D) 분리 표기 (docs/61 §2 공통표).
V3_STANDBY_R = (8.0, 16.0)
# 지평선 재산술 (docs/61 §2, 오류 18 규율): 43.75 + 7.5 + 1.25 = 52.5 s -> 55 s.
# nominal 게이트(P90)의 1000 과 별도 값. ★ P93 green 후 확정 (비준표 조건부).
EPISODE_LEN_TRAIN = 1100
SCALE_V3_TRAIN_CFG = dict(SCALE_V2_CFG, **{"train.episode_len": EPISODE_LEN_TRAIN})

_V3_LAYERS = ("train", "iid")


def _u_v3(layer: str, seed: int, episode: int, key: str) -> float:
    """[0,1) 균일난수 — `derive_spawn_u` 규약 동형 (SHA-256, 파이썬 hash 금지).

    namespace = `v3_train` / `v3_iid` (docs/61 §3 — IID 는 namespace 분리 +
    episode 대역 분리(train 0..N, iid 10000..)를 **둘 다** 쓴다; 대역은 호출자
    책임). 축별 key 분리 — 셀 draw 는 별도 key ("cell").
    """
    h = hashlib.sha256(
        f"v3_{layer}|{int(seed)}|{int(episode)}|{key}".encode()).digest()
    return int.from_bytes(h[:8], "big") / 2 ** 64


def draw_threat_v3(seed: int, episode: int, layer: str) -> dict:
    """docs/61 §1 stratified draw: 셀 (9셀 균등) -> 셀 내 축별 uniform jitter.

    반환 = V3_ARMS 항목과 동형 dict (`attacker`/`spawn`/`standby`/`cfg`) +
    `cell` (감사용). AttackerSpec/StandbySpec 필드로만 구성 — 새 코드 경로
    없음. cruise 층은 sprint/slowdown 이 AttackerSpec 기본값(off)이라 v2
    거동이 TRAIN 안에 nested 다. NOMINAL 로 학습 금지 (관통 규율 2) — 이
    함수가 유일한 TRAIN 산지다.
    """
    if layer not in _V3_LAYERS:
        raise ValueError(f"layer 는 {_V3_LAYERS} 중 하나여야 한다: {layer!r}")
    u = lambda key: _u_v3(layer, seed, episode, key)          # noqa: E731
    lerp = lambda lo_hi, x: lo_hi[0] + x * (lo_hi[1] - lo_hi[0])   # noqa: E731

    cell = int(u("cell") * 9)                     # u < 1 이므로 0..8
    a_name = tuple(V3_TRAIN_CELLS_A)[cell // 3]
    b_name = V3_TRAIN_CELLS_B[cell % 3]
    rg, sr = V3_TRAIN_CELLS_A[a_name]

    kw = dict(route_gain=lerp(rg, u("route_gain")),
              sense_range=lerp(sr, u("sense_range")))
    if b_name != "cruise":
        sprint_range = lerp(V3_SPRINT_RANGE, u("sprint_range"))
        kw.update(sprint_range=sprint_range,
                  sprint_frac=lerp(V3_SPRINT_FRAC, u("sprint_frac")))
        if b_name == "sprint_slowdown":
            near = sprint_range                   # 구간 연속 (docs/61 §2 층 B)
            far = near + lerp(V3_SLOWDOWN_WIDTH, u("slowdown_width"))
            kw.update(slowdown_range=(far, near),
                      slowdown_frac=lerp(V3_SLOWDOWN_FRAC, u("slowdown_frac")))

    return dict(
        attacker=replace(A2_V4, label=f"A2-v3-{layer}-{a_name}/{b_name}", **kw),
        spawn=THREAT_V3_SPAWN,                    # docs/60 비준값 유지 (공통표)
        standby=StandbySpec(R=lerp(V3_STANDBY_R, u("standby_R"))),   # P_init
        cfg=SCALE_V3_TRAIN_CFG,
        cell=(a_name, b_name))


def reaction_stratum(seed: int, episode: int, stratum: str,
                     layer: str = "train") -> dict:
    """P95 paired CRN 재정식화 (docs/61 §5 r2): base draw 의 능력·속도
    프로파일·spawn·standby·jink 위상을 **전부 고정**하고, reaction 축
    (route_gain·sense_range)만 지정 층의 범위로 재사상한다.

    같은 에피소드의 축별 u 를 그대로 쓰므로 세 층은 축 내 상대 위치까지
    동일한 **paired 3중**이다. draw_threat_v3 와 같은 단일 산지 규율.
    """
    if stratum not in V3_TRAIN_CELLS_A:
        raise ValueError(f"stratum 은 {tuple(V3_TRAIN_CELLS_A)} 중 하나: "
                         f"{stratum!r}")
    d = draw_threat_v3(seed, episode, layer)
    rg, sr = V3_TRAIN_CELLS_A[stratum]
    u = lambda key: _u_v3(layer, seed, episode, key)          # noqa: E731
    att = replace(d["attacker"],
                  route_gain=rg[0] + u("route_gain") * (rg[1] - rg[0]),
                  sense_range=sr[0] + u("sense_range") * (sr[1] - sr[0]),
                  label=f"A2-v3-{layer}-p95-{stratum}")
    return dict(d, attacker=att, cell=(stratum, d["cell"][1]))


def v3_distribution_hash() -> str:
    """TRAIN 분포의 version hash (docs/65 A4b — resolved-contract manifest 용).

    선언 상수 전체(셀 경계 + 공통축 + 지평선 + spawn + 능력 브래킷/비율)의
    canonical serialization. 어느 하나라도 바뀌면 hash 가 바뀐다 — 사전등록
    변경 감지가 목적이므로 **테스트가 현재 값을 pin 한다** (변경 = 새 사전등록
    + pin 갱신을 같은 커밋에서).
    """
    import json as _json

    from shepherd.m4_config import CAPABILITY_RATIOS, THREAT_BRACKET
    payload = dict(
        cells_a=V3_TRAIN_CELLS_A, cells_b=V3_TRAIN_CELLS_B,
        sprint_range=V3_SPRINT_RANGE, sprint_frac=V3_SPRINT_FRAC,
        slowdown_width=V3_SLOWDOWN_WIDTH, slowdown_frac=V3_SLOWDOWN_FRAC,
        standby_r=V3_STANDBY_R, episode_len_train=EPISODE_LEN_TRAIN,
        spawn=dict(dx=THREAT_V3_SPAWN.dx, r_range=THREAT_V3_SPAWN.r_range,
                   azimuth=THREAT_V3_SPAWN.azimuth),
        threat_bracket=THREAT_BRACKET, capability_ratios=CAPABILITY_RATIOS)
    return hashlib.sha256(
        _json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]


# nested arm (docs/60 §4.5) -- 동일 seed nesting. V6 는 descriptive 전용.
V3_ARMS = {
    "V3-C":    dict(attacker=replace(A2_V4, route_gain=0.5, sense_range=30.0,
                                     label="A2-v3-C"),
                    spawn=SCALE_V2_SPAWN, standby=None, cfg=SCALE_V2_CFG),
    "V3-CS":   dict(attacker=replace(A2_V4, route_gain=0.5, sense_range=30.0,
                                     sprint_range=60.0, slowdown_range=(90.0, 60.0),
                                     slowdown_frac=0.5, label="A2-v3-CS"),
                    spawn=SCALE_V2_SPAWN, standby=None, cfg=SCALE_V2_CFG),
    "V3-FULL": dict(attacker=THREAT_V3_NOMINAL, spawn=THREAT_V3_SPAWN,
                    standby=THREAT_V3_STANDBY, cfg=SCALE_V3_FULL_CFG),
}
