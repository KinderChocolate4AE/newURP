"""D1 실행 — finite toy 의 exact solve 그림·결과 저장 (docs/105 §4.2-4/5).

    PYTHONIOENCODING=utf-8 python -m shepherd.scripts.mode_switch_toy_dp

산출물 (artifacts/mode_switch/toy_dp/):
  results.json           params snapshot + grid + rank table + null cases + 검산
  figA_strict_grid.png   (prior, rho) 격자의 class winning set 과 strict region
  figB_rank_reversal.png post-cue 정보상태별 선호 mode (reversal 시각화)

해석 한계: 전부 SYNTHETIC_EXPLORATORY toy — 104 부록 B 의 F1-E 행보다도 좁은
"정책군·정보구조 검산" 층이다. 양성 reversal/strict cell 은 계수로 만들어낸
것이며 (docs/106 §3) G2 존재성 증거가 아니다.
"""
from __future__ import annotations

import json
import pathlib
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from shepherd.params import PARAMS
from shepherd.mode_switch.toy_dp import (
    NET, achievable_brute, achievable_dp, default_params, rank_table, strict_grid,
)

OUT = pathlib.Path(__file__).resolve().parents[2] / "artifacts" / "mode_switch" / "toy_dp"

CAT_LABELS = ["neither", "both feasible", "rec only (strict)", "fixed only (BUG)"]
CAT_COLORS = ["#d9d9d9", "#7fb3d5", "#c0392b", "#f39c12"]


def _git_rev() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p = default_params()
    p0s = tuple(PARAMS["mode_switch.toy.grid_p0"].value)
    rhos = tuple(PARAMS["mode_switch.toy.grid_rho"].value)

    # 검산 (105 §4.2-1): tiny + default 에서 DP == brute
    tiny = default_params(T=3, t_cue=1, t_roe=1, tau_net=1)
    checks = {
        "dp_eq_brute_tiny": achievable_dp(tiny) == achievable_brute(tiny),
        "dp_eq_brute_default": achievable_dp(p) == achievable_brute(p),
    }
    assert all(checks.values()), checks

    # null cases (105 §4.2-2/3)
    masked = strict_grid(default_params(t_cue=None), p0s, rhos)
    _, n_rev_dom = rank_table(default_params(p_net=(0.9, 0.9), p_kin=(0.3, 0.3)))
    nulls = {"masked_cue_n_strict": masked["n_strict"],
             "dominant_mode_n_reversal": n_rev_dom}
    assert masked["n_strict"] == 0 and n_rev_dom == 0, nulls
    # 참고용: q=0.5 (cue 도착하되 무정보) -- 잡음 조건화가 만드는 겉보기 gap 계측.
    # 계약상 정보-null 은 완전 마스킹이다 (105 §4.2-2); 이 값은 confound 크기 기록.
    noise = strict_grid(default_params(q=0.5), p0s, rhos)
    nulls["noise_cue_q05_n_strict"] = noise["n_strict"]

    # 본 결과
    grid = strict_grid(p, p0s, rhos)
    rows, n_rev = rank_table(p)

    results = {
        "doc": "docs/105 §4 D1 · docs/106 §3",
        "git_rev": _git_rev(),
        "params": {k: {"value": v.value, "status": v.status}
                   for k, v in PARAMS.items() if k.startswith("mode_switch.toy.")},
        "dp_vs_brute": {k: bool(v) for k, v in checks.items()},
        "null_cases": nulls,
        "grid": grid,
        "rank_table": rows,
        "n_reversal_t": n_rev,
        "claim_limit": ("SYNTHETIC_EXPLORATORY toy: 정책군·정보구조 검산 전용. "
                        "양성 reversal/strict region 은 계수 설계의 산물 -- G2 증거 아님."),
    }
    (OUT / "results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    # figA: strict region grid
    cat = np.array([[c["cat"] for c in row] for row in grid["cells"]])
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.imshow(cat, cmap=matplotlib.colors.ListedColormap(CAT_COLORS),
              vmin=0, vmax=3, aspect="auto", origin="lower")
    ax.set_xticks(range(len(p0s)), [f"{v:g}" for v in p0s])
    ax.set_yticks(range(len(rhos)), [f"{v:g}" for v in rhos])
    ax.set_xlabel("prior P(branch=evasive)")
    ax.set_ylabel(r"cost ratio $\rho_K$ ($c_N$=1)")
    ax.set_title(f"toy winning sets (alpha={p.alpha}, beta={p.beta}, q={p.q})\n"
                 f"strict cells (rec only) = {grid['n_strict']} — SYNTHETIC toy, not G2 evidence")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in CAT_COLORS[:3]]
    ax.legend(handles, CAT_LABELS[:3], loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "figA_strict_grid.png", dpi=150)
    plt.close(fig)

    # figB: post-cue 선호 mode (rank reversal)
    ts = sorted({r["t"] for r in rows})
    pref = np.full((2, len(ts)), np.nan)
    for r in rows:
        if r["pref"] is not None:
            pref[r["cue"], ts.index(r["t"])] = 0.0 if r["pref"] == NET else 1.0
    fig, ax = plt.subplots(figsize=(7.5, 3))
    cmap = matplotlib.colors.ListedColormap(["#2e86c1", "#c0392b"])
    cmap.set_bad("#d9d9d9")
    ax.imshow(np.ma.masked_invalid(pref), cmap=cmap, vmin=0, vmax=1,
              aspect="auto", origin="lower")
    for r in rows:
        ax.text(ts.index(r["t"]), r["cue"],
                r["pref"] or "infeasible", ha="center", va="center",
                color="white" if r["pref"] else "black", fontsize=10)
    ax.set_xticks(range(len(ts)), [str(t) for t in ts])
    ax.set_yticks([0, 1], ["cue=0 (direct)", "cue=1 (evasive)"])
    ax.set_xlabel("t (post-cue decision epoch)")
    ax.set_title(f"preferred mode by information state — reversal epochs = {n_rev}")
    fig.tight_layout()
    fig.savefig(OUT / "figB_rank_reversal.png", dpi=150)
    plt.close(fig)

    print(f"OK  strict cells={grid['n_strict']}/{cat.size}  reversal epochs={n_rev}  "
          f"nulls={nulls}  -> {OUT}")


if __name__ == "__main__":
    main()
