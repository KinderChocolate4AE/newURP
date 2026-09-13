"""101-X commit/jink transition audit — `100-X` 실패 원인 추적 (post-hoc mechanistic).

    python -m shepherd.scripts.r2b_commit_jink_audit

**지위**: exploratory post-hoc mechanistic diagnostic. 새 claim gate 아님. 사전등록된 큰
분기표 없이 **질문 하나**만 고정한다:

> **`LOST`/`RET_effect` 의 비선형 증폭은 attacker 의 `committed` 전환과 그에 따른 jink
> 가속 불연속으로 설명되는가?**

계측: `_general_action` 이 이미 가진 `diag` 훅을 켠다 (`a_raw` · `clipped` · `a_final` ·
`committed` · `route_req`). **새 계측기를 만들지 않는다.** diag 는 순수 write 이므로
(`if diag is not None: diag.update(...)`) 거동 불변이다.

측정 사슬 — **시뮬레이터 적분 순서에 맞춰** 정렬한다:

    commit divergence -> Δa_final -> Δv_A -> Δp_A

기록 규약: 틱 t 의 diag 는 **그 스텝에 적용될 지령**이고, 틱 t 의 (p, v) 는 **이동 전**
상태다. 따라서 틱 t 의 지령차는 틱 **t+1** 의 상태차로 나타난다 — 같은 틱끼리 비교하면
안 된다 (`100-X` 판독문 13h 가 이 점과 창 길이 혼합 두 가지로 어긋났다).

그룹은 `99-X` 에서 **동결 승계**. 정렬은 **FIRE 기준** (창 길이가 2~5 로 제각각이라
t_w 기준 정렬은 서로 다른 국면을 섞는다). torch-free.
"""
from __future__ import annotations

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
from shepherd.scripts.r2b_steer_probe import _withdraw_policy, load_geom  # noqa: E402

OUT = ROOT / "artifacts/r2b/commit_jink_audit.json"
DIAG = ROOT / "artifacts/r2b/noeffect_diag.json"
RHO_N, RHO_D = 3, 4
DT = 0.05
FIRE_OFFSETS = (-5, -4, -3, -2, -1, 0)


def _replay(st, s, policy):
    """diag 훅을 켜고 재생. 틱마다 (이동 전 p,v) + 그 스텝에 적용될 지령 diag."""
    env = st.env
    _fresh(env)
    rows, orig_step = [], env.step
    back = env.backend
    orig_att = back._attacker
    assert orig_att.__name__ != "_a1", "A1 위임 경로 — diag 훅이 없다"
    pending: list = []

    def wrapped(p_att, v_att, **kw):
        d: dict = {}
        out = orig_att(p_att, v_att, diag=d, **kw)
        pending.append(d)
        return out

    def step(*a, **k):
        lims, fin, att = env._states()
        rows.append({"t": int(env._step_i),
                     "p": env._p(att).copy(), "v": env._v(att).copy()})
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


