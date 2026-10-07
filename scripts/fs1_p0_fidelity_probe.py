"""P0 — 충실도·조건부 프로브 (docs/126 §4 P0a/P0b; 학습 없음; 선언 = 노트 2026-10-07d).

    IN=/data/hjhong/l2 python scripts/fs1_p0_fidelity_probe.py \
        --stage1 $IN/e3_in/stage1 --e3b $IN/e3b_in/phase1 --out-dir artifacts/fs1/p0

P0a (③축 1점): 1.5a 점유율 프로토콜 (SEED0=268000, 12 slot = 3 cell × 4 적응 공격자,
발사 금지 rollout) 위에서 witness 를 turn-limited 로 바꿔 창 크기를 재측정.
  **판정-모델 변형 선언**: attacker_turn_limited=True 는 **별도 계보** (w_bk / w8) —
  기존 isotropic 수치 (1.5a·phase2 등) 와 pooling 금지. rollout 동역학은 witness 조회와
  무관 (비발사 프로브) 하므로 세 계보는 같은 tick 에서 paired 비교만 한다.
  ω primary (w_bk) = backend slew 실측값 (runtime 조회; witness ⊇ 실제 공격자 →
  보장-포획 하한 의미론 유지). ω=8.0 (w8, params dead 등재값) = 감도 secondary.
  사전 기준 (docs/126): slot 별 "ep 당 robust step 수" 의 중앙값 (창 0 인 ep 포함,
  24 ep) → 12 slot 중앙값들의 중앙값 ≥ 4 step (0.2 s), 계보 = w_bk → ③축 유효.

P0b (창 감지 가능성): 같은 rollout 의 window tick (LOADED ∧ d ≤ 16) 로지스틱 회귀.
  label = robust_base (기존 계보 primary; robust_w_bk secondary), 특징 = d, closing,
  p_feasible(base), limiter-att 거리 4 (정렬). ep 짝=train / 홀=test, slot 별 AUC +
  pooled (보고용). 기술 문턱 (arm C ①/② 배분 참고, 게이트 아님): slot AUC 중앙값 ≥ 0.8.
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
SEED0 = 268000          # 1.5a 와 동일 (paired 참조용; bit-identity 는 주장하지 않음)
OMEGA_DEAD = 8.0        # params env_frozen.adversary_omega_att_max (DEAD 등재값)
CRIT_STEPS = 4          # 사전 기준: w_bk ep-중앙값들의 slot-중앙값 >= 4 step
AUC_NOTE = 0.8          # P0b 기술 문턱 (배분 참고, 게이트 아님)


def _robust(v):
    return bool(v.v_shot_worst >= 1.0 and not v.boxed_in)


def _max_run(flags):
    best = run = 0
    for f in flags:
        run = run + 1 if f else 0
        best = max(best, run)
    return best


def _fit_logit(X, y, l2=1e-3, iters=50):
    Xb = np.hstack([np.ones((len(X), 1)), X])
    w = np.zeros(Xb.shape[1])
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-np.clip(Xb @ w, -30, 30)))
        g = Xb.T @ (p - y) + l2 * w
        H = (Xb * (p * (1 - p) + 1e-6)[:, None]).T @ Xb + l2 * np.eye(Xb.shape[1])
        w -= np.linalg.solve(H, g)
    return w


def _auc(s, y):
    s, y = np.asarray(s, float), np.asarray(y, int)
    n1 = int(y.sum())
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return None
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(len(s), float)
    i, ss = 0, s[order]
    while i < len(ss):                     # 평균 rank (동점 처리)
        j = i
        while j + 1 < len(ss) and ss[j + 1] == ss[i]:
            j += 1
        ranks[order[i:j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def _logit_auc(rows, label_col, feat_cols):
    """ep 짝=train / 홀=test. rows: dict of np arrays."""
    ep = rows["ep"]
    tr, te = ep % 2 == 0, ep % 2 == 1
    X, y = np.stack([rows[c] for c in feat_cols], 1), rows[label_col].astype(float)
    if y[tr].sum() == 0 or y[te].sum() == 0:
        return None
    mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
    Xn = (X - mu) / sd
    w = _fit_logit(Xn[tr], y[tr])
    return _auc(np.hstack([np.ones((te.sum(), 1)), Xn[te]]) @ w, y[te])


def run_slot(cell, mu, nu, name, root, sub, dfd, eps):
    import torch as T
    from shepherd.fs1.eval import _ep_kf_r
    from shepherd.fs1.train import _team, ATT_ROLES, DISC_IN, att_action, scripted_def_actions
    from shepherd.fs1.world import ADV, FS1Env, FS1Spec, Z_DIM
    from shepherd.game import viability as V

    env = FS1Env(FS1Spec(mu=mu, nu=nu), seed=0)
    obs_dim = len(env.reset(seed=0)[0]["finisher_0"])
    snap = T.load(root / cell / sub / "ckpt.pt", weights_only=False)["teams"]["att"]
    team = _team(ATT_ROLES, snap, obs_dim + Z_DIM, disc=(DISC_IN, Z_DIM))
    inn = env.inner
    om_bk = float(inn.backend.by_name(ADV).limits.omega_max)

    rows = {k: [] for k in ("ep", "step", "d", "closing", "p_feas", "ld1", "ld2", "ld3",
                            "ld4", "rb_base", "rb_wbk", "rb_w8")}
    per_ep = {lin: {"steps": [], "run": []} for lin in ("base", "wbk", "w8")}
    checked = 0
    for i in range(eps):
        s = SEED0 + i
        np.random.seed(s)
        kf_r = _ep_kf_r(dfd, s)
        obs, _ = env.reset(seed=s)
        inn, done = env.inner, False
        flags = {lin: [] for lin in ("base", "wbk", "w8")}
        while not done:
            o = obs["finisher_0"]
            acts = scripted_def_actions(env, kf_r)
            acts["finisher_0"][4] = 0.0                    # ★ 발사 금지 (LOADED 유지)
            acts["adversary_0"] = att_action(team.act(env.att_obs(o))[0], env)
            lims, fin, att = inn._states()
            p_att, v_att, e_att = inn._p(att), inn._v(att), inn._e(att)
            p_fin, v_fin = inn._p(fin), inn._v(fin)
            d = float(np.linalg.norm(p_att - p_fin))
            if inn.fsm.state.value == "LOADED" and d <= WINDOW_D:
                lim_ps = [inn._p(l) for l in lims]
                sd = inn._seed * 100003 + inn._step_i
                base = inn._vshot(p_att, v_att, lim_ps, fin, seed=sd)
                kw = dict(tau=inn.tau_deploy, a_att_max=inn.a_att_max, limiters=lim_ps,
                          kill_radius=inn.kill_radius, n=inn.n_samples,
                          n_segments=inn.n_segments, seed=sd,
                          **inn._vshot_kwargs(p_att, v_att, fin))
                if checked < 3:                            # wiring 자기검증 (bit-exact)
                    chk = V.v_shot(p_att, v_att, **kw)
                    assert (chk.v_shot_soft, chk.v_shot_worst, chk.p_feasible,
                            chk.boxed_in) == (base.v_shot_soft, base.v_shot_worst,
                                              base.p_feasible, base.boxed_in), \
                        f"direct v_shot != inn._vshot at {cell}/{name} ep{i}"
                    checked += 1
                wbk = V.v_shot(p_att, v_att, attacker_turn_limited=True,
                               omega_att_max=om_bk, e_att=e_att, **kw)
                w8 = V.v_shot(p_att, v_att, attacker_turn_limited=True,
                              omega_att_max=OMEGA_DEAD, e_att=e_att, **kw)
                ld = np.sort([np.linalg.norm(p - p_att) for p in lim_ps])
                u = (p_fin - p_att) / max(d, 1e-9)
                for k, v in (("ep", i), ("step", inn._step_i), ("d", d),
                             ("closing", float(np.dot(v_att - v_fin, u))),
                             ("p_feas", base.p_feasible), ("ld1", ld[0]), ("ld2", ld[1]),
                             ("ld3", ld[2]), ("ld4", ld[3]),
                             ("rb_base", _robust(base)), ("rb_wbk", _robust(wbk)),
                             ("rb_w8", _robust(w8))):
                    rows[k].append(v)
                flags["base"].append(_robust(base))
                flags["wbk"].append(_robust(wbk))
                flags["w8"].append(_robust(w8))
            obs, _, done, info = env.step(acts)
        for lin in flags:
            per_ep[lin]["steps"].append(int(sum(flags[lin])))
            per_ep[lin]["run"].append(_max_run(flags[lin]))

    rows = {k: np.asarray(v) for k, v in rows.items()}
    summ = {"omega_backend": om_bk, "eps": eps, "window_steps": int(len(rows["ep"]))}
    for lin in ("base", "wbk", "w8"):
        st = per_ep[lin]["steps"]
        summ[lin] = {"steps_med": float(np.median(st)),
                     "max_run_med": float(np.median(per_ep[lin]["run"])),
                     "eps_with_window": int(sum(s > 0 for s in st)),
                     "steps_per_ep": st}
    feat = ("d", "closing", "p_feas", "ld1", "ld2", "ld3", "ld4")
    summ["p0b"] = {"auc_base": _logit_auc(rows, "rb_base", feat),
                   "auc_wbk": _logit_auc(rows, "rb_wbk", feat),
                   "n_pos_base": int(rows["rb_base"].sum()),
                   "n_pos_wbk": int(rows["rb_wbk"].sum())}
    print(cell, name, {k: summ[k] for k in ("base", "wbk", "w8", "p0b")}, flush=True)
    return summ, rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage1", required=True)
    ap.add_argument("--e3b", required=True)
    ap.add_argument("--out-dir", default="artifacts/fs1/p0")
    ap.add_argument("--eps", type=int, default=EPS)
    a = ap.parse_args()
    roots = {"stage1": pathlib.Path(a.stage1), "e3b": pathlib.Path(a.e3b)}
    out_dir = pathlib.Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    slots, npz = {}, {}
    for cell, mu, nu in CELLS:
        for name, (rk, sub, dfd) in ATTACKERS.items():
            summ, rows = run_slot(cell, mu, nu, name, roots[rk], sub, dfd, a.eps)
            slots[f"{cell}/{name}"] = summ
            for k, v in rows.items():
                npz[f"{cell}.{name}.{k}"] = v
    np.savez_compressed(out_dir / "rows.npz", **npz)

    slot_meds = [s["wbk"]["steps_med"] for s in slots.values()]
    med_of_meds = float(np.median(slot_meds))
    aucs = [s["p0b"]["auc_base"] for s in slots.values() if s["p0b"]["auc_base"] is not None]
    report = {
        "schema": "fs1-p0-probe-v1", "report_only": False, "seed0": SEED0,
        "window_d": WINDOW_D, "lineage_note": "w_bk/w8 = turn-limited 별도 계보; "
        "기존 isotropic 수치와 pooling 금지 (docs/126 P0a)",
        "p0a": {"criterion": f"median-of-slot-medians (w_bk, ep당 robust step) >= {CRIT_STEPS}",
                "slot_medians_wbk": slot_meds, "median_of_medians_wbk": med_of_meds,
                "verdict": "AXIS3_VALID" if med_of_meds >= CRIT_STEPS else "AXIS3_NULL"},
        "p0b": {"note": f"기술 문턱 {AUC_NOTE} (배분 참고, 게이트 아님)",
                "slot_auc_base": {k: s["p0b"]["auc_base"] for k, s in slots.items()},
                "auc_base_med": (float(np.median(aucs)) if aucs else None)},
        "slots": slots,
    }
    (out_dir / "probe.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("p0a verdict:", report["p0a"]["verdict"],
          "med_of_meds(wbk) =", med_of_meds,
          "| p0b auc_base_med =", report["p0b"]["auc_base_med"])
    print("->", out_dir / "probe.json")


if __name__ == "__main__":
    main()
