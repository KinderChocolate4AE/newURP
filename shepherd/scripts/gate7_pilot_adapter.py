"""Phase III 게이트 7 — pilot replay adapter (docs/79 r1 §4 · 후속 검토 ⑦).

    python -m shepherd.scripts.gate7_pilot_adapter --cells chi12 --episodes 20 \
        --out results/phase3/gate7_pilot_chi12.json

목표 (얇게 — 새 sampling/filter/witness family 금지)
--------------------------------------------------------------------------------
2026-08-10 coarse pilot 의 동일 episode/state 를 재생성해, **당시 cheap 라벨이
AMB 였던 engaged 상태만** 골라, **당시와 동일한 witness union** 을 게이트 7 solver
(gate7_relaxation.u_rel) 에 넘긴다. coarse_pilot 의 상태생성·engaged predicate·
label_state·union builder 를 전부 **import 재사용** (복붙 재구현 금지).

parity gate (결과 열람 전 강제 — docs/79 r1 위험 1·2)
----------------------------------------------------
각 상태에서 `label_state` 를 재호출해 cheap 라벨을 재현한다. 재현 라벨이 AMB 가
아니면 그 상태는 **게이트 7 계산에서 제외** (원래 AMB 였던 것만 S_G7). union 은
동일 시드(`seed=int(t)`)로 재빌드 — deterministic 이라 byte-identical.
witness family/turn-filter/G 정의 재분류·정규화 금지: bad_paths·G 는 judge 가
낸 그 값 그대로.

r2 (docs/79 r2 — temporal-semantics repair)
-------------------------------------------
게이트 7 인스턴스의 reachability 는 **현 snapshot limiter 상태** (위치 s["lim"],
속력 |v_i(t)|) 에서 미래 horizon **[0, τ_deploy]** 의 outer 상계
(`d_max_outer`) 로만 계산한다. episode 경과시간 사용 금지 (G7-F).
cheap-label parity 호출 (`label_state`) 은 pilot 원본 그대로 유지 (episode-initial
lim0 + T=t·dt — 원래 AMB 였는지의 재현이 목적이므로 변경 금지).

**오염 통제 (docs/79 r2)**: primary tranche = 에피소드 **20..39** (미접촉).
ep 0..19 는 development set — r1 dry-run·진단에 노출됐으므로 confirmatory 집계
금지 (--ep-start 0 으로 돌리면 파일명에 dev 표기 권장).

state cap (결과 전 고정 — docs/79 r1 위험 3)
-------------------------------------------
셀당 AMB 상태 ≤ CAP_PER_CELL. 초과 시 **episode-stratified deterministic** 표집
(np.random.default_rng(7), 에피소드별 균등 몫). CAP 이하면 전수.

산출물: 셀별 funnel (closed@h/h2/h4) · U1/U4 분위수 · ΔU · certification margin
(θ − U4) · unresolved. 배선 유효성(parity·monotone·nesting)이 확인되면 결과
방향과 무관하게 서버 확장 가능 (favorable 여부는 gate 아님).

torch-free. long-run 은 서버 (long-run policy).
"""
from __future__ import annotations

import argparse
import json
import pathlib
from fractions import Fraction

import numpy as np

from shepherd.game import viability as V
from shepherd.scripts.coarse_pilot import (
    ATT_SPEED_MID, RHO, R_NK, TAU, _cell_world, _engaged, label_state)
from shepherd.scripts.gate7_relaxation import make_instance, u_rel
from shepherd.scripts.lattice_spec import AXIS_GRID
from shepherd.scripts.measure_harness import THETA, _lattice_hash
from shepherd.scripts.mission_rollout import ROLES, scripted_role_actions
from shepherd.scripts.pivot_manifest import stamp
from shepherd.scripts.threat_v3_gates import _base_env

CAP_PER_CELL = 100
FREE_CAP = 20                               # FREE positive-control 표본/셀 (서버 확장)
LEVELS = (0, 1, 2)                          # h, h/2, h/4
N_SET = (1, 4)
THETA_F = Fraction(9, 10)

