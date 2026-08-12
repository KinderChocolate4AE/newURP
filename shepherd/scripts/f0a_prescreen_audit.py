"""Phase III [F-0a] — chi pre-screen 3-arm audit (docs/77 [F] F-0a · third_party_feedback.md §19.3-2).

    python -m shepherd.scripts.f0a_prescreen_audit --episodes 3 \
        --out results/phase3/f0a_prescreen_audit.json

무엇을 재는가
-------------
coarse pilot 의 해석적 교전 pre-screen 이 chi 경계(0.8↔1.2)의 sharpness 를
주입했는지 분리한다. pre-screen 은 chi 와 같은 a·tau^2/2 항을 공유하므로,
audit 전에는 "경계를 발견했다" 서술이 금지된다 (교차검증 v2 §19.3-2).

선언 (결과 열람 전 고정 — 이 audit 은 진단이며 정의·라벨·measure 를 바꾸지 않는다)
--------------------------------------------------------------------------------
1. 슬라이스: coarse pilot 격자의 kappa=0.5 · N=1 · mu=0.4, chi 전 5값
   [0.4, 0.8, 1.2, 1.6, 2.0]. episodes 기본 3 (0..2) — pilot 과 동일 재생성 경로
   (`_cell_world(z, 0, ep)` + `env.reset(seed=ep)` + hold/never 액션).
2. arm 정의:
       P1 = 현행 pre-screen  (reach = cone·sec + |v|·tau + a·tau^2/2)
       P2 = a·tau^2/2 항 제거 (reach 축소 -> pass_P2 ⊆ pass_P1)
       P0 = 스크린 없음 — P1-거부 상태의 무작위 표본에 full solver(label_state)
   delta = P1 통과 ∩ P2 거부 (= a·tau^2/2 항이 살리는 상태).
3. 표본 (rng = np.random.default_rng(7), 에피소드별 quota):
       P1-거부 표본  <= 14 / ep   (full solver -> soundness 실측)
       delta 표본    <= 7 / ep    (full solver -> 이 상태들의 실제 라벨 분포)
4. 판정량:
   (a) false_INF_rate = P1-거부 표본 중 full solver 가 G>0 (caught witness 존재)
       또는 label != INF 인 비율. 0 이면 스크린은 실측으로도 sound — INF 공짜는
       full certificate 와 동치 -> 경계는 스크린 주입이 아니라 실재 (Case 1).
       > 0 이면 스크린이 sharpness 를 주입 (Case 2/3) — 크기를 보고한다.
   (b) delta 표본의 full label 분포 — a·tau^2/2 항 없이는 INF 로 오판됐을 상태들.
   (c) chi 별 pass-rate P1/P2 곡선 — 스크린 선택이 engaged-set 크기에 주는 효과.
5. 해석 한도: kappa=0.5·N=1 슬라이스 한정. 표본 quota 밖 상태는 스크린 판정만
   기록 (전수 full solver 아님 — 비용상 표본 audit).

torch-free.
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np

from shepherd.game import viability as V
from shepherd.scripts.coarse_pilot import (
    ATT_SPEED_MID, RHO, TAU, _cell_world, _engaged, label_state)
from shepherd.scripts.lattice_spec import AXIS_GRID
from shepherd.scripts.measure_harness import THETA, _lattice_hash
from shepherd.scripts.mission_rollout import ROLES, scripted_role_actions
from shepherd.scripts.pivot_manifest import stamp
from shepherd.scripts.threat_v3_gates import _base_env

AUDIT_CHI = AXIS_GRID["chi"][::4]          # pilot 과 동일 [0.4, 0.8, 1.2, 1.6, 2.0]
AUDIT_KAPPA, AUDIT_MU, AUDIT_N = 0.5, 0.4, 1
QUOTA_REJ, QUOTA_DELTA = 14, 7             # per-episode (선언 3)


def _engaged_p2(base, s):
    """P2 arm: a·tau^2/2 항 제거판 pre-screen (선언 2)."""
    apex = np.asarray(s["fin"], float)[0:3]
    tau = float(base.tau_deploy)
    reach = (float(base.cone_range_max) / max(np.cos(float(base.cone_half_angle)), 1e-9)
             + float(np.linalg.norm(s["v_att"])) * tau)
    return float(np.linalg.norm(s["p_att"] - apex)) <= reach


def _full(base, s, *, asset, lim0, v_lim, a_lim, dt):
    """full solver = label_state + G (caught witness 수) 병기."""
    r = label_state(base, s, asset=asset, lim0=lim0, v_lim=v_lim, a_lim=a_lim, dt=dt)
    kw = base._vshot_kwargs(s["p_att"], s["v_att"], s["fin"])
    union = V.build_reachable_union(
        s["p_att"], s["v_att"], tau=base.tau_deploy, a_att_max=base.a_att_max,
        n=2000, n_segments=4, n_dir=32, seed=int(s["t"]), **kw)
    good = np.asarray(union.caught, bool) & np.asarray(union.turn_feasible, bool)
    r["G"] = int(good.sum())
    return r


def run_cell(z, episodes, rng, *, log=print):
    per_ep, rej_evals, delta_evals = [], [], []
    for ep in episodes:
        st = _cell_world(z, 0, int(ep))
        env, base = st.env, _base_env(st.env)
        asset = np.asarray(st.lay.target, float)
        dt = float(base.dt) if hasattr(base, "dt") else 0.05
        v_lim = ATT_SPEED_MID
        a_lim = z["mu"] * z["chi"] * 2.0 * RHO / TAU ** 2
        env.reset(seed=int(ep))
        lims, fin, att = base._states()
        lim0 = [base._p(x).copy() for x in lims]
        states, p1, p2 = [], [], []
        for t in range(1200):
            lims, fin, att = base._states()
            s = dict(ep=int(ep), t=int(t),
                     p_att=base._p(att).copy(), v_att=base._v(att).copy(),
                     fin=np.asarray(fin, float).copy(),
                     lim=[base._p(x).copy() for x in lims])
            states.append(s)
            p1.append(bool(_engaged(base, s)))
            p2.append(bool(_engaged_p2(base, s)))
            acts = scripted_role_actions(env, st.scn, st.lay, roles=ROLES,
                                         limiter_mode="hold", fire_mode="never",
                                         prev_clean=False, states=(lims, fin, att))
            _, _, te, tr, _ = env.step(acts)
            if any(te.values()) or any(tr.values()):
                break
        p1a, p2a = np.asarray(p1), np.asarray(p2)
        idx_rej = np.flatnonzero(~p1a)
        idx_delta = np.flatnonzero(p1a & ~p2a)
        per_ep.append(dict(ep=int(ep), n_steps=len(states),
                           pass_P1=int(p1a.sum()), pass_P2=int(p2a.sum()),
                           n_delta=len(idx_delta)))
        kw = dict(asset=asset, lim0=lim0, v_lim=v_lim, a_lim=a_lim, dt=dt)
        for i in rng.choice(idx_rej, min(QUOTA_REJ, len(idx_rej)), replace=False):
            r = _full(base, states[int(i)], **kw)
            rej_evals.append(dict(ep=int(ep), t=int(i), **r))
        for i in rng.choice(idx_delta, min(QUOTA_DELTA, len(idx_delta)), replace=False):
            r = _full(base, states[int(i)], **kw)
            delta_evals.append(dict(ep=int(ep), t=int(i), **r))

    n_all = sum(e["n_steps"] for e in per_ep)
    false_inf = [r for r in rej_evals if r["G"] > 0 or r["label"] != "INF"]
    lab = lambda rs: {k: sum(r["label"] == k for r in rs)                # noqa: E731
                      for k in ("FREE", "SINGLE", "INF", "AMB")}
    return dict(
        z=z, episodes=per_ep, n_states=n_all,
        pass_rate_P1=sum(e["pass_P1"] for e in per_ep) / max(n_all, 1),
        pass_rate_P2=sum(e["pass_P2"] for e in per_ep) / max(n_all, 1),
        n_delta=sum(e["n_delta"] for e in per_ep),
        rejected_sampled=len(rej_evals),
        false_INF=len(false_inf), false_INF_G=[r["G"] for r in false_inf],
        false_INF_rate=len(false_inf) / max(len(rej_evals), 1),
        rejected_labels=lab(rej_evals),
        delta_sampled=len(delta_evals), delta_labels=lab(delta_evals),
        delta_LN=[round(float(r["LN"]), 4) for r in delta_evals])


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Phase III F-0a pre-screen audit")
    ap.add_argument("--episodes", type=int, default=3)
    ap.add_argument("--out", default="results/phase3/f0a_prescreen_audit.json")
    a = ap.parse_args(argv)
    rng = np.random.default_rng(7)

    cells = []
    for chi in AUDIT_CHI:
        z = dict(chi=chi, kappa=AUDIT_KAPPA, mu=AUDIT_MU, N=AUDIT_N)
        r = run_cell(z, range(a.episodes), rng)
        cells.append(r)
        print(f"chi {chi}: pass P1 {r['pass_rate_P1']:.3f} P2 {r['pass_rate_P2']:.3f} "
              f"delta {r['n_delta']} | rejected sampled {r['rejected_sampled']} "
              f"false-INF {r['false_INF']} ({r['false_INF_rate']:.3f}) "
              f"| delta labels {r['delta_labels']}", flush=True)

    out = dict(
        contract_doc="docs/77 [F] F-0a · third_party_feedback.md §19.3-2",
        declarations="모듈 docstring 1~5 (결과 열람 전 고정)",
        theta=THETA, slice=dict(kappa=AUDIT_KAPPA, mu=AUDIT_MU, N=AUDIT_N),
        episodes=a.episodes, quota=dict(rejected=QUOTA_REJ, delta=QUOTA_DELTA),
        cells=cells,
        reading=("false_INF_rate = 0 전셀 -> 스크린 soundness 실측 -> chi 경계는 "
                 "스크린 주입이 아니라 certificate 와 동치 (Case 1). > 0 -> 크기 보고 "
                 "후 경계 서술에 스크린 caveat 필수 (Case 2/3)."),
        **stamp(artifact="phase3_f0a_prescreen_audit", lattice_hash=_lattice_hash()))
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"-> {p}")


if __name__ == "__main__":
    main()
