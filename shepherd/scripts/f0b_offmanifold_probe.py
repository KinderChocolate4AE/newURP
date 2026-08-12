"""Phase III [F-0b] — off-manifold certificate probe (docs/77 [F] F-0b · third_party_feedback.md §19.4).

    python -m shepherd.scripts.f0b_offmanifold_probe --episodes 5 \
        --out results/phase3/f0b_offmanifold_probe.json

무엇을 재는가
-------------
H3 (반응 문법 -> state-support 편향) 판별: chi=1.2 경계대역의 실제 engaged 상태
근방에, 물리적으로 가능한 섭동으로 도달할 수 있는 **COOP island**
(1 구로는 못 여는데 N 구 constructive 로 열리는 상태) 가 존재하는가.
rollout 불필요 — certificate 재평가만. island 0 -> H3 급락·①-B 실질 강화.
island 존재 -> F-0c (2x2 reachability probe) 로 진행.

선언 (결과 열람 전 고정 — 정의·라벨·measure 불변, coarse pilot 의 것을 그대로 사용)
--------------------------------------------------------------------------------
1. base 상태: chi=1.2 · kappa 전 4값 [0.2, 0.5, 0.8, 1.1] · mu=0.4 · N=4.
   episodes 기본 5 (0..4), pilot 동일 재생성 경로. 에피소드별 P1-engaged 상태에서
   rng(seed 7) 로 max 5 개 표집 -> 셀당 <=25, 총 <=100 base.
2. 섭동 4축 (교차검증 v2 §19.4 — 전부 공격자 상태만 변형, 환경·수비 불변):
       speed   : v_att *= c,  c in {0.5, 0.75}                     (2)
       heading : v_att 를 수직축 중심 회전, ±10°, ±20°, ±30°        (6)
       lateral : v_att 에 수평 횡방향 단위벡터 * 0.15|v| 추가, ±     (2)
       phase   : p_att <- p_att + f*(apex - p_att), f in {0.1, 0.25} (2)
   base 재평가 1 + 섭동 12 = 상태당 13 평가.
3. 판정: coarse pilot 의 label_state 를 그대로 호출.
       island = (label == "AMB") and (LN >= theta)   (= coop_candidate 정의 동일)
   보조 진단: LN >= theta 인데 label == "INF" 인 경우는 island 가 아니다
   (U_cheap 이 sound 하게 닫음) — 별도 카운트만 한다.
4. 보고: 셀별·축별 island 수 / 평가 수, LN 분포 (max, >= theta 수),
   base 대비 이동량. 표본 밖 일반화 금지 — 이 probe 는 존재/부재 진단이다.
5. 해석 한도: 섭동 상태는 "협력이 만들었을 수 있는" 상태의 국소 대리이지
   도달가능성 증명이 아니다 (도달가능성은 F-0c 몫).

torch-free.
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np

from shepherd.scripts.coarse_pilot import (
    ATT_SPEED_MID, RHO, TAU, _cell_world, _engaged, label_state)
from shepherd.scripts.lattice_spec import AXIS_GRID
from shepherd.scripts.measure_harness import THETA, _lattice_hash
from shepherd.scripts.mission_rollout import ROLES, scripted_role_actions
from shepherd.scripts.pivot_manifest import stamp
from shepherd.scripts.threat_v3_gates import _base_env

PROBE_CHI, PROBE_MU, PROBE_N = 1.2, 0.4, 4
PROBE_KAPPA = AXIS_GRID["kappa"][::3]      # [0.2, 0.5, 0.8, 1.1] — pilot 동일
BASE_PER_EP = 5                            # 선언 1


def _rot_z(v, deg):
    th = np.deg2rad(deg)
    c, s = np.cos(th), np.sin(th)
    R = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    return R @ np.asarray(v, float)


def perturbations(s):
    """선언 2 의 12 섭동 (name, s') 목록."""
    p, v = np.asarray(s["p_att"], float), np.asarray(s["v_att"], float)
    apex = np.asarray(s["fin"], float)[0:3]
    out = []
    for c in (0.5, 0.75):
        out.append((f"speed_{c}", dict(s, v_att=v * c)))
    for d in (-30, -20, -10, 10, 20, 30):
        out.append((f"heading_{d:+d}", dict(s, v_att=_rot_z(v, d))))
    horiz = np.array([v[1], -v[0], 0.0])
    n = np.linalg.norm(horiz)
    lat = (horiz / n if n > 1e-9 else np.array([1.0, 0.0, 0.0])) * 0.15 * np.linalg.norm(v)
    for sgn, tag in ((1.0, "+"), (-1.0, "-")):
        out.append((f"lateral_{tag}", dict(s, v_att=v + sgn * lat)))
    for f in (0.1, 0.25):
        out.append((f"phase_{f}", dict(s, p_att=p + f * (apex - p))))
    return out


def run_cell(z, episodes, rng, *, log=print):
    evals = []
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
        engaged_states = []
        for t in range(1200):
            lims, fin, att = base._states()
            s = dict(ep=int(ep), t=int(t),
                     p_att=base._p(att).copy(), v_att=base._v(att).copy(),
                     fin=np.asarray(fin, float).copy(),
                     lim=[base._p(x).copy() for x in lims])
            if _engaged(base, s):
                engaged_states.append(s)
            acts = scripted_role_actions(env, st.scn, st.lay, roles=ROLES,
                                         limiter_mode="hold", fire_mode="never",
                                         prev_clean=False, states=(lims, fin, att))
            _, _, te, tr, _ = env.step(acts)
            if any(te.values()) or any(tr.values()):
                break
        pick = rng.choice(len(engaged_states),
                          min(BASE_PER_EP, len(engaged_states)), replace=False) \
            if engaged_states else []
        kw = dict(asset=asset, lim0=lim0, v_lim=v_lim, a_lim=a_lim, dt=dt)
        for i in pick:
            s0 = engaged_states[int(i)]
            r0 = label_state(base, s0, **kw)
            evals.append(dict(ep=s0["ep"], t=s0["t"], pert="base", **r0))
            for name, sp in perturbations(s0):
                r = label_state(base, sp, **kw)
                evals.append(dict(ep=s0["ep"], t=s0["t"], pert=name, **r))
        log(f"  ep {ep}: engaged {len(engaged_states)}, base picked {len(pick)}",
            flush=True)

    islands = [e for e in evals if e["label"] == "AMB" and e["LN"] >= THETA]
    ln_hi_inf = [e for e in evals if e["label"] == "INF" and e["LN"] >= THETA]
    by_axis = {}
    for e in evals:
        ax = e["pert"].split("_")[0]
        d = by_axis.setdefault(ax, dict(n=0, island=0, LN_max=0.0))
        d["n"] += 1
        d["island"] += int(e["label"] == "AMB" and e["LN"] >= THETA)
        d["LN_max"] = max(d["LN_max"], float(e["LN"]))
    return dict(
        z=z, n_evals=len(evals),
        n_base=sum(e["pert"] == "base" for e in evals),
        n_island=len(islands),
        islands=[dict(ep=e["ep"], t=e["t"], pert=e["pert"],
                      V0=round(float(e["V0"]), 4), L1=round(float(e["L1"]), 4),
                      LN=round(float(e["LN"]), 4),
                      U_cheap=round(float(e["U_cheap"]), 4)) for e in islands],
        n_LN_ge_theta_but_INF=len(ln_hi_inf),
        LN_max=float(max((e["LN"] for e in evals), default=0.0)),
        by_axis=by_axis)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Phase III F-0b off-manifold probe")
    ap.add_argument("--episodes", type=int, default=5)
    ap.add_argument("--out", default="results/phase3/f0b_offmanifold_probe.json")
    a = ap.parse_args(argv)
    rng = np.random.default_rng(7)

    cells = []
    for kappa in PROBE_KAPPA:
        z = dict(chi=PROBE_CHI, kappa=kappa, mu=PROBE_MU, N=PROBE_N)
        print(f"cell chi {PROBE_CHI} kappa {kappa} N {PROBE_N}:", flush=True)
        r = run_cell(z, range(a.episodes), rng)
        cells.append(r)
        ax = ", ".join(f"{k}:{v['island']}" for k, v in r["by_axis"].items())
        print(f"  -> evals {r['n_evals']} islands {r['n_island']} "
              f"LNmax {r['LN_max']:.3f} LN>=theta-but-INF "
              f"{r['n_LN_ge_theta_but_INF']} | islands by axis {{{ax}}}", flush=True)

    n_island = sum(c["n_island"] for c in cells)
    out = dict(
        contract_doc="docs/77 [F] F-0b · third_party_feedback.md §19.4",
        declarations="모듈 docstring 1~5 (결과 열람 전 고정)",
        theta=THETA,
        grid=dict(chi=PROBE_CHI, kappa=list(PROBE_KAPPA), mu=PROBE_MU, N=PROBE_N),
        episodes=a.episodes, base_per_ep=BASE_PER_EP,
        cells=cells, n_island_total=n_island,
        reading=("island 0 -> H3 급락·①-B 실질 강화 (근방에 협력이 열 상태 부재). "
                 "island > 0 -> F-0c 2x2 reachability probe 로 진행 — 도달가능성 "
                 "확인 전 ①-B 서술 금지 (§19.4)."),
        **stamp(artifact="phase3_f0b_offmanifold_probe", lattice_hash=_lattice_hash()))
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"-> {p} | islands total {n_island}")


if __name__ == "__main__":
    main()