# 셀 세트 (docs/79 r1 §4 · full = 서버 확장: pilot 격자 전체, B1 prevalence 만)
CELL_SETS = {
    "chi12": [dict(chi=1.2, kappa=k, mu=0.4, N=4) for k in (0.2, 1.1)],   # 최우선
    "chi08": [dict(chi=0.8, kappa=k, mu=0.4, N=4) for k in (0.2, 1.1)],   # neg-control
    "chi16": [dict(chi=1.6, kappa=k, mu=0.4, N=4) for k in (0.2, 1.1)],
    "full": [dict(chi=c, kappa=k, mu=0.4, N=4)
             for c in (0.4, 0.8, 1.2, 1.6, 2.0) for k in (0.2, 0.5, 0.8, 1.1)],
}


def _union_for(base, s):
    """label_state 와 **동일 인자·동일 시드** union (byte-identical 재빌드)."""
    kw = base._vshot_kwargs(s["p_att"], s["v_att"], s["fin"])
    return V.build_reachable_union(
        s["p_att"], s["v_att"], tau=base.tau_deploy, a_att_max=base.a_att_max,
        n=2000, n_segments=4, n_dir=32, seed=int(s["t"]), **kw)


def _gate7_input(union, s, *, asset, lim_snap, lim_v0, v_lim, a_lim, r_kill):
    """union → make_instance (r2). bad = turn_feasible & ~caught · G = caught & tf.
    witness 경로는 path_blocks 그대로 (재분류·병합·정규화 없음).
    reachability = snapshot limiter 상태 + 미래 [0, τ] — 경과시간 입력 없음 (G7-F)."""
    caught = np.asarray(union.caught, bool)
    tf = np.asarray(union.turn_feasible, bool)
    paths = []                              # per-witness (T_b, 3), 블록 순서 = concat 순서
    for pb in union.path_blocks:
        for w in range(pb.shape[0]):
            paths.append(pb[w])
    bad_idx = np.flatnonzero(tf & ~caught)
    G = int((caught & tf).sum())
    bad_paths = [paths[i] for i in bad_idx]
    return make_instance(
        bad_paths=bad_paths, n_good=G, lim0=lim_snap, lim_v0=lim_v0,
        T=TAU, v_lim=v_lim, a_lim=a_lim,
        asset=asset, r_nk=R_NK, r_kill=r_kill), dict(n_bad=len(bad_paths), G=G)


def _collect_amb(z, episodes, rng, log, collect_free=False):
    """셀의 원래-AMB engaged 상태 수집 (label_state parity). collect_free 시
    FREE 상태 (V0>=θ) 도 별도 수집 — soundness positive control 용 (U>=V0 검사만,
    새 과학 질문 아님). 반환 (amb, free)."""
    amb, free, seen = [], [], 0
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
        for t in range(1200):
            lims, fin, att = base._states()
            s = dict(ep=int(ep), t=int(t),
                     p_att=base._p(att).copy(), v_att=base._v(att).copy(),
                     fin=np.asarray(fin, float).copy(),
                     lim=[base._p(x).copy() for x in lims])
            if _engaged(base, s):
                seen += 1
                r = label_state(base, s, asset=asset, lim0=lim0,
                                v_lim=v_lim, a_lim=a_lim, dt=dt)
                if r["label"] in (("AMB", "FREE") if collect_free else ("AMB",)):
                    lim_v0 = [float(np.linalg.norm(base._v(x))) for x in lims]
                    rec = dict(s=s, base=base, asset=asset,
                               lim_v0=lim_v0, v_lim=v_lim, a_lim=a_lim,
                               r_kill=float(base.kill_radius),
                               cheap=dict(V0=r["V0"], U_cheap=r["U_cheap"],
                                          L1=r["L1"], LN=r["LN"]))
                    (amb if r["label"] == "AMB" else free).append(rec)
            acts = scripted_role_actions(env, st.scn, st.lay, roles=ROLES,
                                         limiter_mode="hold", fire_mode="never",
                                         prev_clean=False, states=(lims, fin, att))
            _, _, te, tr, _ = env.step(acts)
            if any(te.values()) or any(tr.values()):
                break
        log(f"  ep {ep}: engaged-seen {seen}, AMB so far {len(amb)}", flush=True)
    if len(amb) > CAP_PER_CELL:               # episode-stratified deterministic
        idx = rng.choice(len(amb), CAP_PER_CELL, replace=False)
        amb = [amb[int(i)] for i in sorted(idx)]
    if len(free) > FREE_CAP:
        idx = rng.choice(len(free), FREE_CAP, replace=False)
        free = [free[int(i)] for i in sorted(idx)]
    return amb, free


