"""E1b — paired 조준오차 진단 (docs/83 §12 · §12-A 동결 프로토콜 구현).

묻는 것 (§12A.5)
----------------
  Primary   : 동일한 outcome-생성 T1 rollout 안에서, nominal slew cap 을 제거하면
              **pre-commit** 조준 오차가 줄어드는가?
  Secondary : 유일한 rescue 에피소드가 비정상적으로 음(-)인 Delta_psi 와 결부되는가?
              (post-result diagnostic localization -- confirmatory 아님)

핵심 (§12A.1~2)
---------------
psi 는 **E1 결과를 생성한 것과 동일한 ratified rollout 안에서** 잰다.
`slew_audit.aim_geometry` 가 단일 정의원이고 (수식 재정의 금지), 여기서는 그것을
호출만 한다. legacy `slew_audit.audit_episode` 는 발사가 없는 세계라
`PSI_MED_DEG=4.26` 과 절대값을 비교하지 않는다.

판정 순서는 §12.6 그대로 **고정**이다 (뒤집으면 서사에 맞추기 쉬워진다):
  1) I1 integrity  2) eligibility 회계  3) primary Delta_psi  4) 동결 규칙
  5) rescue 위치   6) diagnostic omega=inf crossing

    python -m shepherd.scripts.e1b_aim_diag --n 500 --out results/e1b_aim_diag.json

torch-free.
"""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import List, Optional

import numpy as np

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.agents.mobile_finisher import SLEW_UNLIMITED
from shepherd.env_sys import RewardSpec, ratified_system
from shepherd.m4_config import THREAT_BRACKET, m4_config
from shepherd.m4_env import mission_eval
from shepherd.scripts.curve_sweep import _cross50, band_of, bin_edges
from shepherd.scripts.mobility_factorial import PREREG_COMMIT, SUCCESS
from shepherd.scripts.slew_audit import aim_geometry
from shepherd.spawn_rand import SpawnSpec

__all__ = ["episode_psi", "run_arm", "paired_delta_psi"]

BOOT, BOOT_SEED = 20000, 0          # §12.3: paired_compare 와 동일 기계


def _kw(route_gain: float, sense_range: float) -> dict:
    """E1 (mobility_factorial._kw) 과 **동일한 세계**. 여기서 갈라지면 E1b 무의미."""
    return dict(system=ratified_system(),
                reward=RewardSpec(w_kill=0.5, enabled=True),
                attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0,
                                      route_gain=route_gain, sense_range=sense_range),
                spawn=SpawnSpec())


def episode_psi(ep_tel: dict, *, tau: float, range_max: float) -> dict:
    """한 에피소드의 psi 통계 (§12A.4 창 정의).

    Primary  창: `in_band AND t < t_fire`  (commit 스텝 자체 제외)
    Secondary  : `psi_at_commit` = t == t_fire 스텝의 psi (단일값)

    ★ 발사가 없는 에피소드(`fire_step is None`)는 t_fire 가 없으므로 **모든
      in_band 스텝이 pre-fire** 다 -- "발사 전" 의 유일하게 정합적인 읽기이며
      자유도가 아니다. `psi_at_commit` 은 그 경우 None (§12A.4 별도 집계).
    """
    t_fire = ep_tel["fire_step"]
    pre, at_commit = [], None
    for row in ep_tel["rows"]:
        g = aim_geometry(row["p_att"], row["v_att"], row["p_fin"], row["e_fin"],
                         tau=tau, range_max=range_max)
        if g is None or not g["in_band"]:
            continue
        t = int(row["t"])
        if t_fire is None or t < int(t_fire):
            pre.append(g["psi"])
        elif t == int(t_fire):
            at_commit = g["psi"]
    return {"psi_med": float(np.median(pre)) if pre else None,
            "n_eligible": len(pre),
            "psi_at_commit": at_commit,
            "captured": bool(ep_tel["label"] in SUCCESS),
            "label": ep_tel["label"], "regime": ep_tel["regime"],
            "a_att": float(ep_tel["a_att"]), "att_speed": float(ep_tel["att_speed"]),
            "fire_step": t_fire, "steps": ep_tel["steps"]}


def run_arm(n: int, seed0: int, *, omega_max: Optional[float],
            route_gain: float, sense_range: float,
            tau: float, range_max: float) -> List[dict]:
    tel: List[dict] = []
    mission_eval(seed0, n, limiter_mode="hold", mobility=0.0, omega_max=omega_max,
                 telemetry=tel, **_kw(route_gain, sense_range))
    return [episode_psi(e, tau=tau, range_max=range_max) for e in tel]


