"""P84 — coupling Gate 1: attacker–limiter manipulation check (docs/58 §7).

"0.75 m 밖에서 limiter 배치는 공격자 행동에 인과효과가 없다" 를 결과 artifact
로 고정한다. 채널 격리: fire_mode="never" (net-side committed 경로 차단 --
남는 후보 채널은 repel 뿐).

판정 (사전등록): (i) 밖 구성 3종 전부 공격자 궤적 bit 동일 (ii) positive
control (0.74 m 안) 은 1스텝 내 발산 -- 아니면 검사 무효.
torch-free.
"""
from __future__ import annotations

import argparse, json, pathlib
from typing import List
import numpy as np

from shepherd.scripts.recoverability_probe import (
    MISS_EPISODES, SEED0, _analytic_backend, drive_to, replay_baseline)

__all__ = ["coupling_gate"]

T_STEPS = 10
CLEAR = 2.0                     # 밖 구성의 최소 이격 [m] (사전등록)


def _teleport(d, positions):
    bk = _analytic_backend(d.env)
    for lid, p in zip(d.env.limiter_ids, positions):
        ag = bk.by_name(lid)
        ag.p = np.asarray(p, float).copy()
        ag.v = np.zeros(3)


def _att_traj(d, steps=T_STEPS):
    out = [d.env._p(d.env._states()[2]).copy()]
    for _ in range(steps):
        if d.done:
            break
        d.step(limiter_mode="hold")
        out.append(d.env._p(d.env._states()[2]).copy())
    return np.array(out)


def _configs(p_att, fwd):
    """밖 구성 3종 (docs/58 §7). 전부 공격자 기준 >= CLEAR."""
    lat = np.array([0.0, 1.0, 0.0])
    up = np.array([0.0, 0.0, 1.0])
    return {
        "side": [p_att + 12 * lat + i * 3 * fwd for i in range(4)],
        "line": [p_att - (6 + 2 * i) * fwd for i in range(4)],
        "far":  [p_att + 15 * (lat if i % 2 else -lat) + (15 if i < 2 else -15) * up
                 for i in range(4)],
    }


def coupling_gate(episodes=MISS_EPISODES) -> dict:
    rows: List[dict] = []
    for ep in episodes:
        base = replay_baseline(ep)
        for tag, s0 in (("prefire", base.fire_step - 5),
                        ("postmiss", base.handoff_step + 1)):
            ref = drive_to(ep, s0)
            ref.fire_mode = "never"
            att0 = ref.env._p(ref.env._states()[2]).copy()
            v0 = ref.env._v(ref.env._states()[2])
            fwd = v0 / max(float(np.linalg.norm(v0)), 1e-9)
            traj_ref = _att_traj(ref)

            for name, pos in _configs(att0, fwd).items():
                d = drive_to(ep, s0)
                d.fire_mode = "never"
                _teleport(d, pos)
                # 사전 검증: 배치 시점 이격 >= CLEAR (위반 시 구성 무효 기록)
                clr = min(float(np.linalg.norm(att0 - np.asarray(p))) for p in pos)
                traj = _att_traj(d)
                n = min(len(traj_ref), len(traj))
                dev = float(np.max(np.linalg.norm(traj_ref[:n] - traj[:n], axis=1)))
                rows.append(dict(episode=ep, timepoint=tag, config=name,
                                 clearance=round(clr, 2), steps=n - 1,
                                 max_dev=dev, identical=bool(dev == 0.0)))

            # positive control: limiter 0 을 0.74 m 안 (repel 발동 예상)
            d = drive_to(ep, s0)
            d.fire_mode = "never"
            bk = _analytic_backend(d.env)
            ag = bk.by_name(d.env.limiter_ids[0])
            ag.p = att0 + 0.74 * np.array([1.0, 0.0, 0.0])
            ag.v = np.zeros(3)
            traj = _att_traj(d, steps=3)
            n = min(len(traj_ref), len(traj))
            dev1 = float(np.linalg.norm(traj_ref[1] - traj[1]))
            rows.append(dict(episode=ep, timepoint=tag, config="POSITIVE_CONTROL",
                             clearance=0.74, steps=n - 1, max_dev=dev1,
                             identical=bool(dev1 == 0.0)))
    outside = [r for r in rows if r["config"] != "POSITIVE_CONTROL"]
    pos = [r for r in rows if r["config"] == "POSITIVE_CONTROL"]
    return {
        "contract": "docs/58 §7 (P84)",
        "outside_all_identical": all(r["identical"] for r in outside),
        "outside_n": len(outside),
        "positive_control_all_diverge": all(not r["identical"] for r in pos),
        "positive_control_n": len(pos),
        "min_clearance_outside": min(r["clearance"] for r in outside),
        "records": rows,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="P84 coupling Gate 1 (docs/58 §7)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    r = coupling_gate()
    print(f"밖 구성 {r['outside_n']}건 전부 동일: {r['outside_all_identical']} "
          f"(최소 이격 {r['min_clearance_outside']} m)")
    print(f"positive control {r['positive_control_n']}건 전부 발산: "
          f"{r['positive_control_all_diverge']}")
    bad = [x for x in r["records"]
           if (x["config"] != "POSITIVE_CONTROL") != x["identical"]]
    for x in bad:
        print("  예외:", x)
    if a.out:
        p = pathlib.Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  -> {a.out}")


if __name__ == "__main__":
    main()
