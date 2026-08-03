"""공용 통계 헬퍼. 의존성 없음 (stdlib math 만) -- torch-free · env-import-free.

2026-08-03: Wilson 구간이 네 곳에 따로 구현돼 있었다 (`scripts/c1_phase1e`,
`scripts/curve_sweep`, `scripts/sweep_m4`, `train/phi_potential`). 수식은 전부
같았지만 판정식이 여기에 걸려 있으므로 **한 곳에서만** 정의한다.
"""
from __future__ import annotations

import math

__all__ = ["wilson", "Z_TWO_SIDED_95", "Z_ONE_SIDED_95"]

Z_TWO_SIDED_95 = 1.959964
Z_ONE_SIDED_95 = 1.645


def wilson(k: int, n: int, z: float = Z_TWO_SIDED_95) -> tuple[float, float]:
    """이항 비율의 Wilson 점수 구간 (lower, upper). k=0 에서도 유한한 상한을 준다."""
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    d = 1.0 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max((c - h) / d, 0.0), min((c + h) / d, 1.0))