def paired_delta_psi(fixed: List[dict], inf: List[dict]) -> dict:
    """§12.3 estimand: Delta_psi_i = psi_i^inf - psi_i^2.0 (양쪽 자격 있는 쌍만).

    판정: **CI95 upper < 0** 일 때만 "psi 감소 established". 그 외 not established.
    """
    both, only_f, only_i, neither = [], 0, 0, 0
    for i, (a, b) in enumerate(zip(fixed, inf)):
        ea, eb = a["n_eligible"] > 0, b["n_eligible"] > 0
        if ea and eb:
            both.append((i, b["psi_med"] - a["psi_med"]))
        elif ea:
            only_f += 1
        elif eb:
            only_i += 1
        else:
            neither += 1
    d = np.array([x for _, x in both], float)
    out = {"n_both": len(both), "n_only_fixed": only_f, "n_only_inf": only_i,
           "n_neither": neither,
           "median_delta_psi_rad": None, "median_delta_psi_deg": None,
           "ci95_rad": None, "decrease_established": False}
    if len(d):
        rng = np.random.default_rng(BOOT_SEED)
        idx = rng.integers(0, len(d), size=(BOOT, len(d)))
        meds = np.median(d[idx], axis=1)
        lo, hi = np.percentile(meds, [2.5, 97.5])
        out.update(median_delta_psi_rad=float(np.median(d)),
                   median_delta_psi_deg=float(np.degrees(np.median(d))),
                   ci95_rad=[float(lo), float(hi)],
                   ci95_deg=[float(np.degrees(lo)), float(np.degrees(hi))],
                   decrease_established=bool(hi < 0.0))
        out["_delta"] = {i: v for i, v in both}
    return out


def _capture_curve(arm: List[dict], edges: List[float]) -> tuple:
    xs, ps, ns = [], [], []
    for i in range(len(edges) - 1):
        lo, hi = edges[i], edges[i + 1]
        sub = [e for e in arm if lo <= e["a_att"] < hi]
        if not sub:
            continue
        xs.append(0.5 * (lo + hi))
        ps.append(sum(1 for e in sub if e["captured"]) / len(sub))
        ns.append(len(sub))
    return xs, ps, ns


