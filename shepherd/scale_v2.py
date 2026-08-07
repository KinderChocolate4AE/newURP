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

import math
from dataclasses import replace

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.spawn_rand import SpawnSpec, StandbySpec

__all__ = ["SCALE_V2_CFG", "SCALE_V2_SPAWN",
           "A2_V4", "THREAT_V3_NOMINAL", "THREAT_V3_SPAWN", "THREAT_V3_STANDBY",
           "SCALE_V3_FULL_CFG", "V3_ARMS"]

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
