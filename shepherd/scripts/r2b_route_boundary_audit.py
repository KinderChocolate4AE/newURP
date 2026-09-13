"""101 route-choice boundary audit — docs/101 사전등록의 기계 이행.

    python -m shepherd.scripts.r2b_route_boundary_audit

**질문**: 11 cm 수준의 limiter 궤적 차이가 왜 A2 의 route request 를 107° 뒤집었는가.

**GO gate (docs/101 §2)** — 어제의 실패가 만든 규율의 첫 적용:

    ||a_route^reconstructed - diag["route_req"]|| <= 1e-9   (전 tick · 양 궤적)

`100-X` 는 `_route_accel` 원본을 부르고도 `fwd` 를 잘못 넣어 **다른 함수를 측정**했고,
자기검증이 **내 코드 vs 내 코드** 라 그것을 못 잡았다. 그래서 이번 재구성은
**시뮬레이터가 실제 쓴 값**과 대조하고, 깨지면 그 판의 δ_g 판독을 **금지**한다.

판독 2-분기 (사전 고정):
  **101-A** score-order crossing  — 후보 집합 동일 ∧ top-2 순위 뒤집힘 (near-tie separatrix)
  **101-B** topology crossing     — 후보 집합 자체가 split/merge/생성/소멸 (n_ahead 변화 포함)
  **101-N** GO gate 실패 또는 flip 없음

δ_g 만 남기지 않는다 — 전 arc 의 (width, center, endpoints) · top-2 · blocker index ·
n_ahead · n_gaps 를 보존한다 (δ_g 가 작지 않을 가능성을 미리 인정).

그룹은 `99-X` 동결 승계. 어휘: **behavior-mediated cooperative geometry under sealed A2**
(physics-only 로 일반화 금지). torch-free.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.agents.attacker_ladder import _unit                     # noqa: E402
from shepherd.m4_env import build_m4_env                              # noqa: E402
from shepherd.scripts.mission_rollout import run_episode              # noqa: E402
from shepherd.scripts.r2b_c_runner import (                           # noqa: E402
    SEED0, _fresh, _plan_policy, scenario_kwargs)
from shepherd.scripts.r2b_phase1 import _cells, _slices               # noqa: E402
from shepherd.scripts.r2b_steer_probe import _withdraw_policy, load_geom  # noqa: E402

OUT = ROOT / "artifacts/r2b/route_boundary_audit.json"
DIAG = ROOT / "artifacts/r2b/noeffect_diag.json"
RHO_N, RHO_D = 3, 4
GO_TOL = 1e-9                 # docs/101 §2
FLIP_RAD = 0.5                # divergence tick 정의 (CJ-audit 와 동일)
CENTER_TOL = 0.3              # docs/101 §4 후보 대응 규칙 (선언값)
TWO_PI = 2.0 * np.pi
_Q = 1e-9                     # _route_accel 의 tie-break 양자화 그대로


def free_arcs(spec, p_att, v_att, lims, kill_radius, a_lat_max, target):
    """`_route_accel` 의 기하를 **그대로** 재구성하고 중간 산출물을 노출한다.

    반환의 `a_route` 는 GO gate 에서 `diag["route_req"]` 와 대조된다 — 일치하지 않으면
    이 재구성은 신뢰할 수 없고 그 판은 판독에서 제외된다.
    """
    p_att = np.asarray(p_att, float)
    v_att = np.asarray(v_att, float)
    fwd = _unit(np.asarray(target, float) - p_att, v_att)   # ★ 100-X 가 틀린 곳
    d_target = float(np.linalg.norm(np.asarray(target, float) - p_att))
    zero = {"a_route": np.zeros(3), "n_ahead": 0, "n_gaps": 0, "arcs": [],
            "selected_center": None, "g1": None, "g2": None, "delta_g": None,
            "why_zero": None}
    if spec.route_gain == 0.0 or lims is None:
        return {**zero, "why_zero": "route_gain=0"}
    if spec.jink_terminal_r > 0.0 and d_target <= spec.jink_terminal_r:
        return {**zero, "why_zero": "terminal gate"}

    ref = np.array([0.0, 0.0, 1.0]) if abs(fwd[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = _unit(np.cross(fwd, ref), [0.0, 1.0, 0.0])
    w = _unit(np.cross(fwd, u), [0.0, 0.0, 1.0])
    r_block = 1.0 * spec.lam_range * float(kill_radius)      # repel_margin = 1.0

    ahead = [(i, c) for i, c in enumerate(np.asarray(lims, float))
             if float((c - p_att) @ fwd) > 0.0
             and float(np.linalg.norm(c - p_att)) <= spec.sense_range]
    if not ahead:
        return {**zero, "why_zero": "no limiter ahead"}
    spans = []
    for i, c in ahead:
        rel = c - p_att
        ox, oy = float(rel @ u), float(rel @ w)
        d = float(np.hypot(ox, oy))
        beta = float(np.arctan2(oy, ox))
        alpha = 0.5 * np.pi if d <= r_block else float(np.arcsin(r_block / d))
        spans.append((beta - alpha, beta + alpha, i))
    if sum(e - s for s, e, _ in spans) >= TWO_PI:
        return {**zero, "n_ahead": len(ahead), "why_zero": "full blockage"}

    spans = sorted(((s % TWO_PI, (s % TWO_PI) + (e - s), i) for s, e, i in spans))
    merged = []
    for s, e, i in spans + [(s + TWO_PI, e + TWO_PI, i) for s, e, i in spans]:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
            merged[-1][2].add(i)
        else:
            merged.append([s, e, {i}])
    if any(e - s >= TWO_PI for s, e, _ in merged):
        return {**zero, "n_ahead": len(ahead), "why_zero": "full blockage (merged)"}

    arcs = []
    for (s0, e0, b0), (s1, _e1, b1) in zip(merged, merged[1:]):
        if s0 >= TWO_PI:
            break
        if s1 - e0 > 1e-12:
            arcs.append({"width": float(s1 - e0), "center": float((e0 + s1) / 2.0 % TWO_PI),
                         "left": float(e0 % TWO_PI), "right": float(s1 % TWO_PI),
                         "blockers": sorted(b0 | b1)})
    if not arcs:
        return {**zero, "n_ahead": len(ahead), "why_zero": "no free arc"}

    v_lat = v_att - float(v_att @ fwd) * fwd
    ref_bearing = (float(np.arctan2(float(v_lat @ w), float(v_lat @ u)))
                   if float(np.linalg.norm(v_lat)) > 1e-12 else 0.0)

    def _angdist(a, b):
        d = abs(a - b) % TWO_PI
        return min(d, TWO_PI - d)

    def _key(g):
        dir_z = float(np.cos(g["center"]) * u[2] + np.sin(g["center"]) * w[2])
        return (-round(g["width"] / _Q), round(_angdist(g["center"], ref_bearing) / _Q),
                -round(dir_z / _Q), g["center"])

    sel = min(arcs, key=_key)
    direction = np.cos(sel["center"]) * u + np.sin(sel["center"]) * w
    ws = sorted((a["width"] for a in arcs), reverse=True)
    return {"a_route": spec.route_gain * float(a_lat_max) * direction,
            "n_ahead": len(ahead), "n_gaps": len(arcs), "arcs": arcs,
            "selected_center": sel["center"], "selected_width": sel["width"],
            "selected_blockers": sel["blockers"],
            "g1": float(ws[0]), "g2": float(ws[1]) if len(ws) > 1 else None,
            "delta_g": float(ws[0] - ws[1]) if len(ws) > 1 else None,
            "why_zero": None}


def _replay(st, s, policy, spec):
    env = st.env
    _fresh(env)
    rows, orig_step = [], env.step
    back = env.backend
    orig_att = back._attacker
    pending: list = []

    def wrapped(p_att, v_att, **kw):
        d: dict = {}
        out = orig_att(p_att, v_att, diag=d, **kw)
        pending.append(d)
        return out

    def step(*a, **k):
        lims, fin, att = env._states()
        p, v = env._p(att).copy(), env._v(att).copy()
        lp = [env._p(x).copy() for x in lims]
        fa = free_arcs(spec, p, v, lp, env.kill_radius, env.adv_a_max,
                       env.layout.target)
        rows.append({"t": int(env._step_i), "p": p, "v": v, "arc": fa})
        out = orig_step(*a, **k)
        rows[-1]["diag"] = pending[-1] if pending else None
        return out

    back._attacker, env.step = wrapped, step
    try:
        r = run_episode(env, st.scn, st.lay, seed=SEED0 + s, policy=policy,
                        scripted_roles=("finisher",), fire_mode="clean")
    finally:
        back._attacker, env.step = orig_att, orig_step
    return r, rows


def classify(a, b):
    """docs/101 §4 — 후보 집합이 같은가, top-2 순위가 뒤집혔는가."""
    if a["n_ahead"] != b["n_ahead"]:
        return "101-B", f"n_ahead {a['n_ahead']} -> {b['n_ahead']}"
    if a["n_gaps"] != b["n_gaps"]:
        return "101-B", f"n_gaps {a['n_gaps']} -> {b['n_gaps']}"
    ca = sorted(x["center"] for x in a["arcs"])
    cb = sorted(x["center"] for x in b["arcs"])
    if not ca:
        return "101-N", "no arcs"
    shift = max(min(abs(x - y) % TWO_PI, TWO_PI - abs(x - y) % TWO_PI)
                for x, y in zip(ca, cb))
    if shift > CENTER_TOL:
        return "101-B", f"max center shift {shift:.3f} rad > {CENTER_TOL}"
    # 같은 후보 집합 -> 최광폭 arc 의 정체가 바뀌었는가 (순위 교차)
    wa = max(a["arcs"], key=lambda x: x["width"])
    wb = max(b["arcs"], key=lambda x: x["width"])
    dc = abs(wa["center"] - wb["center"]) % TWO_PI
    dc = min(dc, TWO_PI - dc)
    if dc > CENTER_TOL:
        return "101-A", f"argmax arc center moved {dc:.3f} rad (same candidate set)"
    return "101-N", f"same candidate set, argmax unchanged (center shift {dc:.4f})"


def audit(s, g, group, cells, sls):
    kw = scenario_kwargs(s, cells, sls)[5]
    spec = kw["attacker"]
    plan = np.asarray(g["plan"], float)
    fire = int(g["fire_step"])
    tw = (RHO_N * fire) // RHO_D
    sa = build_m4_env(SEED0, s, **kw)
    horizon = int(sa.lay.episode_len)
    r_ref, ref = _replay(sa, s, _plan_policy(sa.env, plan, horizon), spec)
    sb = build_m4_env(SEED0, s, **kw)
    r_br, br = _replay(sb, s, _withdraw_policy(sb.env, plan, horizon, tw, None), spec)
    if (r_ref.label, r_ref.fire_step, r_ref.steps) != (g["label"], g["fire_step"],
                                                       g["steps"]):
        return {"s": s, "ok": False, "why": "reference parity"}

    A = {x["t"]: x for x in ref}
    B = {x["t"]: x for x in br}
    # ── GO gate: 재구성 == diag (전 tick, 양 궤적) ──────────────────────────
    worst, n_chk = 0.0, 0
    for src in (A, B):
        for t, x in src.items():
            if x["diag"] is None:
                continue
            err = float(np.linalg.norm(np.asarray(x["arc"]["a_route"], float)
                                       - np.asarray(x["diag"]["route_req"], float)))
            worst = max(worst, err)
            n_chk += 1
    if worst > GO_TOL:
        return {"s": s, "ok": False, "why": "GO gate", "max_err": worst,
                "n_checked": n_chk}

    # ── divergence tick = route 방향이 처음 FLIP_RAD 이상 갈린 tick ──────────
    flip_t, rows = None, []
    for t in range(tw, fire + 1):
        if t not in A or t not in B:
            continue
        ra = np.asarray(A[t]["arc"]["a_route"], float)
        rb = np.asarray(B[t]["arc"]["a_route"], float)
        na, nb = float(np.linalg.norm(ra)), float(np.linalg.norm(rb))
        ang = (None if na < 1e-12 or nb < 1e-12 else
               float(np.arccos(np.clip(float(ra @ rb) / (na * nb), -1.0, 1.0))))
        rows.append({"t": t, "fire_off": t - fire, "route_angle": ang,
                     "n_ahead": [A[t]["arc"]["n_ahead"], B[t]["arc"]["n_ahead"]],
                     "n_gaps": [A[t]["arc"]["n_gaps"], B[t]["arc"]["n_gaps"]],
                     "delta_g_ref": A[t]["arc"]["delta_g"],
                     "g1_ref": A[t]["arc"]["g1"], "g2_ref": A[t]["arc"]["g2"],
                     "why_zero": [A[t]["arc"]["why_zero"], B[t]["arc"]["why_zero"]]})
        if flip_t is None and ang is not None and ang > FLIP_RAD:
            flip_t = t
    out = {"s": s, "ok": True, "group": group, "fire_step": fire, "t_withdraw": tw,
           "go_max_err": worst, "n_checked": n_chk, "flip_t": flip_t, "rows": rows}
    if flip_t is not None:
        pre = flip_t - 1
        out["branch"], out["why"] = classify(A[flip_t]["arc"], B[flip_t]["arc"])
        out["at_flip"] = {"ref": A[flip_t]["arc"], "br": B[flip_t]["arc"]}
        out["pre_flip"] = ({"ref": A[pre]["arc"], "br": B[pre]["arc"]}
                           if pre in A and pre in B else None)
        out["delta_g_pre_flip"] = (A[pre]["arc"]["delta_g"] if pre in A else None)
    else:
        out["branch"], out["why"] = "101-N", "no flip in window"
    return out


def _clean(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    return o


def main():
    cells, sls = _cells(), _slices()
    geom = load_geom()
    grp = {d["s"]: d["group"]
           for d in json.loads(DIAG.read_text(encoding="utf-8"))["records"]}
    t0, recs = time.time(), []
    for i, (s, gname) in enumerate(sorted(grp.items()), 1):
        recs.append(audit(s, geom[s], gname, cells, sls))
        if i % 15 == 0:
            print(f"  {i}/{len(grp)} ({(time.time()-t0)/i:.1f} s/scn)", flush=True)

    ok = [r for r in recs if r["ok"]]
    excl = [{k: r[k] for k in ("s", "why", "max_err") if k in r}
            for r in recs if not r["ok"]]
    summ = {}
    for gname in ("RET_noeffect", "LOST", "RET_effect"):
        sub = [r for r in ok if r["group"] == gname]
        if not sub:
            continue
        br = {}
        for r in sub:
            br[r["branch"]] = br.get(r["branch"], 0) + 1
        dg = [r["delta_g_pre_flip"] for r in sub
              if r.get("delta_g_pre_flip") is not None]
        na = [r["at_flip"]["ref"]["n_ahead"] - r["at_flip"]["br"]["n_ahead"]
              for r in sub if r.get("at_flip")]
        summ[gname] = {
            "n": len(sub), "branches": br,
            "n_flip": sum(r["flip_t"] is not None for r in sub),
            "delta_g_pre_flip_median": float(np.median(dg)) if dg else None,
            "delta_g_pre_flip_min": float(np.min(dg)) if dg else None,
            "n_ahead_changed_at_flip": int(sum(x != 0 for x in na)),
        }
    out = {"doc": "docs/101", "evidence_grade": "exploratory",
           "go_tol": GO_TOL, "flip_rad": FLIP_RAD, "center_tol": CENTER_TOL,
           "n_excluded": len(excl), "excluded": excl, "summary": summ,
           "vocabulary": "behavior-mediated cooperative geometry under sealed A2 — "
                         "NOT physics-only",
           "records": _clean(recs)}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float),
                   encoding="utf-8")

    gm = max((r["go_max_err"] for r in ok), default=None)
    print(f"\nok {len(ok)}/{len(recs)} · 제외 {len(excl)} {excl[:3]}")
    print(f"GO gate: 재구성 vs diag 최대 오차 {gm:.2e} (허용 {GO_TOL:.0e})")
    for gname, v in summ.items():
        print(f"\n[{gname}] n={v['n']}  flip {v['n_flip']}/{v['n']}  {v['branches']}")
        print(f"  flip 직전 delta_g  median {v['delta_g_pre_flip_median']}  "
              f"min {v['delta_g_pre_flip_min']}")
        print(f"  flip tick 에 n_ahead 가 달라진 판: "
              f"{v['n_ahead_changed_at_flip']}/{v['n']}")


if __name__ == "__main__":
    main()