def main() -> None:
    ap = argparse.ArgumentParser(description="E1b paired 조준오차 진단 (docs/83 §12)")
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--route-gain", type=float, default=0.5)
    ap.add_argument("--sense-range", type=float, default=30.0)
    ap.add_argument("--out", default="results/e1b_aim_diag.json")
    a = ap.parse_args()

    cfg = m4_config()
    tau = float(cfg["physics"]["tau_deploy"])
    rmax = float(cfg["viability"]["cone"]["range_max"])
    rho = float(cfg["physics"]["net_radius"])
    print(f"[E1b] n={a.n} paired CRN · T1(route {a.route_gain}, sense {a.sense_range}) "
          f"· tau {tau} · range_max {rmax}")

    fixed = run_arm(a.n, a.seed0, omega_max=None, route_gain=a.route_gain,
                    sense_range=a.sense_range, tau=tau, range_max=rmax)
    inf = run_arm(a.n, a.seed0, omega_max=SLEW_UNLIMITED, route_gain=a.route_gain,
                  sense_range=a.sense_range, tau=tau, range_max=rmax)

    # ── 1) I1 integrity (실패 시 psi 해석 금지) ───────────────────────────────
    kf = sum(1 for e in fixed if e["captured"])
    ki = sum(1 for e in inf if e["captured"])
    n01 = [i for i, (x, y) in enumerate(zip(fixed, inf))
           if (not x["captured"]) and y["captured"]]
    n10 = [i for i, (x, y) in enumerate(zip(fixed, inf))
           if x["captured"] and not y["captured"]]
    # I1 은 E1 과 **같은 n·seed0** 일 때만 의미가 있다 (E1: n=500, seed0=0).
    i1_applicable = (a.n == 500 and a.seed0 == 0)
    i1 = (kf == 84 and ki == 85 and len(n01) == 1 and len(n10) == 0)
    verdict = ("PASS" if i1 else "*** FAIL -> 분기 D ***") if i1_applicable \
        else "N/A (n/seed0 != E1 조건 500/0 -- 스모크)"
    print(f"\n1) I1 integrity : {kf} -> {ki}, n01={len(n01)}, n10={len(n10)}  "
          f"[E1 기대 84 -> 85, 1, 0]  => {verdict}")

    # ── 2) eligibility 회계 (telemetry completeness) ─────────────────────────
    pd = paired_delta_psi(fixed, inf)
    print(f"2) eligibility  : both {pd['n_both']} · fixed-only {pd['n_only_fixed']} · "
          f"inf-only {pd['n_only_inf']} · neither {pd['n_neither']}")
    nc_f = sum(1 for e in fixed if e["psi_at_commit"] is not None)
    nc_i = sum(1 for e in inf if e["psi_at_commit"] is not None)
    print(f"                  psi_at_commit 정의됨: fixed {nc_f} / inf {nc_i}")

    # ── 3~4) primary Delta_psi + 동결 규칙 ───────────────────────────────────
    if pd["median_delta_psi_rad"] is not None:
        print(f"3) Delta_psi    : median {pd['median_delta_psi_deg']:+.4f} deg  "
              f"CI95 [{pd['ci95_deg'][0]:+.4f}, {pd['ci95_deg'][1]:+.4f}] deg")
        print(f"4) 동결 규칙     : CI upper < 0 ?  => "
              f"{'감소 ESTABLISHED' if pd['decrease_established'] else 'not established'}")
    else:
        print("3) Delta_psi    : 계산 불가 (자격 쌍 0)")

    # ── 5) rescue 위치 (등록 regime 만; 정확 a_att 는 diagnostic) ─────────────
    resc = []
    for i in n01:
        e = fixed[i]
        d_i = pd.get("_delta", {}).get(i)
        pct = None
        if d_i is not None and pd["median_delta_psi_rad"] is not None:
            arr = np.array(list(pd["_delta"].values()), float)
            pct = float((arr < d_i).mean() * 100.0)
        resc.append({"episode": i, "registered_band": band_of(e["a_att"], cfg),
                     "regime": e["regime"], "a_att_diagnostic": e["a_att"],
                     "delta_psi_rad": d_i,
                     "delta_psi_percentile_diagnostic": pct,
                     "label_fixed": e["label"], "label_inf": inf[i]["label"]})
    print(f"5) rescue 위치   : " + (", ".join(
        f"ep{r['episode']} band={r['registered_band']} "
        f"(a_att={r['a_att_diagnostic']:.2f}, dpsi_pct={r['delta_psi_percentile_diagnostic']})"
        for r in resc) if resc else "없음"))

    # ── 6) diagnostic omega=inf crossing (n 부족 -> diagnostic only) ─────────
    lo, hi = THREAT_BRACKET["physics.a_att_max"]
    edges = bin_edges(lo, hi, 2.0 * rho / tau ** 2, per_side=4)
    cross = {}
    for name, arm in (("omega2.0", fixed), ("omega_inf", inf)):
        xs, ps, ns = _capture_curve(arm, edges)
        cross[name] = {"cross50_diagnostic": _cross50(xs, ps), "bins": xs,
                       "p": ps, "n_per_bin": ns}
    print(f"6) crossing(진단) : omega2.0 {cross['omega2.0']['cross50_diagnostic']:.2f} · "
          f"omega_inf {cross['omega_inf']['cross50_diagnostic']:.2f}  "
          f"[n={a.n}, 곡선 n=2700 의 약 1/5 -- diagnostic only, 22.45 와 병치 금지]")

    from shepherd.scripts.pivot_manifest import stamp
    pd.pop("_delta", None)
    out = {"manifest": dict(
               stamp(artifact="docs83_E1b_aim_diagnostic"),
               prereg_commit=PREREG_COMMIT,
               prereg_doc="docs/83 §12 + §12-A (E1b)",
               psi_definition="slew_audit.aim_geometry (single source; extracted, float-exact)",
               psi_window_primary="in_band AND t < t_fire (commit step excluded)",
               psi_window_secondary="psi_at_commit = psi at t == t_fire",
               no_fire_episode_rule="fire_step is None -> all in_band steps are pre-fire",
               threat_class="T1", attacker=dict(level="A2", jink_amp=0.6, seed=0,
                   route_gain=a.route_gain, sense_range=a.sense_range),
               limiter_mode="hold", finisher_mobility=0.0,
               omega_max_arms=[float(cfg["attitude"]["omega_max"]), SLEW_UNLIMITED],
               n=a.n, seed0=a.seed0, crn_episode_range=[a.seed0, a.seed0 + a.n - 1],
               boot=BOOT, boot_seed=BOOT_SEED,
               geometry=dict(rho=rho, tau=tau, cone_range_max=rmax,
                             cone_half_angle=cfg["viability"]["cone"]["half_angle"],
                             kill_radius=cfg["physics"]["kill_radius"],
                             dt=cfg["physics"]["dt"],
                             episode_len=cfg["train"]["episode_len"])),
           "integrity_I1": {"fixed_k": kf, "inf_k": ki, "n01": len(n01), "n10": len(n10),
                            "expected_from_E1": {"fixed_k": 84, "inf_k": 85,
                                                 "n01": 1, "n10": 0},
                            "applicable": bool(i1_applicable),
                            "pass": bool(i1) if i1_applicable else None},
           "eligibility": {k: pd[k] for k in
                           ("n_both", "n_only_fixed", "n_only_inf", "n_neither")},
           "psi_at_commit_defined": {"fixed": nc_f, "inf": nc_i},
           "primary_delta_psi": {k: v for k, v in pd.items()
                                 if not k.startswith("n_only") and k != "n_neither"},
           "rescue_localization_diagnostic": resc,
           "crossing_diagnostic": cross,
           "records": {"fixed": fixed, "inf": inf}}
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  -> {p}")


if __name__ == "__main__":
    main()
