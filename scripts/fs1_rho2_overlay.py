"""P-ρ2 overlay (docs/129 §9, manifest `fs1_e7_manifest.build_e7a3`): 등록 모집단 정합 재계산.

    python scripts/fs1_rho2_overlay.py --dir artifacts/fs1/e7a3

등록 (노트 10-08c): 창 중앙값 = shell 통과 encounter 조건부 robust tick 수 중앙값.
- 변형 v (τ_v, θ_v): r_v = ½·a_att·τ_v², D_min = r_v / sin θ_v, D_max = R_max − r_v (δ = 0).
- tick 의 조준점 c = p_att + v_att·τ_v (witness 구 중심 — 조준 모델 cv/ma 와 무관), D = |c − p_fin|.
- encounter = episode. shell 통과 = window tick 중 하나라도 D ∈ [D_min, D_max].
- 창 = 그 episode 의 robust tick 수 (변형 v 판정). 4 slot 의 shell 통과 episode 를 합쳐 중앙값.
- 예측: N_pred = N∞·(1 − ρ₀(θ_v)/ρ_v)₊, N∞ = R_max/(V̄·dt), V̄ = 23.01 (등록),
  ρ₀(θ) = secθ + tanθ, ρ*(θ) = ρ₀(θ) / (1 − 4·dt·V̄/R_max).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fs1_e7_probe import ATTACKERS, EPS, VARIANTS  # noqa: E402

V_BAR = 23.01


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default="artifacts/fs1/e7a3")
    ap.add_argument("--eps", type=int, default=EPS)
    a = ap.parse_args()
    d = pathlib.Path(a.dir)
    z = np.load(d / "rows.npz")
    pj = json.loads((d / "probe.json").read_text(encoding="utf-8"))
    k = pj["consts"]
    n_inf = k["range_max"] / (V_BAR * k["dt"])
    out = {"schema": "fs1-rho2-overlay-v1", "V_bar": V_BAR, "N_inf": round(n_inf, 4), "variants": {}}
    for vn, ts, hs, aim in VARIANTS:
        tv, thv = k["tau0"] * ts, k["theta0"] * hs
        r = 0.5 * k["a_att"] * tv * tv
        dmin, dmax = r / np.sin(thv), k["range_max"] - r
        rho = pj["rho"][vn]
        rho0 = 1 / np.cos(thv) + np.tan(thv)
        rho_star = rho0 / (1 - 4 * k["dt"] * V_BAR / k["range_max"])
        n_pred = max(0.0, n_inf * (1 - rho0 / rho))
        counts, passed_all = [], 0
        for s in ATTACKERS:
            ep = z[f"{s}.ep"]
            rb = z[f"{s}.{vn}.rb"].astype(bool)
            c = z[f"{s}.pa"] + z[f"{s}.va"] * tv
            D = np.linalg.norm(c - z[f"{s}.pf"], axis=1)
            in_shell = (D >= dmin) & (D <= dmax)
            for i in range(a.eps):
                m = ep == i
                if m.any() and in_shell[m].any():
                    counts.append(int(rb[m].sum()))
                    passed_all += 1
        med = float(np.median(counts)) if counts else None
        out["variants"][vn] = {"rho": rho, "rho0": round(float(rho0), 4), "rho_star": round(float(rho_star), 4),
                               "D_min": round(float(dmin), 3), "D_max": round(float(dmax), 3),
                               "shell_pass_eps": passed_all, "cond_window_med": med,
                               "N_pred": round(n_pred, 3),
                               "pred_open": bool(rho >= rho_star),
                               "obs_open": (None if med is None else bool(med >= 4))}
    V = out["variants"]
    agree = [v["pred_open"] == v["obs_open"] for v in V.values() if v["obs_open"] is not None]
    obs = [v["cond_window_med"] for v in V.values() if v["cond_window_med"] is not None]
    pred = [v["N_pred"] for v in V.values() if v["cond_window_med"] is not None]

    def rank(x):
        x = np.asarray(x, float); o = np.argsort(x, kind="mergesort"); r = np.empty(len(x)); i = 0
        while i < len(x):
            j = i
            while j + 1 < len(x) and x[o[j + 1]] == x[o[i]]:
                j += 1
            r[o[i:j + 1]] = 0.5 * (i + j); i = j + 1
        return r
    sp = float(np.corrcoef(rank(pred), rank(obs))[0, 1]) if len(obs) > 2 and np.std(obs) > 0 else None
    out["summary"] = {"classification_agree": f"{sum(agree)}/{len(agree)}",
                      "spearman_pred_vs_obs": sp,
                      "note": "report-only overlay — registered values (rho* 2.813) immutable"}
    (d / "overlay.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out["summary"], indent=2))
    for vn, v in V.items():
        print(f"{vn:14s} rho {v['rho']:6.2f} rho* {v['rho_star']:5.2f} shell_eps {v['shell_pass_eps']:3d} "
              f"med {v['cond_window_med']} pred {v['N_pred']:5.2f} pred_open {v['pred_open']} obs_open {v['obs_open']}")


if __name__ == "__main__":
    main()