def _quant(vals):
    if not vals:
        return {}
    a = np.array([float(v) for v in vals])
    return {q: round(float(np.quantile(a, q)), 4) for q in (0.1, 0.5, 0.9)}


def _score_free(free, log):
    """FREE positive control: soundness U4_bound >= V0 (위반 = artifact invalid)
    + 폐쇄 여부 (V0>=θ 상태는 닫히면 안 됨). 새 판정량 없음 — 검증 전용."""
    rows, viol = [], 0
    for a in free:
        inst, meta = _gate7_input(_union_for(a["base"], a["s"]), a["s"],
                                  asset=a["asset"], lim_snap=a["s"]["lim"],
                                  lim_v0=a["lim_v0"],
                                  v_lim=a["v_lim"], a_lim=a["a_lim"],
                                  r_kill=a["r_kill"])
        r4 = u_rel(inst, 4, level=2)
        sound = float(r4["u_bound"]) >= a["cheap"]["V0"] - 1e-9
        viol += (not sound)
        rows.append(dict(ep=a["s"]["ep"], t=a["s"]["t"], V0=round(a["cheap"]["V0"], 4),
                         U4_bound=str(r4["u_bound"]), n_sigs=r4["n_sigs"],
                         closed=bool(r4["u_bound"] < THETA_F), sound=sound))
    return dict(n=len(rows), sound_viol=viol,
                n_closed=sum(r["closed"] for r in rows), rows=rows)


