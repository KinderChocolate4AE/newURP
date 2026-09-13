"""R2b state steering probe 판독 — docs/96 §6 figure 3 장 + §7 3-분기 기계 적용.

    python -m shepherd.scripts.r2b_steer_readout

입력 = `artifacts/r2b/steer_probe/shard{00..07}.json` (140 판 × 20 branch, 서버 산출).
판정 규칙은 **실행 전 봉인**됐다 (docs/96). 이 스크립트는 적용기다:

- primary stratum = **multi-dependent 46** (dep-probe 라벨 조인) · solo-sufficient 94 = 대조군
- 보고 단위 = **prefix-sufficiency pattern** — $(W_0, W_{.25}, W_{.5}, W_{.75})$ **4-vector**.
  **$\\rho^\\ast$ 단일 threshold 를 쓰지 않는다** (반응형 적대자 → 단조성 보장 없음, §5).
- reference clock = **$t_F^C$ 고정**. branch 자신의 FIRE 로 시계를 갈아타지 않는다.
- outcome 4 범주 (§5): **S** 포획 유지 · **L** $t_F^C$ 까지 살았으나 capture 상실 ·
  **P** 조기 침투 · **T** 조기 종료. **P·T 는 결측이 아니라 개입의 결과다.**
- 어휘: $W_\\rho$ 는 zero-acceleration **command withdrawal** 이고 $\\rho>0$ 에서는
  limiter 가 **coast** 한다 — "세웠다 / 제거했다" 금지. **$W_0$ 만이 legacy hold**.
  necessity 아님 (재최적화 없음).

descriptive causal-suffix analysis — CI·가설검정 없음 (§9). torch-free.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
PROBE = ROOT / "artifacts/r2b/steer_probe"
FIGS = ROOT / "figures"
B0V3_HASH = "5e7b5b486b9d8a4a"
B0_HASH = "cba024d7ee3d9f61"
RHOS = (0.0, 0.25, 0.5, 0.75)
TESTS = (0.25, 0.5, 0.75)          # rho = 0 은 hold 앵커이지 개입 시험이 아니다
CATS = ("S", "L", "P", "T")


def load():
    recs = []
    for f in sorted(PROBE.glob("shard*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        assert d["b0_hash"] == B0_HASH and d["b0_v3_hash"] == B0V3_HASH
        recs += d["records"]
    assert len({r["s"] for r in recs}) == len(recs) == 140, f"표본 {len(recs)}"
    excluded = [(r["s"], "ref_parity_ok=False") for r in recs if not r["ref_parity_ok"]]
    keep = [r for r in recs if r["ref_parity_ok"]]
    bad = [(r["s"], b["rho"]) for r in keep for b in r["branches"]
           if not b["prefix_parity_ok"]]
    assert not bad, f"prefix parity 붕괴 — 데이터가 아니라 코드 문제다: {bad[:5]}"
    return keep, excluded


def full(r, rho):
    """해당 rho 의 **full withdrawal** branch (limiter=None)."""
    return next(b for b in r["branches"]
                if abs(b["rho"] - rho) < 1e-9 and b["limiter"] is None)


def loo(r, rho, j):
    return next(b for b in r["branches"]
                if abs(b["rho"] - rho) < 1e-9 and b["limiter"] == j)


def destroyed(b) -> bool:
    """capture 파괴 = S 가 아닌 모든 것 (L/P/T). docs/96 §5 범주 그대로."""
    return b["category"] != "S"


def pattern_stats(recs):
    """prefix-sufficiency pattern — 4-vector 분포 + 비단조 집계."""
    pats = {}
    nonmono = 0
    for r in recs:
        p = tuple(full(r, x)["category"] for x in RHOS)
        pats[p] = pats.get(p, 0) + 1
        d = [destroyed(full(r, x)) for x in TESTS]
        # 비단조 = 파괴가 rho 에 대해 한 번 꺼졌다가 다시 켜짐 (정상, 기록 대상)
        if any(not d[i] and d[i + 1] for i in range(len(d) - 1)):
            nonmono += 1
    return {"patterns": {"".join(k): v for k, v in
                         sorted(pats.items(), key=lambda x: -x[1])},
            "n_nonmonotone": nonmono, "n_records": len(recs)}


def per_rho(recs):
    out = {}
    for x in RHOS:
        bs = [full(r, x) for r in recs]
        cat = {c: sum(b["category"] == c for b in bs) for c in CATS}
        reach = [b for b in bs if b["reached_ref_fire"]]
        dp = [b["delta_at_ref_fire"]["dp_norm"] for b in reach]
        dh = [b["delta_at_ref_fire"]["dheading_rad"] for b in reach]
        dvw = [b["delta_at_ref_fire"]["d_v_worst"] for b in reach]
        dbx = [b["delta_at_ref_fire"]["d_boxed"] for b in reach]
        coast = [float(np.max(b["coast_disp"])) for b in bs]
        out[x] = {
            "n": len(bs), "categories": cat,
            "destroyed": sum(destroyed(b) for b in bs),
            "destroyed_frac": sum(destroyed(b) for b in bs) / len(bs),
            "n_reached_ref_fire": len(reach),
            "dp_norm": _q(dp), "dheading_rad": _q(dh),
            "d_v_worst": _q(dvw),
            "n_dp_exactly_zero": int(sum(v == 0.0 for v in dp)),
            "n_lost_authoritative": int(sum(v < 0 for v in dvw)),
            "n_boxed_changed": int(sum(v != 0 for v in dbx)),
            "coast_disp_max_per_record": _q(coast),
            "t_withdraw": _q([b["t_withdraw"] for b in bs]),
        }
    return out


def _q(v):
    if not v:
        return None
    a = np.asarray(v, float)
    return {"median": float(np.median(a)), "min": float(a.min()),
            "max": float(a.max()), "mean": float(a.mean())}


def loo_map(recs):
    """limiter × rho 파괴율. 어휘 lock: '필수' 금지 — 재최적화가 없다."""
    return {str(x): [sum(destroyed(loo(r, x, j)) for r in recs) / len(recs)
                     for j in range(4)] for x in RHOS}


def verdict(multi, pr):
    """docs/96 §7 3-분기. 발명한 cutoff 없음 — '대부분' 은 과반으로만 읽고,
    분기 1 vs 3 은 **임계치가 아니라 순서 비교** (늦은 rho 에서 파괴가 줄어드는가)."""
    d = {x: pr[x]["destroyed_frac"] for x in TESTS}
    small = d[0.25]
    declines = d[0.75] < d[0.25]
    # 상태가 실제로 달라졌는가 = 정확한 0 대 비영 (임계치 아님)
    moved = pr[0.25]["n_reached_ref_fire"] - pr[0.25]["n_dp_exactly_zero"]

    if all(v <= 0.5 for v in d.values()):
        return "BRANCH_2", (
            "Under the sealed A2-reactive world, withdrawing limiter acceleration "
            "commands did not generally change the outcome at any tested rho "
            f"(destroyed {d[0.25]:.0%} / {d[0.5]:.0%} / {d[0.75]:.0%} at rho "
            "0.25 / 0.5 / 0.75). The sealed plan's TIME-SUFFIX control is therefore "
            "not what the multi-agent dependence rests on; the next intervention "
            "should target placement / initial conditions rather than command "
            "withdrawal.")
    if small > 0.5 and declines:
        return "BRANCH_1", (
            "Under the sealed A2-reactive world and its fixed interaction semantics, "
            "withdrawing limiter acceleration commands from t_rho onward changed the "
            "reactive target's state at the original firing time t_F^C and removed "
            "the capture-ready condition that the original plan had reached there "
            f"(destroyed {d[0.25]:.0%} at rho=0.25, falling to {d[0.75]:.0%} at "
            f"rho=0.75; {moved}/{pr[0.25]['n_reached_ref_fire']} survivors show a "
            "non-zero attacker-state displacement at t_F^C).")
    if small > 0.5 and not declines:
        return "BRANCH_3", (
            f"Destruction is essentially uniform in rho ({d[0.25]:.0%} / {d[0.5]:.0%} "
            f"/ {d[0.75]:.0%}) rather than concentrated in early withdrawal, while "
            "docs/95 found the instantaneous geometry null. Neither instantaneous "
            "blocking nor prefix steering accounts for it — look at FIRE timing, "
            "hard-kill commits, capturer alignment, longitudinal state.")
    return "AMBIGUOUS_SEE_NUMBERS", (
        f"destroyed {d[0.25]:.0%} / {d[0.5]:.0%} / {d[0.75]:.0%} — docs/96 §7 의 세 "
        "분기 중 어느 것도 조항대로 성립하지 않는다. 임계치를 발명하지 않는다.")


def figures(multi, solo, pr_m, pr_s, lm):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIGS.mkdir(exist_ok=True)
    x = np.arange(len(RHOS))
    col = {"S": "#4C9F70", "L": "#E4B363", "P": "#C1444F", "T": "#7A6C9B"}

    # Fig 1 — outcome ladder (rho x 범주), primary / control 분리
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, pr, nm, n in ((axes[0], pr_m, "multi-dependent", len(multi)),
                          (axes[1], pr_s, "solo-sufficient (control)", len(solo))):
        bot = np.zeros(len(RHOS))
        for c in CATS:
            v = np.array([pr[r]["categories"][c] for r in RHOS], float)
            ax.bar(x, v, 0.6, bottom=bot, label=c, color=col[c])
            bot += v
        ax.set_xticks(x)
        ax.set_xticklabels([f"$W_{{{r:g}}}$" for r in RHOS])
        ax.set_title(f"{nm} (n={n})", fontsize=9)
        ax.set_xlabel(r"withdrawal point $\rho$")
    axes[0].set_ylabel("records")
    axes[0].legend(fontsize=8, title="S survived / L lost / P penetrated / T terminated",
                   title_fontsize=7)
    fig.suptitle("Fig 1 - outcome ladder. $W_0$ = legacy hold anchor; "
                 r"$\rho>0$ = command withdrawal (limiters coast)", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGS / "r2b_steer_f1_outcome_ladder.png", dpi=160)
    plt.close(fig)

    # Fig 2 — state divergence at t_F^C (추세선 금지: 점만)
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    for ax, key, lbl in ((axes[0], "dp_norm", r"$\|\Delta p_A(t_F^C)\|$ [m]"),
                         (axes[1], "dheading_rad", r"$\Delta \hat v_A(t_F^C)$ [rad]"),
                         (axes[2], "coast_disp_max_per_record",
                          r"max limiter coast after $t_\rho$ [m]")):
        for i, r in enumerate(RHOS):
            q = pr_m[r][key]
            if q is None:
                continue
            ax.plot([i], [q["median"]], "o", color="C0", ms=7)
            ax.vlines(i, q["min"], q["max"], color="C0", alpha=.4, lw=2)
        ax.set_xticks(x)
        ax.set_xticklabels([f"{r:g}" for r in RHOS])
        ax.set_xlabel(r"$\rho$")
        ax.set_ylabel(lbl, fontsize=9)
        ax.grid(alpha=.25)
        ax.set_xlim(-0.5, len(RHOS) - 0.5)
    axes[0].set_title("multi-dependent, records reaching $t_F^C$ only\n"
                      "(P/T counted in Fig 1, not here)", fontsize=8)
    fig.suptitle(r"Fig 2 - state divergence at the reference firing time. "
                 r"No trend line: non-monotonicity in $\rho$ is expected", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGS / "r2b_steer_f2_divergence.png", dpi=160)
    plt.close(fig)

    # Fig 3 — per-limiter x branch-time destruction map
    m = np.array([lm[str(r)] for r in RHOS]).T          # (4 limiter, 4 rho)
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    im = ax.imshow(m, cmap="Reds", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r:g}" for r in RHOS])
    ax.set_yticks(range(4))
    ax.set_yticklabels([f"limiter {j}" for j in range(4)], fontsize=8)
    ax.set_xlabel(r"$\rho$")
    for i in range(4):
        for j in range(len(RHOS)):
            ax.text(j, i, f"{m[i, j]:.2f}", ha="center", va="center", fontsize=7,
                    color="white" if m[i, j] > 0.5 else "black")
    fig.colorbar(im, ax=ax, label="destroyed fraction")
    ax.set_title(r"Fig 3 - leave-one-out $W_\rho^{(j)}$ destruction, multi-dependent"
                 f" (n={len(multi)})\nnot necessity: no reoptimization", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGS / "r2b_steer_f3_loo_map.png", dpi=160)
    plt.close(fig)


def main():
    keep, excluded = load()
    multi = [r for r in keep if r["dep"]["multi_dependent"]]
    solo = [r for r in keep if not r["dep"]["multi_dependent"]]
    pr_m, pr_s = per_rho(multi), per_rho(solo)
    lm = loo_map(multi)
    vkey, sentence = verdict(multi, pr_m)
    figures(multi, solo, pr_m, pr_s, lm)

    out = {"doc": "docs/96 §6·§7 readout", "b0_v3_hash": B0V3_HASH,
           "r2b_b0_hash": B0_HASH,
           "sample": {"kept": len(keep), "excluded": excluded,
                      "multi_dependent": len(multi), "solo_sufficient": len(solo)},
           "primary_multi_dependent": {str(k): v for k, v in pr_m.items()},
           "control_solo_sufficient": {str(k): v for k, v in pr_s.items()},
           "prefix_sufficiency_pattern": pattern_stats(multi),
           "loo_destruction_map": lm,
           "reference_authoritative_at_fire":
               int(sum(r["ref"]["authoritative_at_fire"] for r in multi)),
           "verdict": {"branch": vkey, "sentence": sentence},
           "caveat_asymmetry": (
               "The realized plan is constant acceleration, so v_L(t_rho) ~ a_L*t_rho "
               "is already built up and late withdrawal is an intrinsically weak "
               "intervention (limiters coast). A null at late rho is NOT strong "
               "evidence against steering (docs/96 §2b)."),
           }
    (ROOT / "artifacts/r2b/steer_readout.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"kept {len(keep)}  excluded {len(excluded)}  "
          f"multi {len(multi)}  solo {len(solo)}")
    for nm, pr in (("multi", pr_m), ("solo ", pr_s)):
        print(f"  -- {nm} --")
        for r in RHOS:
            p = pr[r]
            dp = p["dp_norm"]
            print(f"   W_{r:<5g} t_w med {p['t_withdraw']['median']:>4.0f} | "
                  f"{ {c: p['categories'][c] for c in CATS} } "
                  f"destroyed {p['destroyed_frac']:>5.1%} | "
                  f"reached {p['n_reached_ref_fire']:>3} "
                  f"dp med {dp['median']:>7.3f} max {dp['max']:>8.3f} "
                  f"(exact 0: {p['n_dp_exactly_zero']}) | "
                  f"lost-auth {p['n_lost_authoritative']:>3} | "
                  f"coast med {p['coast_disp_max_per_record']['median']:>6.2f} m")
    ps = out["prefix_sufficiency_pattern"]
    print(f"  patterns (W0,W.25,W.5,W.75): {list(ps['patterns'].items())[:6]}")
    print(f"  non-monotone records: {ps['n_nonmonotone']}/{ps['n_records']}")
    print(f"  LOO destruction by rho: { {k: [round(x,2) for x in v] for k, v in lm.items()} }")
    print(f"\n[{vkey}] {sentence}")


if __name__ == "__main__":
    main()