def audit(s, g, group, cells, sls):
    kw = scenario_kwargs(s, cells, sls)[5]
    plan = np.asarray(g["plan"], float)
    fire, tw = int(g["fire_step"]), (RHO_N * int(g["fire_step"])) // RHO_D
    sa = build_m4_env(SEED0, s, **kw)
    horizon = int(sa.lay.episode_len)
    r_ref, ref = _replay(sa, s, _plan_policy(sa.env, plan, horizon))
    sb = build_m4_env(SEED0, s, **kw)
    r_br, br = _replay(sb, s, _withdraw_policy(sb.env, plan, horizon, tw, None))
    if (r_ref.label, r_ref.fire_step, r_ref.steps) != (g["label"], g["fire_step"],
                                                       g["steps"]):
        return {"s": s, "ok": False, "why": "reference parity"}

    A = {x["t"]: x for x in ref}
    B = {x["t"]: x for x in br}
    rows = []
    for t in range(tw, fire + 1):
        if t not in A or t not in B or A[t]["diag"] is None or B[t]["diag"] is None:
            continue
        da, db = A[t]["diag"], B[t]["diag"]
        ra, rb = (np.asarray(da["route_req"], float),
                  np.asarray(db["route_req"], float))
        af = np.asarray(da["a_final"], float) - np.asarray(db["a_final"], float)
        rq = ra - rb
        na, nb = float(np.linalg.norm(ra)), float(np.linalg.norm(rb))
        # env 자신의 route_req 두 벡터 사이 각도 = 선택된 free-arc 방향의 차이.
        # 재구현 0 (100-X 는 fwd 를 잘못 넣어 다른 함수를 쟀다).
        rang = (None if na < 1e-12 or nb < 1e-12 else
                float(np.arccos(np.clip(float(ra @ rb) / (na * nb), -1.0, 1.0))))
        rows.append({
            "t": t, "fire_off": t - fire,
            "committed_ref": bool(da["committed"]),
            "committed_br": bool(db["committed"]),
            "commit_mismatch": bool(da["committed"] != db["committed"]),
            "clipped_ref": bool(da["clipped"]), "clipped_br": bool(db["clipped"]),
            "clip_mismatch": bool(da["clipped"] != db["clipped"]),
            "d_a_final": float(np.linalg.norm(af)),
            "d_a_route": float(np.linalg.norm(rq)),
            "route_angle_rad": rang,
            "route_norm_ref": na, "route_norm_br": nb,
            # residual = 표적 자신의 나머지 항 (jink / dodge / homing / 전진) 의 기여
            "d_a_residual": float(np.linalg.norm(af - rq)),
            "a_raw_ref": float(da["a_raw"]), "a_raw_br": float(db["a_raw"]),
            "d_p": float(np.linalg.norm(A[t]["p"] - B[t]["p"])),
            "d_v": float(np.linalg.norm(A[t]["v"] - B[t]["v"])),
        })
    return {"s": s, "ok": True, "group": group, "fire_step": fire, "t_withdraw": tw,
            "branch_fire_step": r_br.fire_step, "branch_label": r_br.label,
            "fire_same_tick": bool(r_br.fire_step == fire), "rows": rows}


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

    summ = {}
    for gname in ("RET_noeffect", "LOST", "RET_effect"):
        sub = [r for r in ok if r["group"] == gname]
        if not sub:
            continue
        allr = [x for r in sub for x in r["rows"]]
        prof = {}
        for k in FIRE_OFFSETS:
            sel = [x for x in allr if x["fire_off"] == k]
            if not sel:
                continue
            prof[str(k)] = {
                "n": len(sel),
                "d_a_final": float(np.median([x["d_a_final"] for x in sel])),
                "d_a_route": float(np.median([x["d_a_route"] for x in sel])),
                "d_a_residual": float(np.median([x["d_a_residual"] for x in sel])),
                "d_v": float(np.median([x["d_v"] for x in sel])),
                "d_p": float(np.median([x["d_p"] for x in sel])),
                "route_angle_rad": (lambda v: float(np.median(v)) if v else None)(
                    [x["route_angle_rad"] for x in sel
                     if x["route_angle_rad"] is not None]),
                "n_route_flip_gt_0p5rad": int(sum(
                    (x["route_angle_rad"] or 0) > 0.5 for x in sel)),
                "n_commit_mismatch": int(sum(x["commit_mismatch"] for x in sel)),
                "n_clip_mismatch": int(sum(x["clip_mismatch"] for x in sel)),
            }
        summ[gname] = {
            "n": len(sub),
            "n_fire_same_tick": int(sum(r["fire_same_tick"] for r in sub)),
            "n_any_commit_mismatch": int(sum(any(x["commit_mismatch"] for x in r["rows"])
                                             for r in sub)),
            "n_any_clip_mismatch": int(sum(any(x["clip_mismatch"] for x in r["rows"])
                                           for r in sub)),
            "by_fire_offset": prof,
        }
    out = {"doc": "101-X commit/jink audit", "evidence_grade": "exploratory post-hoc",
           "question": ("is the nonlinear amplification explained by a committed-state "
                        "transition and the resulting jink acceleration discontinuity?"),
           "alignment": "FIRE-relative (window length varies 2..5 ticks)",
           "groups_inherited_from": "99-X (frozen)",
           "n_excluded": len(recs) - len(ok), "summary": summ, "records": recs}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=float),
                   encoding="utf-8")

    print(f"\nok {len(ok)}/{len(recs)}")
    for gname, v in summ.items():
        print(f"\n[{gname}] n={v['n']}  fire 같은틱 {v['n_fire_same_tick']}/{v['n']}  "
              f"commit 불일치 판 {v['n_any_commit_mismatch']}  "
              f"clip 불일치 판 {v['n_any_clip_mismatch']}")
        print("   off |  d_a_final   d_a_route  d_a_resid  | route_ang flip |"
              "     d_v        d_p     | cmt clip")
        for k in FIRE_OFFSETS:
            p = v["by_fire_offset"].get(str(k))
            if not p:
                continue
            ang = p.get("route_angle_rad")
            print(f"  {k:+3d} | {p['d_a_final']:10.5f} {p['d_a_route']:11.5f} "
                  f"{p['d_a_residual']:10.5f}  | "
                  f"{(f'{ang:8.4f}' if ang is not None else '     n/a')} "
                  f"{p['n_route_flip_gt_0p5rad']:3d}/{p['n']:<2d} |"
                  f" {p['d_v']:9.5f} {p['d_p']:10.6f} "
                  f"|  {p['n_commit_mismatch']:2d}  {p['n_clip_mismatch']:2d}")


if __name__ == "__main__":
    main()