def run_cell(z, episodes, rng, *, log=print, free_control=False):
    amb, free = _collect_amb(z, episodes, rng, log, collect_free=free_control)
    invalid, rows = [], []
    for a in amb:
        inst4, meta = _gate7_input(_union_for(a["base"], a["s"]), a["s"],
                                   asset=a["asset"], lim_snap=a["s"]["lim"],
                                   lim_v0=a["lim_v0"],
                                   v_lim=a["v_lim"], a_lim=a["a_lim"],
                                   r_kill=a["r_kill"])
        # G=0 이면 cheap 단계에서 이미 INF 였어야 → AMB 와 모순 (parity 위반)
        if meta["G"] == 0:
            invalid.append(dict(ep=a["s"]["ep"], t=a["s"]["t"], why="G0_but_AMB"))
            continue
        # d_max_outer 의 v_max·τ 항이 상계이려면 |v0| <= v_lim 필수 (docs/79 r2)
        if max(a["lim_v0"]) > a["v_lim"] + 1e-6:
            invalid.append(dict(ep=a["s"]["ep"], t=a["s"]["t"], why="v0_gt_vmax",
                                v0=max(a["lim_v0"])))
            continue
        u4 = [u_rel(inst4, 4, level=lv) for lv in LEVELS]
        u1 = [u_rel(inst4, 1, level=lv) for lv in LEVELS]
        # 배선 invariants (docs/79 r1 stop condition)
        u4v = [r["u"] for r in u4]
        if not (u4v[0] >= u4v[1] >= u4v[2]):
            invalid.append(dict(ep=a["s"]["ep"], t=a["s"]["t"], why="mono4",
                                us=[str(x) for x in u4v]))
            continue
        if not all(u1[lv]["u"] <= u4[lv]["u"] for lv in LEVELS):
            invalid.append(dict(ep=a["s"]["ep"], t=a["s"]["t"], why="nesting"))
            continue
        # INF 는 certified bound 로만 (status CAP 이면 u_bound 사용)
        bound4 = u4[-1]["u_bound"]
        closed = [u4[lv]["u_bound"] < THETA_F for lv in LEVELS]
        rows.append(dict(
            ep=a["s"]["ep"], t=a["s"]["t"], n_bad=meta["n_bad"], G=meta["G"],
            U1_fin=str(u1[-1]["u"]), U4_fin=str(u4v[-1]),
            U4_bound=str(bound4), status4=u4[-1]["status"],
            dU=float(u4v[-1] - u1[-1]["u"]),
            margin=float(THETA_F - bound4),
            n_sigs4=u4[-1]["n_sigs"],
            frac_bad_touched=round(u4[-1]["frac_bad_touched"], 4),
            closed_h=closed[0], closed_h2=closed[1], closed_h4=closed[2]))

    n = len(rows)
    closed4 = [r for r in rows if r["closed_h4"]]
    fc = _score_free(free, log) if free_control else None
    return dict(
        free_control=fc,
        z=z, n_amb=len(amb), n_scored=n, n_invalid=len(invalid),
        invalid=invalid[:20],
        p_close_h=sum(r["closed_h"] for r in rows) / max(n, 1),
        p_close_h2=sum(r["closed_h2"] for r in rows) / max(n, 1),
        p_close_h4=sum(r["closed_h4"] for r in rows) / max(n, 1),
        U1_quant=_quant([Fraction(r["U1_fin"]) for r in rows]),
        U4_quant=_quant([Fraction(r["U4_fin"]) for r in rows]),
        dU_quant=_quant([r["dU"] for r in rows]),
        margin_quant=_quant([r["margin"] for r in rows]),
        n_sigs_zero=sum(r["n_sigs4"] == 0 for r in rows),
        frac_touched_quant=_quant([r["frac_bad_touched"] for r in rows]),
        n_closed_h4=len(closed4),
        rows=rows)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Gate 7 pilot replay adapter (r2)")
    ap.add_argument("--cells", choices=list(CELL_SETS) + ["dry"], default="chi12")
    ap.add_argument("--cell-range", default=None,
                    help="셀 샤딩 i0:i1 (full 서버 확장용)")
    ap.add_argument("--ep-start", type=int, default=20,
                    help="primary tranche 시작 (r2: 20..39 미접촉. 0..19 = dev set)")
    ap.add_argument("--episodes", type=int, default=20)
    ap.add_argument("--free-control", action="store_true",
                    help="FREE 상태 positive control (soundness U>=V0) 동시 수집")
    ap.add_argument("--out", default="results/phase3/gate7_pilot.json")
    a = ap.parse_args(argv)
    rng = np.random.default_rng(7)
    cellset = ([CELL_SETS["chi12"][0]] if a.cells == "dry" else CELL_SETS[a.cells])
    if a.cell_range:
        i0, i1 = (int(x) for x in a.cell_range.split(":"))
        cellset = cellset[i0:i1]
    eps = range(a.ep_start, a.ep_start + a.episodes)

    out_cells = []
    for z in cellset:
        print(f"cell chi {z['chi']} kappa {z['kappa']} N {z['N']} eps {a.ep_start}..{a.ep_start+a.episodes-1}:", flush=True)
        r = run_cell(z, eps, rng, free_control=a.free_control)
        out_cells.append(r)
        print(f"  -> AMB {r['n_amb']} scored {r['n_scored']} invalid {r['n_invalid']} "
              f"| p_close h/h2/h4 {r['p_close_h']:.2f}/{r['p_close_h2']:.2f}/"
              f"{r['p_close_h4']:.2f} | U4 med {r['U4_quant'].get(0.5)} "
              f"U1 med {r['U1_quant'].get(0.5)} dU med {r['dU_quant'].get(0.5)}",
              flush=True)

    out = dict(
        contract_doc="docs/79 r1 §4 · 후속 ⑦ adapter",
        theta=THETA, cap_per_cell=CAP_PER_CELL, levels=list(LEVELS),
        cells=out_cells,
        reading=("배선 유효(parity·mono·nesting)면 결과 방향 무관 서버 확장. "
                 "closed@h4 = certified U4_bound < θ. ΔU=U4−U1 이 핵심 부수결과 "
                 "(패턴 A U1≈U4 / B U1≪U4<θ / C U1<θ≤U4)."),
        **stamp(artifact="phase3_gate7_pilot_adapter", lattice_hash=_lattice_hash()))
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"-> {p}")


if __name__ == "__main__":
    main()
