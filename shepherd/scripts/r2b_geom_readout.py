"""R2b geometry probe 판독 — docs/95 §5 figure 4장 + §7.5 3-분기 기계 적용.

    python -m shepherd.scripts.r2b_geom_readout

입력 = `artifacts/r2b/geom_probe/shard{00..07}.json` (140건, 서버 산출·커밋).
판독 규칙은 **실행 전 봉인** 됐다 (docs/95). 이 스크립트는 고를 것이 없는 적용기다:

- primary stratum = **multi-dependent** (dep-probe 조인 라벨) · solo-sufficient 는 대조군
- 시간축 = **ξ = (t − t_FIRE)/τ₀ ∈ [−2, 0]** (q_dec = 1/6 → FIRE 직전 12 틱).
  FIRE 이후는 capture-set shaping 이 아니므로 primary 에서 제외 (§3).
- H1 canonical inactivity = **`n_block_full == 0 ∧ n_block_hold == 0`** (r1.2 정정).
  `min_dist > kill_radius + χρ` 는 **보조** 기하형 (§6.5 문장 형식용, ρ = 1.77).
- §7.5 3-분기는 **조항 자체의 연접**으로 판정한다 (`verdict()` 참조). branch 1 은
  "closure 반복 ∧ authoritative 진입과 맞물림" 이므로 closure 가 capturability 를 **양으로**
  움직인 판이 정확히 0 이면 임계치 없이 탈락한다. branch 2 의 "대부분 inactive" 는
  **과반**으로만 읽는다. 둘 다 아니면 `AMBIGUOUS_SEE_NUMBERS` — 수치를 발명하지 않는다.
- descriptive mechanism analysis — CI·가설검정 없음 (§7). necessity 아님.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
PROBE = ROOT / "artifacts/r2b/geom_probe"
FIGS = ROOT / "figures"
B0V3_HASH = "5e7b5b486b9d8a4a"
B0_HASH = "cba024d7ee3d9f61"
RHO = 1.77                      # physics.net_radius (m4_config) — χρ 의 ρ
Q_DEC = 6                       # 1 tick = ξ 1/6
KS = np.arange(-12, 1)          # ξ ∈ [−2, 0] 의 정수 tick offset
ETAS = (2.1, 2.4, 2.7, 3.0, 3.3, 3.6, 3.9)


def load():
    """shards → (kept records, excluded (s, reason))."""
    recs = []
    for f in sorted(PROBE.glob("shard*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        assert d["b0_hash"] == B0_HASH, f"{f.name}: r2b b0 hash 불일치"
        recs += d["records"]
    for r in recs:
        assert r["b0_v3_hash"] == B0V3_HASH and r["r2b_b0_hash"] == B0_HASH, \
            f"s={r['s']}: world hash 불일치 — pooling 금지"
    assert len({r["s"] for r in recs}) == len(recs), "중복 s"
    # 판독 전 확인 (§6.8): parity 실패 판 제외 + 사유·건수 명시
    bad = [(r["s"], f"cf_parity_ok=False ticks={r['cf_parity_bad_ticks']}")
           for r in recs if not r["cf_parity_ok"]]
    bad += [(r["s"], "dep 라벨 결측") for r in recs if r["dep"] is None]
    bad += [(r["s"], "fire_step 없음") for r in recs if r["fire_step"] is None]
    drop = {s for s, _ in bad}
    return [r for r in recs if r["s"] not in drop], bad


def prefire(r):
    """ξ ∈ [−2, 0] 틱 (FIRE 포함, 이후 제외)."""
    want = {r["fire_step"] + int(k) for k in KS}
    return [t for t in r["ticks"] if t["t"] in want]


def series(recs, key):
    """(n_rec × len(KS)) — 결측 tick 은 NaN (FIRE 전 12틱보다 짧은 에피소드)."""
    out = np.full((len(recs), len(KS)), np.nan)
    for i, r in enumerate(recs):
        by_t = {t["t"]: t for t in r["ticks"]}
        for j, k in enumerate(KS):
            t = by_t.get(r["fire_step"] + int(k))
            if t is not None:
                out[i, j] = key(t)
    return out


def quant(a):
    with np.errstate(all="ignore"):
        q = np.nanpercentile(a, [25, 50, 75], axis=0)
    return {"q25": q[0].tolist(), "median": q[1].tolist(), "q75": q[2].tolist(),
            "n_per_k": np.sum(~np.isnan(a), axis=0).tolist()}


def h1_stats(recs):
    """H1 채널 활성도 + pre-fire closure 실측 (§6.5 [r1.1] 문장 형식 입력)."""
    n_tick = n_inact = n_geom_inact = 0
    rec_any_close = rec_any_open = 0
    peak_dG, peak_dV = [], []
    for r in recs:
        pre = prefire(r)
        n_tick += len(pre)
        n_inact += sum(t["channel_inactive"] for t in pre)
        n_geom_inact += sum(
            t["min_dist_att_lim"] > t["kill_radius"] + r["chi"] * RHO for t in pre)
        rec_any_close += any(t["n_close"] > 0 for t in pre)
        rec_any_open += any(t["n_open"] > 0 for t in pre)
        peak_dG.append(max((t["dG_close"] for t in pre), default=np.nan))
        peak_dV.append(max((t["dV"] for t in pre), default=np.nan))
    return {
        "n_records": len(recs), "n_prefire_ticks": n_tick,
        "channel_inactive_frac": n_inact / n_tick if n_tick else None,
        "geom_inactive_frac": n_geom_inact / n_tick if n_tick else None,
        "records_with_prefire_n_close": rec_any_close,
        "records_with_prefire_n_open": rec_any_open,
        "prefire_peak_dG_close": {"median": float(np.nanmedian(peak_dG)),
                                  "max": float(np.nanmax(peak_dG))},
        "prefire_peak_dV": {"median": float(np.nanmedian(peak_dV)),
                            "max": float(np.nanmax(peak_dV))},
    }


def authoritative(recs):
    """H2 의 authoritative predicate — FIRE 시점 ¬boxed_in ∧ v_shot_worst ≥ 1."""
    ok = nb = 0
    for r in recs:
        t = next((x for x in r["ticks"] if x["t"] == r["fire_step"]), None)
        if t is None:
            continue
        nb += not t["boxed_full"]
        ok += (not t["boxed_full"]) and t["v_worst_full"] >= 1
    return {"n": len(recs), "not_boxed_at_fire": nb, "capture_predicate_at_fire": ok}


def h3_stats(recs):
    npl = series(recs, lambda t: t["n_plus"])
    dsum = series(recs, lambda t: float(np.sum(t["coma_D"])))
    return {"n_plus_prefire_max_hist": np.bincount(
                np.nan_to_num(np.nanmax(npl, axis=1)).astype(int), minlength=5).tolist(),
            "n_plus_at_fire_hist": np.bincount(
                np.nan_to_num(npl[:, -1]).astype(int), minlength=5).tolist(),
            "sum_D_prefire_max": float(np.nanmax(dsum))}


def residual_closure(recs):
    """pre-fire closure 가 **있는** 판의 해부 — branch 1 의 '맞물림' 조항 검사용.

    branch 1 은 "ΔG_close > 0 이 **반복**되고 **authoritative 진입과 맞물림**" 을
    요구한다 (§7.5). 따라서 closure 의 존재만으로는 branch 1 이 아니고, 같은 판에서
    capturability 가 **양으로** 움직였는지를 같이 봐야 한다. `coupled` 가 **정확히 0**
    이면 임계치 없이 branch 1 이 탈락한다 (발명한 cutoff 아님).
    """
    rows, coupled = [], 0
    for r in recs:
        by_t = {t["t"]: t for t in r["ticks"]}
        pre = [(int(k), by_t[r["fire_step"] + int(k)]) for k in KS
               if r["fire_step"] + int(k) in by_t]
        hits = [(k, t) for k, t in pre if t["n_close"] > 0]
        if not hits:
            continue
        dv_at_hits = [t["dV"] for _, t in hits]
        pos = max(dv_at_hits) > 0
        coupled += pos
        rows.append({"s": r["s"], "eta": r["eta"], "chi": r["chi"],
                     "n_hit_ticks": len(hits), "n_prefire_ticks": len(pre),
                     "k_range": [hits[0][0], hits[-1][0]],
                     "max_dG_close": max(t["dG_close"] for _, t in hits),
                     "dV_at_closure_ticks": dv_at_hits,
                     "dV_positive_anywhere": bool(pos)})
    return {"records": rows, "n_with_closure": len(rows),
            "n_closure_coupled_to_positive_dV": coupled}


def verdict(multi, resid):
    """§7.5 3-분기 기계 적용.

    발명한 수치 cutoff 는 없다. branch 1 은 **자기 조항의 연접**으로 탈락/성립하고
    (`coupled` 의 정확한 0), branch 2 의 "대부분 inactive" 는 **과반** 으로만 읽는다
    (관측값이 98% 수준이면 이 독해는 cutoff-insensitive 하다).
    """
    inact = multi["channel_inactive_frac"]
    coupled = resid["n_closure_coupled_to_positive_dV"]
    if coupled > 0 and resid["n_with_closure"] > multi["n_records"] / 2:
        return "BRANCH_1", ("direct cooperative closure geometry is the mechanism — "
                            "formalize that geometry")
    if inact is not None and inact > 0.5:
        return "BRANCH_2", (
            "Under the sealed A2-reactive world and its fixed interaction semantics, "
            "multi-agent-dependent successful plans were not generally explained by "
            "instantaneous limiter-induced escape-channel closure near FIRE. "
            f"H1 was structurally inactive in {inact:.1%} of pre-fire ticks "
            "(n_block_full == 0 and n_block_hold == 0). Newly blocked escape "
            f"directions appeared before FIRE in only "
            f"{resid['n_with_closure']}/{multi['n_records']} records of the "
            "multi-dependent stratum, confined to the final ticks, and in none of "
            "them did that closure coincide with a positive move of the "
            "capturability proxy. Next card: trajectory-level state steering probe "
            "(separate pre-registration).")
    return "AMBIGUOUS_SEE_NUMBERS", (
        f"closure in {resid['n_with_closure']}/{multi['n_records']} records "
        f"(coupled to positive dV: {coupled}), channel_inactive {inact:.1%} — "
        "docs/95 §7.5 의 두 분기 모두 성립하지 않는다. 임계치를 발명하지 않고 "
        "수치만 보고한다.")


def figures(multi, solo, keep):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIGS.mkdir(exist_ok=True)
    xi = KS / Q_DEC

    # Fig 1 — FIRE-aligned time series (primary stratum vs control)
    fig, axes = plt.subplots(3, 1, figsize=(7, 8), sharex=True)
    panels = [(r"$\Delta G_{close}$ (H1)", lambda t: t["dG_close"]),
              (r"$\Delta V$ (H2 proxy)", lambda t: t["dV"]),
              (r"$v_{shot}^{worst}-1$ (authoritative)",
               lambda t: t["v_worst_full"] - 1.0)]
    for ax, (lbl, key) in zip(axes, panels):
        for recs, c, nm in ((multi, "C0", "multi-dependent"),
                            (solo, "C1", "solo-sufficient")):
            if not recs:
                continue
            q = np.nanpercentile(series(recs, key), [25, 50, 75], axis=0)
            ax.plot(xi, q[1], color=c, lw=2, label=f"{nm} (n={len(recs)})")
            ax.fill_between(xi, q[0], q[2], color=c, alpha=.18, lw=0)
        ax.axhline(0, color="k", lw=.6, ls=":")
        ax.axvline(0, color="r", lw=.8, ls="--")
        ax.set_ylabel(lbl, fontsize=9)
        ax.grid(alpha=.25)
    axes[0].legend(fontsize=8)
    axes[0].set_title("Fig 1 - FIRE-aligned, geometry-probe analysis sample\n"
                      "(deterministic selected set, K=5 per cell; not 'all C successes')",
                      fontsize=9)
    axes[-1].set_xlabel(r"$\xi=(t-t_{FIRE})/\tau_0$")
    fig.tight_layout()
    fig.savefig(FIGS / "r2b_geom_f1_fire_aligned.png", dpi=160)
    plt.close(fig)

    # Fig 2 — target-centered angular geometry, stratum-summed
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    for ax, xs in zip(axes, (-1.0, -0.5, 0.0)):
        den = np.zeros(72)
        clo = np.zeros(72)
        opn = np.zeros(72)
        n = 0
        for r in multi:
            for a in r["angular"]:
                if abs(a["xi"] - xs) < 1e-9:
                    den += a["h_denom"]
                    clo += a["h_close"]
                    opn += a["h_open"]
                    n += 1
        im = ax.imshow(den.reshape(6, 12), origin="lower", aspect="auto",
                       cmap="Blues", extent=[-180, 180, 0, 180])
        ax.set_title(f"xi={xs:+.1f}  n={n}\ndenom={den.sum():.0f}  "
                     f"close={clo.sum():.0f}  open={opn.sum():.0f}", fontsize=8)
        ax.set_xlabel(r"$\varphi$ [deg]", fontsize=8)
        ax.set_ylabel(r"$\theta$ from net axis [deg]", fontsize=8)
        fig.colorbar(im, ax=ax, label="turn-feasible witnesses")
    fig.suptitle("Fig 2 - target-centered surviving escape directions, "
                 "multi-dependent stratum (sum over records)", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGS / "r2b_geom_f2_angular.png", dpi=160)
    plt.close(fig)

    # Fig 3 — per-limiter contribution heatmap
    m = np.stack([np.nanmean(series(multi, lambda t, i=i: t["coma_D"][i]), axis=0)
                  for i in range(4)])
    v = max(float(np.nanmax(np.abs(m))), 1e-12)
    fig, ax = plt.subplots(figsize=(7, 2.9))
    im = ax.imshow(m, aspect="auto", cmap="RdBu_r", vmin=-v, vmax=v,
                   extent=[xi[0], xi[-1], 3.5, -0.5])
    ax.set_yticks(range(4))
    ax.set_yticklabels([f"limiter {i}" for i in range(4)], fontsize=8)
    ax.set_xlabel(r"$\xi$")
    fig.colorbar(im, ax=ax, label=r"$D_i$ (coma_D)")
    ax.set_title(f"Fig 3 - per-limiter marginal, mean over multi-dependent "
                 f"(n={len(multi)}); max|D_i| = {v:.2e}\n"
                 "non-additivity diagnostic only - not a Shapley decomposition",
                 fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGS / "r2b_geom_f3_limiter_heatmap.png", dpi=160)
    plt.close(fig)

    # Fig 4 — mechanism vs difficulty
    es, md, dg, dv = [], [], [], []
    for e in ETAS:
        g = [r for r in keep if abs(r["eta"] - e) < 0.15]
        if not g:
            continue
        sub = [r for r in g if r["dep"]["multi_dependent"]] or g
        st = h1_stats(sub)
        es.append(e)
        md.append(float(np.mean([r["dep"]["multi_dependent"] for r in g])))
        dg.append(st["prefire_peak_dG_close"]["median"])
        dv.append(st["prefire_peak_dV"]["median"])
    fig, ax = plt.subplots(figsize=(7, 4))
    ax2 = ax.twinx()
    ax.plot(es, md, "o-", color="C2", label="multi-dependent fraction")
    ax2.plot(es, dg, "s--", color="C0", label=r"median pre-fire peak $\Delta G_{close}$")
    ax2.plot(es, dv, "^--", color="C3", label=r"median pre-fire peak $\Delta V$")
    ax.set_xlabel(r"$\eta$ (difficulty)")
    ax.set_ylabel("fraction", color="C2")
    ax2.set_ylabel("mechanism magnitude")
    ax.set_title("Fig 4 - mechanism vs difficulty, geometry-probe analysis sample\n"
                 "(fractions are 'of the analysis sample', not of all C successes)",
                 fontsize=9)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper left")
    ax.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(FIGS / "r2b_geom_f4_mechanism_vs_difficulty.png", dpi=160)
    plt.close(fig)
    return {"eta": es, "multi_dependent_frac": md, "peak_dG_median": dg,
            "peak_dV_median": dv}


def main():
    keep, excluded = load()
    multi = [r for r in keep if r["dep"]["multi_dependent"]]
    solo = [r for r in keep if not r["dep"]["multi_dependent"]]
    mstat, sstat = h1_stats(multi), h1_stats(solo)
    resid = residual_closure(multi)
    vkey, sentence = verdict(mstat, resid)
    by_eta = figures(multi, solo, keep)
    out = {
        "doc": "docs/95 §5 readout", "b0_v3_hash": B0V3_HASH, "r2b_b0_hash": B0_HASH,
        "sample": {"kept": len(keep), "excluded": excluded,
                   "multi_dependent": len(multi), "solo_sufficient": len(solo),
                   "note": "deterministic selected analysis set (K=5 per cell); "
                           "fractions are 'of the analysis sample'"},
        "primary_multi_dependent": mstat, "control_solo_sufficient": sstat,
        "H1_series": {"xi": (KS / Q_DEC).tolist(),
                      "dG_close": quant(series(multi, lambda t: t["dG_close"]))},
        "H2": {"dV": quant(series(multi, lambda t: t["dV"])),
               "authoritative_at_fire": authoritative(multi)},
        "H3": h3_stats(multi),
        "residual_closure_multi": resid,
        "residual_closure_solo": residual_closure(solo),
        "by_eta": by_eta,
        "verdict": {"branch": vkey, "sentence": sentence},
        # docs/95 §4 는 L2 를 secondary 로 두되 생략 조항을 두지 않았다 -> 조용한 skip 금지.
        "deviations": [
            "preregistered secondary (L2 paired trajectory) not executed; superseded "
            "by a separately preregistered trajectory-level steering analysis"],
    }
    (ROOT / "artifacts/r2b/geom_readout.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"kept {len(keep)}  excluded {len(excluded)}  "
          f"multi-dependent {len(multi)}  solo-sufficient {len(solo)}")
    for nm, st in (("multi", mstat), ("solo ", sstat)):
        print(f"  {nm}: channel_inactive {st['channel_inactive_frac']:.1%} "
              f"(geom form {st['geom_inactive_frac']:.1%}) of "
              f"{st['n_prefire_ticks']} pre-fire ticks | "
              f"records w/ pre-fire n_close>0: "
              f"{st['records_with_prefire_n_close']}/{st['n_records']} | "
              f"peak dG med {st['prefire_peak_dG_close']['median']:.4f} "
              f"max {st['prefire_peak_dG_close']['max']:.4f} | "
              f"peak dV med {st['prefire_peak_dV']['median']:.4f} "
              f"max {st['prefire_peak_dV']['max']:.4f}")
    print(f"  residual closure (multi): {resid['n_with_closure']} records, "
          f"coupled to positive dV: {resid['n_closure_coupled_to_positive_dV']}")
    for w in resid["records"]:
        print(f"    s={w['s']:5d} eta={w['eta']:.2f} k{w['k_range']} "
              f"{w['n_hit_ticks']}/{w['n_prefire_ticks']} ticks  "
              f"max dG {w['max_dG_close']:+.4f}  dV@closure "
              f"{[round(x, 6) for x in w['dV_at_closure_ticks']]}")
    print(f"  authoritative at FIRE (multi): {out['H2']['authoritative_at_fire']}")
    print(f"  H3 n_plus at FIRE hist: {out['H3']['n_plus_at_fire_hist']}  "
          f"pre-fire max hist: {out['H3']['n_plus_prefire_max_hist']}  "
          f"max sum D pre-fire: {out['H3']['sum_D_prefire_max']:.2e}")
    print(f"\n[{vkey}] {sentence}")


if __name__ == "__main__":
    main()
