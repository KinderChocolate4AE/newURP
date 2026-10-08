"""E7-a — ①축 net 물리 프로브 격자 (docs/129 §2; 학습·세계 변경 없음 — 판정 재계산).

    IN=/data/hjhong/l2 python scripts/fs1_e7_probe.py \
        --stage1 $IN/e3_in/stage1 --e3b $IN/e3b_in/phase1 --out-dir artifacts/fs1/e7a

1.5a 프로토콜 (m0.35_n1 고정, 4 적응 공격자 × 24 ep, SEED0 268000, 발사 금지) 의 같은
rollout 위에서, 매 window tick 에 12 변형 (τ{1,.7,.5} × θ{1,1.5} × 조준{cv,ma}) 의 judge
를 paired 재계산한다. 비발사 rollout 에서 세 손잡이는 전부 judge 호출 인자이므로 세계
변경이 필요 없다 (JAX 설계 메모 §1 와 합치).

선언 (manifest `fs1_e7_manifest.py` 와 함께 봉인):
- 조준: cv = nc = p_att + v·τ_v (현행 외삽). ma = + ½·â·τ_v², â = (v_t − v_{t−1})/dt,
  ‖â‖ ≤ a_att_max clip (첫 tick â=0). 콘 축 n_F = unit(nc − p_fin) — **즉시 조준 근사**
  (포탑 slew 무시 = 낙관 상한, 선별용; 기준 변형 vs rollout-축 anchor 로 근사 오차 정량).
- ρ(변형) = d*·tan(θ_v) / (½·a_att·τ_v²), d* = cone_range_max (runtime 기록). 절대값은
  d* 관례 의존 — 단조성·상대비만 사용 (A.1 의 1.6 과 절대 비교 금지).
- wiring 자기검증: (τ1, θ1, n_F = rollout e_fin) 직접 호출이 inn._vshot 과 bit-exact.
"""
from __future__ import annotations

import argparse
import itertools
import json
import pathlib

import numpy as np

CELL, MU, NU = "m0.35_n1", 0.35, 1.0
ATTACKERS = {"ex_kfirst50": ("stage1", "exploit_kfirst50", "kfirst50"),
             "ex_fin12_fb": ("stage1", "exploit_fin12_fb", "fin12_fb"),
             "ex_mix5050": ("e3b", "exploit_mix5050", "mix5050"),
             "ex_kfirst_rand": ("e3b", "exploit_kfirst_rand", "kfirst_rand")}
WINDOW_D = 16.0
EPS = 24
SEED0 = 268000
TS, HS, AIMS = (1.0, 0.7, 0.5), (1.0, 1.5), ("cv", "ma")
VARIANTS = [(f"t{t}_h{h}_{a}", t, h, a) for t, h, a in itertools.product(TS, HS, AIMS)]
CRIT_STEPS = 4            # E7-b 진입: 변형 창 중앙값 (4 slot 중앙값들의 중앙값) >= 4 step


def _robust(v):
    return bool(v.v_shot_worst >= 1.0 and not v.boxed_in)


def _max_run(flags):
    best = run = 0
    for f in flags:
        run = run + 1 if f else 0
        best = max(best, run)
    return best


