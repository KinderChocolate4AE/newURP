"""docs/97 §B.4a knob-efficacy gate — Class I knob 이 실제로 causal 하게 배선돼 있는가.

    python -m shepherd.scripts.r2b_knob_efficacy

**과학 결과를 보는 gate 가 아니다.** 성능은 묻지 않는다. 단 하나만 묻는다:

    각 Class I 파라미터를 min/nominal/max 로 두면, 사전 선언된 smoke state 에서
    **시뮬레이터가 실제 쓴 attacker 출력**이 달라지는가?

**비교 대상은 재구현이 아니라 `diag`** (오늘의 규율: authoritative comparator).

사전 규칙 (배선 확인이지 성능 선택이 아니다):
  - min/nom/max 어디에서도 출력이 **한 번도 안 바뀌는** knob → nominal 고정 후 CEM 차원에서
    제거 (flat dimension 은 exploration budget 만 먹는다)
  - 한 번이라도 바뀌면 → 유지

**사전 지목** (docs/97 §B.4a): `jink_terminal_r` 이 가장 inert 할 위험이 크다 —
`101` 표본에서 3 m 게이트가 한 번도 활성화되지 않았다 (d_target 최소 ~12.9 m).
이 지목은 규칙을 바꾸지 않는다.

**smoke state 집합 (사전 선언)**: geom_probe 표본에서 `s` 오름차순 앞 **5 판**, 각 판의
봉인 plan replay 전 구간. 결정론적이라 선택 자유도가 없다.

정규화 확인 (§A.5.1 조항 3) 도 같이 낸다 — CEM 은 z ∈ [0,1] 에서 돌아야 하므로 각 구간의
affine 매핑을 여기서 미리 정의해 둔다. torch-free.
"""
from __future__ import annotations

import dataclasses
import json
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.m4_env import build_m4_env                              # noqa: E402
from shepherd.scripts.mission_rollout import run_episode              # noqa: E402
from shepherd.scripts.r2b_c_runner import (                           # noqa: E402
    SEED0, _fresh, _plan_policy, scenario_kwargs)
from shepherd.scripts.r2b_phase1 import _cells, _slices               # noqa: E402
from shepherd.scripts.r2b_steer_probe import load_geom                # noqa: E402

OUT = ROOT / "artifacts/r2b/knob_efficacy.json"
N_SMOKE = 5                      # 사전 선언: s 오름차순 앞 5 판
TOL = 0.0                        # 출력이 "달라졌다" = 비트 단위로 다르다

#: docs/97 §A.5 승인 구간 (APPROVED AS PROPOSED, 수치 변경 금지)
CLASS_I = {
    "jink_amp":        (0.0, 1.0),
    "jink_freq":       (0.5, 3.0),
    "jink_terminal_r": (0.0, 6.0),
    "route_gain":      (0.0, 1.0),
    "homing_gain":     (0.0, 8.0),
    "sense_range":     (10.0, 60.0),
    "bait_gain":       (0.0, 1.0),
}


def to_unit(name, x):
    lo, hi = CLASS_I[name]
    return (float(x) - lo) / (hi - lo)


def from_unit(name, z):
    lo, hi = CLASS_I[name]
    return lo + float(z) * (hi - lo)


def trace(s, kw, spec, plan, horizon):
    """봉인 plan 을 재생하며 diag 를 그대로 적재 (attacker 출력의 authoritative 기록)."""
    st = build_m4_env(SEED0, s, **dict(kw, attacker=spec))
    env = st.env
    _fresh(env)
    back = env.backend
    orig = back._attacker
    got: list = []

    def wrapped(p_att, v_att, **k):
        d: dict = {}
        out = orig(p_att, v_att, diag=d, **k)
        got.append(d)
        return out

    back._attacker = wrapped
    try:
        r = run_episode(env, st.scn, st.lay, seed=SEED0 + s,
                        policy=_plan_policy(env, plan, horizon),
                        scripted_roles=("finisher",), fire_mode="clean")
    finally:
        back._attacker = orig
    return r, got


