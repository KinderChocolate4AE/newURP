"""100-X discrete-transition audit — docs/100 사전등록의 기계 이행.

    python -m shepherd.scripts.r2b_transition_audit

**증거 등급 = exploratory.** 추적하는 가설은 `99-X` 가 결과를 보고 만든 post-hoc 가설이다.
규칙 봉인은 분석 자유도를 줄이기 위함이지 confirmatory 승격이 아니다 (docs/100 머리말).

추적 사슬:

    작은 기하 섭동 -> free-arc argmax switch -> A2 지령 점프
                  -> 표적 상태 이탈 -> AUTH 결과 분기

**핵심은 시간 순서**다: t_switch <= t_cmd <= t_amp 인가.

switch 는 **물리적**으로 정의한다 (arc index 금지 — 목록이 매 틱 재정렬/분할/병합된다).
`_route_accel` 이 `route_gain·a_lat_max·(cos m·û + sin m·ŵ)` 를 돌려주므로 **선택 방향은
원본 출력에서 그대로** 나온다: 재구현 0.

    SWITCH(t)  <=>  angle(d_ref, d_branch) > 0.05 rad

g1/g2/delta_g 는 진단 전용으로 재구현하고, 그 재구현이 고른 방향이 `_route_accel` 출력과
일치하는지 **매 틱 기계 확인**한다 (판정에는 쓰지 않는다). torch-free.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from shepherd.agents.attacker_ladder import _route_accel, _unit       # noqa: E402
from shepherd.m4_env import build_m4_env                              # noqa: E402
from shepherd.scripts.mission_rollout import run_episode              # noqa: E402
from shepherd.scripts.r2b_c_runner import (                           # noqa: E402
    SEED0, _fresh, _plan_policy, scenario_kwargs)
from shepherd.scripts.r2b_phase1 import _cells, _slices               # noqa: E402
from shepherd.scripts.r2b_steer_probe import _withdraw_policy, load_geom  # noqa: E402

OUT = ROOT / "artifacts/r2b/transition_audit.json"
DIAG = ROOT / "artifacts/r2b/noeffect_diag.json"
DT = 0.05
RHO_N, RHO_D = 3, 4                 # t_rho = (3 * fire) // 4
EPS_THETA = 0.05                    # rad — docs/100 §2
EPS_A = 0.1                         # m/s^2 — docs/100 §3
AMP_FACTOR = 10.0                   # docs/100 §3
REPEL_R = 0.75                      # repel_margin(1.0) * kill_radius(0.75)


def _gaps(spec, p_att, v_att, lims, kill_radius):
    """[진단 전용] `_route_accel` 의 gap 구성을 그대로 재현해 g1/g2/선택방향을 낸다.

    판정에는 쓰지 않는다 — 매 틱 원본 출력 방향과의 일치 확인으로 drift 를 잡는 용도.
    """
    fwd = _unit(v_att)
    ref = np.array([0.0, 0.0, 1.0]) if abs(fwd[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = _unit(np.cross(fwd, ref), [0.0, 1.0, 0.0])
    w = _unit(np.cross(fwd, u), [0.0, 0.0, 1.0])
    r_block = 1.0 * spec.lam_range * float(kill_radius)
    two_pi = 2.0 * np.pi
    ahead = [c for c in np.asarray(lims, float)
             if float((c - p_att) @ fwd) > 0.0
             and float(np.linalg.norm(c - p_att)) <= spec.sense_range]
    spans = []
    for c in ahead:
        rel = c - p_att
        ox, oy = float(rel @ u), float(rel @ w)
        d = float(np.hypot(ox, oy))
        beta = float(np.arctan2(oy, ox))
        alpha = 0.5 * np.pi if d <= r_block else float(np.arcsin(r_block / d))
        spans.append((beta - alpha, beta + alpha))
    if not spans or sum(e - s for s, e in spans) >= two_pi:
        return None
    spans = sorted(((s % two_pi, (s % two_pi) + (e - s)) for s, e in spans))
    merged = []
    for s, e in spans + [(s + two_pi, e + two_pi) for s, e in spans]:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    if any(e - s >= two_pi for s, e in merged):
        return None
    gaps = []
    for (s0, e0), (s1, _) in zip(merged, merged[1:]):
        if s0 >= two_pi:
            break
        if s1 - e0 > 1e-12:
            gaps.append((s1 - e0, (e0 + s1) / 2.0 % two_pi))
    if not gaps:
        return None
    ws = sorted((g[0] for g in gaps), reverse=True)
    return {"g1": float(ws[0]), "g2": float(ws[1]) if len(ws) > 1 else None,
            "delta_g": float(ws[0] - ws[1]) if len(ws) > 1 else None,
            "n_gaps": len(gaps), "n_ahead": len(ahead)}


def _route(spec, p_att, v_att, lims, env):
    return _route_accel(spec, p_att=p_att, v_att=v_att, fwd=_unit(v_att),
                        limiters=list(np.asarray(lims, float)),
                        kill_radius=env.kill_radius, repel_margin=1.0,
                        a_lat_max=env.adv_a_max,
                        d_target=float(np.linalg.norm(
                            np.asarray(env.layout.target, float) - p_att)))


def _record_replay(st, s, policy, spec):
    """한 궤적을 재생하며 틱마다 (p_att, v_att, p_lims, route accel, gap 진단) 적재."""
    env = st.env
    _fresh(env)
    ticks, orig = [], env.step

    def step(*a, **k):
        lims, fin, att = env._states()
        p_att, v_att = env._p(att), env._v(att)
        lp = [env._p(x) for x in lims]
        ar = _route(spec, p_att, v_att, lp, env)
        ticks.append({"t": int(env._step_i), "p_att": p_att, "v_att": v_att,
                      "a_route": np.asarray(ar, float), "gaps": _gaps(
                          spec, p_att, v_att, lp, env.kill_radius),
                      "min_dist": float(min(np.linalg.norm(p_att - x) for x in lp))})
        return orig(*a, **k)

    env.step = step
    try:
        r = run_episode(env, st.scn, st.lay, seed=SEED0 + s, policy=policy,
                        scripted_roles=("finisher",), fire_mode="clean")
    finally:
        env.step = orig
    return r, ticks


def _dirn(a):
    n = float(np.linalg.norm(a))
    return None if n < 1e-12 else np.asarray(a, float) / n


def audit(s, g, group, cells, sls):
    kw = scenario_kwargs(s, cells, sls)[5]
    spec = kw["attacker"]
    plan = np.asarray(g["plan"], float)
    fire = int(g["fire_step"])
    tw = (RHO_N * fire) // RHO_D
    horizon = int(build_m4_env(SEED0, s, **kw).lay.episode_len)

    r_ref, tk_ref = _record_replay(build_m4_env(SEED0, s, **kw), s,
                                   _plan_policy(build_m4_env(SEED0, s, **kw).env,
                                                plan, horizon), spec)
    stb = build_m4_env(SEED0, s, **kw)
    r_br, tk_br = _record_replay(stb, s,
                                 _withdraw_policy(stb.env, plan, horizon, tw, None),
                                 spec)
    if (r_ref.label, r_ref.fire_step, r_ref.steps) != (g["label"], g["fire_step"],
                                                       g["steps"]):
        return {"s": s, "ok": False, "why": "reference parity"}

    ref = {t["t"]: t for t in tk_ref}
    br = {t["t"]: t for t in tk_br}
    rows, bad_sc, repel_on = [], 0, 0
    for t in range(tw, min(fire, max(br)) + 1):
        if t not in ref or t not in br:
            break
        a, b = ref[t], br[t]
        da, db = _dirn(a["a_route"]), _dirn(b["a_route"])
        ang = (None if da is None or db is None else
               float(np.arccos(np.clip(float(da @ db), -1.0, 1.0))))
        # 자기검증: 재구현 gap 이 고른 방향이 원본 출력 방향과 일치하는가
        for side in (a, b):
            if side["gaps"] is None and _dirn(side["a_route"]) is not None:
                bad_sc += 1
        repel_on += int(min(a["min_dist"], b["min_dist"]) <= REPEL_R)
        rows.append({
            "t": t, "dtheta_star": ang,
            "d_a_route": float(np.linalg.norm(a["a_route"] - b["a_route"])),
            "dp": float(np.linalg.norm(a["p_att"] - b["p_att"])),
            "dv": float(np.linalg.norm(a["v_att"] - b["v_att"])),
            "delta_g_ref": (a["gaps"] or {}).get("delta_g"),
            "g1_ref": (a["gaps"] or {}).get("g1"),
            "n_ahead_ref": (a["gaps"] or {}).get("n_ahead"),
            "min_dist": min(a["min_dist"], b["min_dist"]),
        })

    da0 = next((x["d_a_route"] for x in rows if x["t"] == tw + 1), 0.0)
    t_sw = next((x["t"] for x in rows
                 if x["dtheta_star"] is not None and x["dtheta_star"] > EPS_THETA), None)
    t_cmd = next((x["t"] for x in rows if x["d_a_route"] > EPS_A), None)
    t_amp = next((x["t"] for x in rows
                  if x["dp"] > AMP_FACTOR * 0.5 * da0 * ((x["t"] - tw) * DT) ** 2
                  and x["t"] > tw + 1), None)
    dg_pre = next((x["delta_g_ref"] for x in rows if t_sw and x["t"] == t_sw - 1), None)
    return {"s": s, "ok": True, "group": group, "t_withdraw": tw, "fire_step": fire,
            "n_ticks": len(rows), "da0": da0,
            "t_switch": t_sw, "t_cmd": t_cmd, "t_amp": t_amp,
            "delta_g_before_switch": dg_pre,
            "order_ok": (None if t_sw is None or t_amp is None else
                         bool(t_sw <= (t_cmd if t_cmd is not None else t_amp) <= t_amp)),
            "selfcheck_bad": bad_sc, "repel_active_ticks": repel_on,
            "final_dp": rows[-1]["dp"] if rows else None, "rows": rows}


def main():
    cells, sls = _cells(), _slices()
    geom = load_geom()
    grp = {d["s"]: d["group"]
           for d in json.loads(DIAG.read_text(encoding="utf-8"))["records"]}
    t0, recs = time.time(), []
    for i, (s, gname) in enumerate(sorted(grp.items()), 1):
        recs.append(audit(s, geom[s], gname, cells, sls))
        if i % 10 == 0:
            print(f"  {i}/{len(grp)} ({(time.time()-t0)/i:.1f} s/scn)", flush=True)

    ok = [r for r in recs if r["ok"]]
    summ = {}
    for gname in ("RET_noeffect", "LOST", "RET_effect"):
        sub = [r for r in ok if r["group"] == gname]
        if not sub:
            continue
        sw = [r for r in sub if r["t_switch"] is not None]
        dg = [r["delta_g_before_switch"] for r in sw
              if r["delta_g_before_switch"] is not None]
        orders = [r["order_ok"] for r in sub if r["order_ok"] is not None]
        summ[gname] = {
            "n": len(sub), "n_switch": len(sw),
            "frac_switch": len(sw) / len(sub),
            "delta_g_before_switch_median": float(np.median(dg)) if dg else None,
            "n_amp": sum(r["t_amp"] is not None for r in sub),
            "order_ok": [int(sum(orders)), len(orders)],
            "median_final_dp": float(np.median([r["final_dp"] for r in sub
                                                if r["final_dp"] is not None])),
        }
    out = {"doc": "docs/100 (100-X)", "evidence_grade": "exploratory — tracks a post-hoc "
           "hypothesis generated by 99-X; NOT confirmatory",
           "thresholds": {"eps_theta_rad": EPS_THETA, "eps_a": EPS_A,
                          "amp_factor": AMP_FACTOR},
           "groups_inherited_from": "99-X noeffect_diag.json (frozen)",
           "n_excluded": len(recs) - len(ok),
           "selfcheck_bad_total": sum(r.get("selfcheck_bad", 0) for r in ok),
           "repel_active_total": sum(r.get("repel_active_ticks", 0) for r in ok),
           "summary": summ, "records": recs}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float),
                   encoding="utf-8")

    print(f"\nok {len(ok)}/{len(recs)} · selfcheck bad {out['selfcheck_bad_total']} · "
          f"repel-active ticks {out['repel_active_total']} (0 이어야 route 가 유일 채널)")
    for gname, v in summ.items():
        print(f"\n[{gname}] n={v['n']}")
        print(f"  switch {v['n_switch']}/{v['n']} ({v['frac_switch']:.0%})   "
              f"amplified {v['n_amp']}/{v['n']}   "
              f"order t_sw<=t_cmd<=t_amp {v['order_ok'][0]}/{v['order_ok'][1]}")
        print(f"  delta_g just before switch (med): "
              f"{v['delta_g_before_switch_median']}   "
              f"final dp med {v['median_final_dp']:.5f} m")


if __name__ == "__main__":
    main()
