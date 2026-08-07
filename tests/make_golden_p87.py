"""P87 golden 생성 — v3 배선 **전** 커밋의 동작을 고정한다 (docs/60 §5 P87).

v3 필드가 전부 기본값일 때 attacker 행동과 spawn draw 가 이 golden 과 bit
동일해야 한다. 이 스크립트는 배선 전 코드에서 한 번 실행해 JSON 을 만들고,
이후 다시 실행하지 않는다 (재실행하면 gate 가 자기참조가 된다).

    PYTHONIOENCODING=utf-8 python tests/make_golden_p87.py
"""
from __future__ import annotations

import json
import pathlib

import numpy as np

from shepherd.agents.attacker_ladder import AttackerSpec, make_attacker
from shepherd.scale_v2 import SCALE_V2_SPAWN
from shepherd.spawn_rand import sample_spawn

OUT = pathlib.Path(__file__).parent / "golden" / "p87_prewiring.json"

# V4 baseline 의 공격자 (scale_v2_baseline.py 와 동일 spec)
A2_V4 = AttackerSpec(level="A2", jink_amp=0.6, seed=0)


def attacker_grid():
    """합성 상태 격자에서 general 경로 출력 덤프 (P1b 의 kwarg 묶음과 동일 형)."""
    fn = make_attacker(A2_V4)          # jink!=0 -> general 경로
    rng = np.random.default_rng(20260807)
    rows = []
    for i in range(300):
        kw = dict(
            target=np.zeros(3), net_center=rng.normal(size=3) * 3.0,
            finisher_p=np.array([2.0, 0.0, 0.0]),
            limiters=rng.normal(size=(4, 3)) * 4.0,
            kill_radius=0.75, a_att_max=30.0, omega_att_max=8.0,
            v_nominal=20.0, dt=0.05, committed=bool(rng.integers(2)),
            repel_margin=1.0, t=float(i) * 0.05, phase=1.234,
        )
        p = rng.normal(size=3) * 8.0 + np.array([50.0, 0.0, 0.0])
        v = rng.normal(size=3) * 10.0
        out = fn(p.copy(), v.copy(), **{k: (val.copy() if isinstance(val, np.ndarray)
                                            else val) for k, val in kw.items()})
        rows.append({"a": list(map(float, out["a"])),
                     "e": list(map(float, out["e_cmd"]))})
    return rows


def spawn_grid():
    """SCALE_V2_SPAWN draw 10 에피소드 덤프."""
    rows = []
    for ep in range(10):
        d = sample_spawn(SCALE_V2_SPAWN, base_p=[300.0, 0.0, 0.0],
                         target=[0.0, 0.0, 0.0], speed=20.0, seed=0, episode=ep)
        rows.append({"p": list(map(float, d.p)), "v": list(map(float, d.v)),
                     "e": list(map(float, d.e))})
    return rows


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"attacker": attacker_grid(), "spawn": spawn_grid()},
                              indent=1), encoding="utf-8")
    print(f"golden -> {OUT}")