def differs(a, b):
    """두 diag 열이 다른 첫 지점. 비교 항목은 시뮬레이터가 실제 쓴 값뿐."""
    if len(a) != len(b):
        return {"where": "n_ticks", "ref": len(a), "alt": len(b)}
    for i, (x, y) in enumerate(zip(a, b)):
        for k in ("a_final", "route_req"):
            if float(np.linalg.norm(np.asarray(x[k], float)
                                    - np.asarray(y[k], float))) > TOL:
                return {"where": k, "tick": i}
        for k in ("a_raw", "clipped", "committed", "v_ref", "speed", "d_asset"):
            if x.get(k) != y.get(k):
                return {"where": k, "tick": i}
    return None


def main():
    cells, sls = _cells(), _slices()
    geom = load_geom()
    scs = sorted(geom)[:N_SMOKE]
    print(f"smoke states (사전 선언): {scs}")

    base = {}
    for s in scs:
        kw = scenario_kwargs(s, cells, sls)[5]
        plan = np.asarray(geom[s]["plan"], float)
        horizon = int(build_m4_env(SEED0, s, **kw).lay.episode_len)
        r, d = trace(s, kw, kw["attacker"], plan, horizon)
        base[s] = {"kw": kw, "plan": plan, "horizon": horizon, "diag": d,
                   "label": r.label, "fire": r.fire_step}
        assert (r.label, r.fire_step) == (geom[s]["label"], geom[s]["fire_step"]), \
            f"s={s}: nominal replay parity 실패"
    print(f"nominal replay parity OK ({len(scs)} 판)\n")

    t0, res = time.time(), {}
    for name, (lo, hi) in CLASS_I.items():
        nom = getattr(base[scs[0]]["kw"]["attacker"], name)
        hits = {}
        for tag, val in (("min", lo), ("max", hi)):
            if float(val) == float(nom):
                hits[tag] = {"skipped": "endpoint == nominal"}
                continue
            found = None
            for s in scs:
                b = base[s]
                spec = dataclasses.replace(b["kw"]["attacker"], **{name: val})
                _, d = trace(s, b["kw"], spec, b["plan"], b["horizon"])
                diff = differs(b["diag"], d)
                if diff is not None:
                    found = {"s": s, **diff}
                    break
            hits[tag] = {"value": float(val), "changed_output": found is not None,
                         "first_difference": found}
        causal = any(v.get("changed_output") for v in hits.values())
        res[name] = {"nominal": float(nom), "range": [lo, hi],
                     "unit_of_nominal": to_unit(name, nom),
                     "endpoints": hits, "causal": causal,
                     "verdict": "KEEP" if causal else "DROP (fix at nominal)"}
        print(f"  {name:<16} nom {nom:<6g} z_nom {to_unit(name, nom):.3f}  "
              f"-> {res[name]['verdict']}"
              + ("" if causal else "   <-- CEM 차원에서 제거"))

    keep = [k for k, v in res.items() if v["causal"]]
    out = {"doc": "docs/97 §B.4a", "purpose": "wiring check, not performance",
           "comparator": "simulator diag (authoritative) — not a reimplementation",
           "smoke_states": scs, "class_I_intervals": CLASS_I,
           "normalization": "CEM searches z in [0,1]^d; affine map per interval "
                            "(docs/97 §A.5.1 clause 3)",
           "results": res, "keep": keep,
           "drop": [k for k in CLASS_I if k not in keep],
           "cem_dim": len(keep), "elapsed_s": time.time() - t0}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nCEM 차원: {len(CLASS_I)} -> {len(keep)}   유지 {keep}")
    print(f"제거 {out['drop']}   ({time.time()-t0:.0f} s)")


if __name__ == "__main__":
    main()
