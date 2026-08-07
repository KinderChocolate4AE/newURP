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

from shepherd.spawn_rand import SpawnSpec

__all__ = ["SCALE_V2_CFG", "SCALE_V2_SPAWN"]

# docs/59 §1 선언값. 결과를 본 뒤 바꾸지 않는다.
SCALE_V2_CFG = {
    "train.layout.adversary_start_x": 300.0,   # 24 -> 300 (~10 s+ 대응시간)
    "train.episode_len": 800,                  # 80 -> 800 (40 s; docs/59 정정 2 --
                                               # att_speed 하한 8 m/s -> 310/8=38.75 s)
    "train.layout.ring_center": (50.0, 0.0, 0.0),  # 8 -> 50 (NK 밖 + cone 상류)
}

# dx 2 -> 10 (도달시간 지터 ±0.5 s @ v=20). r_lat 은 ring_radius 연동 유지.
SCALE_V2_SPAWN = SpawnSpec(dx=10.0)
