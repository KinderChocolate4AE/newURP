"""E3b-1.5a — 포획-판정 점유율 측정 (보고 전용, 학습 없음; 노트 2026-10-06a §6 사다리 ③의 상한 probe).

    python scripts/fs1_viab_occupancy.py --stage1 /data/hjhong/l2/e3_in/stage1 \
        --e3b /data/hjhong/l2/e3b_in/phase1 --out artifacts/fs1/e3b/occupancy.json

질문: 적응 공격자의 접근 동안, robust 포획 조건 (v_shot_worst ≥ 1 ∧ ¬boxed_in) 이 성립하는
step 이 존재하는가. finisher 는 **발사하지 않고** (LOADED 유지) 교전 창 (d ≤ 16 m) 의 매 step
판정을 조회한다. limiter 는 그 공격자가 학습한 상대 scripted 와 같은 규칙.
caveat (기록): 공격자는 발사하는 방어를 상대로 학습했으므로 비발사 궤적은 분포 밖 — 접근
구간은 동일하고, 점유율 ≈ 0 의 해석 (finisher 단독 발사 타이밍으로는 불가) 에는 보수적 방향.
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np

CELLS = [("m0.35_n1", 0.35, 1.0), ("m0.7_n1", 0.7, 1.0), ("m1.4_n1", 1.4, 1.0)]
ATTACKERS = {"ex_kfirst50": ("stage1", "exploit_kfirst50", "kfirst50"),
             "ex_fin12_fb": ("stage1", "exploit_fin12_fb", "fin12_fb"),
             "ex_mix5050": ("e3b", "exploit_mix5050", "mix5050"),
             "ex_kfirst_rand": ("e3b", "exploit_kfirst_rand", "kfirst_rand")}
WINDOW_D = 16.0
EPS = 24
SEED0 = 268000


def run_cell(cell, mu, nu, roots, eps):
    import torch  # noqa: F401
    from shepherd.fs1.eval import _ep_kf_r
    from shepherd.fs1.train import _team, ATT_ROLES, DISC_IN, att_action, scripted_def_actions
    from shepherd.fs1.world import FS1Env, FS1Spec, Z_DIM
    env = FS1Env(FS1Spec(mu=mu, nu=nu), seed=0)
    obs_dim = len(env.reset(seed=0)[0]["finisher_0"])
    out = {}
    for name, (root_key, sub, dfd) in ATTACKERS.items():
        ck = roots[root_key] / cell / sub / "ckpt.pt"
        import torch as T
        snap = T.load(ck, weights_only=False)["teams"]["att"]
        team = _team(ATT_ROLES, snap, obs_dim + Z_DIM, disc=(DISC_IN, Z_DIM))
        occ_eps, occ_steps, win_steps, max_worst, max_soft = 0, 0, 0, [], []
        for i in range(eps):
            s = SEED0 + i
            np.random.seed(s)
            kf_r = _ep_kf_r(dfd, s)
            obs, _ = env.reset(seed=s)
            inn, done, hit, mw, ms = env.inner, False, 0, 0.0, 0.0
            while not done:
                o = obs["finisher_0"]
                acts = scripted_def_actions(env, kf_r)
                acts["finisher_0"][4] = 0.0                     # ★ 발사 금지 (LOADED 유지)
                acts["adversary_0"] = att_action(team.act(env.att_obs(o))[0], env)
                lims, fin, att = inn._states()
                d = float(np.linalg.norm(inn._p(att) - inn._p(fin)))
                if inn.fsm.state.value == "LOADED" and d <= WINDOW_D:
                    v = inn._vshot(inn._p(att), inn._v(att), [inn._p(l) for l in lims], fin,
                                   seed=inn._seed * 100003 + inn._step_i)
                    win_steps += 1
                    mw, ms = max(mw, v.v_shot_worst), max(ms, v.v_shot_soft)
                    if v.v_shot_worst >= 1.0 and not v.boxed_in:
                        hit += 1
                obs, _, done, info = env.step(acts)
            occ_eps += hit > 0; occ_steps += hit
            max_worst.append(mw); max_soft.append(ms)
        out[name] = {"eps": eps, "eps_with_capture_ok": int(occ_eps),
                     "capture_ok_steps": int(occ_steps), "window_steps": int(win_steps),
                     "max_worst_med": round(float(np.median(max_worst)), 3),
                     "max_soft_med": round(float(np.median(max_soft)), 3)}
        print(cell, name, out[name], flush=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage1", required=True)
    ap.add_argument("--e3b", required=True)
    ap.add_argument("--out", default="artifacts/fs1/e3b/occupancy.json")
    ap.add_argument("--eps", type=int, default=EPS)
    a = ap.parse_args()
    roots = {"stage1": pathlib.Path(a.stage1), "e3b": pathlib.Path(a.e3b)}
    res = {cell: run_cell(cell, mu, nu, roots, a.eps) for cell, mu, nu in CELLS}
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"schema": "fs1-e3b-occupancy-v1", "report_only": True,
                               "window_d": WINDOW_D, "seed0": SEED0, "cells": res}, indent=2),
                   encoding="utf-8")
    print("->", out)


if __name__ == "__main__":
    main()