def run_slot(name, root, sub, dfd, eps):
    import torch as T
    from shepherd.fs1.eval import _ep_kf_r
    from shepherd.fs1.train import _team, ATT_ROLES, DISC_IN, att_action, scripted_def_actions
    from shepherd.fs1.world import FS1Env, FS1Spec, Z_DIM
    from shepherd.game import viability as V

    env = FS1Env(FS1Spec(mu=MU, nu=NU), seed=0)
    obs_dim = len(env.reset(seed=0)[0]["finisher_0"])
    snap = T.load(root / CELL / sub / "ckpt.pt", weights_only=False)["teams"]["att"]
    team = _team(ATT_ROLES, snap, obs_dim + Z_DIM, disc=(DISC_IN, Z_DIM))
    inn = env.inner
    tau0, th0 = float(inn.tau_deploy), float(inn.cone_half_angle)
    rmin, rmax, dt = float(inn.cone_range_min), float(inn.cone_range_max), float(inn.dt)
    a_att = float(inn.a_att_max)

    per_ep = {vn: {"steps": [], "run": []} for vn, *_ in VARIANTS}
    rows = {f"{vn}.rb": [] for vn, *_ in VARIANTS}
    rows.update({"ep": [], "step": [], "anchor_rb": [], "agree_cv11": []})
    checked = 0
    for i in range(eps):
        s = SEED0 + i
        np.random.seed(s)
        kf_r = _ep_kf_r(dfd, s)
        obs, _ = env.reset(seed=s)
        done, v_prev = False, None
        flags = {vn: [] for vn, *_ in VARIANTS}
        while not done:
            o = obs["finisher_0"]
            acts = scripted_def_actions(env, kf_r)
            acts["finisher_0"][4] = 0.0                    # ★ 발사 금지 (LOADED 유지)
            acts["adversary_0"] = att_action(team.act(env.att_obs(o))[0], env)
            lims, fin, att = inn._states()
            p_att, v_att = inn._p(att), inn._v(att)
            p_fin = inn._p(fin)
            d = float(np.linalg.norm(p_att - p_fin))
            ahat = np.zeros(3) if v_prev is None else (v_att - v_prev) / dt
            if (n := np.linalg.norm(ahat)) > a_att:
                ahat = ahat * (a_att / n)
            if inn.fsm.state.value == "LOADED" and d <= WINDOW_D:
                lim_ps = [inn._p(l) for l in lims]
                sd = inn._seed * 100003 + inn._step_i
                base = inn._vshot(p_att, v_att, lim_ps, fin, seed=sd)
                com = dict(a_att_max=a_att, limiters=lim_ps, kill_radius=inn.kill_radius,
                           n=inn.n_samples, n_segments=inn.n_segments, seed=sd,
                           judge="se3_cone", net_apex=p_fin, range_min=rmin, range_max=rmax)
                if checked < 3:                            # wiring (rollout 축) bit-exact
                    chk = V.v_shot(p_att, v_att, tau=tau0, theta_net=th0,
                                   n_F=inn._e(fin), **com)
                    assert (chk.v_shot_soft, chk.v_shot_worst, chk.p_feasible,
                            chk.boxed_in) == (base.v_shot_soft, base.v_shot_worst,
                                              base.p_feasible, base.boxed_in), \
                        f"direct v_shot != inn._vshot at {name} ep{i}"
                    checked += 1
                rows["ep"].append(i); rows["step"].append(inn._step_i)
                rows["anchor_rb"].append(_robust(base))
                for vn, ts, hs, aim in VARIANTS:
                    tv = tau0 * ts
                    nc = p_att + v_att * tv + (0.5 * ahat * tv * tv if aim == "ma" else 0.0)
                    ax = nc - p_fin
                    nrm = np.linalg.norm(ax)
                    n_F = ax / nrm if nrm > 1e-9 else inn._e(fin)
                    r = V.v_shot(p_att, v_att, tau=tv, theta_net=th0 * hs, n_F=n_F, **com)
                    rb = _robust(r)
                    rows[f"{vn}.rb"].append(rb)
                    flags[vn].append(rb)
                rows["agree_cv11"].append(rows["t1.0_h1.0_cv.rb"][-1] == rows["anchor_rb"][-1])
            obs, _, done, info = env.step(acts)
            v_prev = v_att
        for vn in flags:
            per_ep[vn]["steps"].append(int(sum(flags[vn])))
            per_ep[vn]["run"].append(_max_run(flags[vn]))

    consts = {"tau0": tau0, "theta0": th0, "range_max": rmax, "a_att": a_att, "dt": dt}
    summ = {vn: {"steps_med": float(np.median(p["steps"])),
                 "max_run_med": float(np.median(p["run"])),
                 "eps_with_window": int(sum(x > 0 for x in p["steps"]))}
            for vn, p in per_ep.items()}
    summ["_anchor"] = {"window_ticks": len(rows["ep"]),
                       "aim_approx_agree": (round(float(np.mean(rows["agree_cv11"])), 4)
                                            if rows["agree_cv11"] else None)}
    print(CELL, name, json.dumps(summ["_anchor"]), flush=True)
    return consts, summ, {k: np.asarray(v) for k, v in rows.items()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage1", required=True)
    ap.add_argument("--e3b", required=True)
    ap.add_argument("--out-dir", default="artifacts/fs1/e7a")
    ap.add_argument("--eps", type=int, default=EPS)
    a = ap.parse_args()
    roots = {"stage1": pathlib.Path(a.stage1), "e3b": pathlib.Path(a.e3b)}
    out_dir = pathlib.Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    slots, npz, consts = {}, {}, None
    for name, (rk, sub, dfd) in ATTACKERS.items():
        consts, summ, rows = run_slot(name, roots[rk], sub, dfd, a.eps)
        slots[name] = summ
        for k, v in rows.items():
            npz[f"{name}.{k}"] = v
    np.savez_compressed(out_dir / "rows.npz", **npz)

    rho, variant_med = {}, {}
    for vn, ts, hs, aim in VARIANTS:
        tv, thv = consts["tau0"] * ts, consts["theta0"] * hs
        rho[vn] = round(consts["range_max"] * np.tan(thv) / (0.5 * consts["a_att"] * tv * tv), 3)
        variant_med[vn] = float(np.median([slots[s][vn]["steps_med"] for s in ATTACKERS]))
    rs = np.array([rho[vn] for vn, *_ in VARIANTS])
    ws = np.array([variant_med[vn] for vn, *_ in VARIANTS])
    def _rank(x):
        o = np.argsort(np.argsort(x, kind="mergesort"), kind="mergesort")
        return o.astype(float)
    spear = (float(np.corrcoef(_rank(rs), _rank(ws))[0, 1])
             if len(set(rs)) > 1 and len(set(ws)) > 1 else None)
    promoted = [vn for vn, *_ in VARIANTS if variant_med[vn] >= CRIT_STEPS]
    report = {
        "schema": "fs1-e7a-probe-v1", "seed0": SEED0, "cell": CELL, "consts": consts,
        "caveats": ["구세계 적응 공격자 (비공진화) — 낙관 편향, 선별용만",
                    "즉시 조준 근사 (포탑 slew 무시) — anchor agree 로 오차 정량",
                    "양성 판정은 E7-b (신세계 전용 착취자) 만"],
        "rho": rho, "variant_window_med": variant_med,
        "p_rho1": {"criterion": "Spearman(rho, window_med) >= 0.7", "spearman": spear,
                   "verdict": (None if spear is None else
                               "P_RHO1_SUPPORTED" if spear >= 0.7 else "P_RHO1_NOT_SUPPORTED")},
        "e7b_entry": {"criterion": f"variant window med (4-slot med-of-med) >= {CRIT_STEPS}",
                      "promoted": promoted},
        "anchor": {s: slots[s]["_anchor"] for s in ATTACKERS},
        "slots": slots,
    }
    (out_dir / "probe.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("promoted:", promoted, "| spearman:", spear)
    print("->", out_dir / "probe.json")


if __name__ == "__main__":
    main()
