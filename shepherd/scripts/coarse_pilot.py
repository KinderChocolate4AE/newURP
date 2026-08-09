"""Phase III [E] — coarse pilot: 분기 판정용 라벨 prevalence (docs/77 [E] · docs/75 게이트 11).

    python -m shepherd.scripts.coarse_pilot --episodes 1 --cells 0:1               # 스모크
    python -m shepherd.scripts.coarse_pilot --episodes 20 \
        --out results/phase3/coarse_pilot_0_20.json --cells 0:20                   # 샤드

무엇을 재는가
-------------
`Z_master` 부분집합 (core 2D slice: chi x kappa, mu·N 고정층) 에서 라벨 5 종의
**prevalence** 를 관찰해 분기 (①-A / ①-B / ①-C / 정상) 를 판정한다.
계산은 값싼 것만: [D] unblockable-mass 상한 + 값싼 constructive 하한 (docs/77 [E]).

선언 (결과 열람 전 고정 — 이 pilot 이 정의·축·measure·선택규칙을 바꾸지 않는다)
--------------------------------------------------------------------------------
1. **pilot 격자**: `AXIS_GRID["chi"][::4]` (5 값) x `AXIS_GRID["kappa"][::3]` (4 값),
   `mu = 0.4` (격자값; nominal 0.35 에 최근접 상위 — 방어측 유리 방향이므로 INF 판정이
   나오면 더 강한 결론), `N ∈ {1, 4}`. 전부 Z_master 격자값 — 새 점 생성 없음.
2. **D_z^ref 구성** (docs/74 §3.1 은 기전 미봉인 — 여기서 선언): 에피소드 나머지
   자유도(공격자 행동 스펙·spawn·standby)는 v3 TRAIN draw 로 뽑고, core 축이 닿는
   물리 키만 pin 한다:
       physics.a_att_max  = chi * 2 * rho / tau^2
       physics.kill_radius = kappa * rho
       physics.a_lim_max  = mu * a_att_max
       physics.att_speed  = 19.0 (bracket 중앙 — conditioning eta 를 nominal 로 고정)
       train.limits.limiter_v_max = 1.0 * att_speed (nu nominal)
       scenario.n_limiters = N
3. **라벨** (docs/74 §3.4 그대로; 이 pilot 의 도구 수준에서 확정 가능한 것만 certify):
       FREE   : V_0 >= theta                (V_0 = hold 배치 v_shot)
       INF    : U_cheap < theta             (U_cheap = unblockable-mass 상한, N-무관 sound)
       SINGLE : V_0 < theta <= L1           (L1 = 명시적 reachable 배치 1 구의 g=1 최대)
       COOP   : **이 pilot 도구로는 원리적으로 확정 불가** — U^rel_{<=1} (N=1 한정 상한)
                이 게이트 7 relaxation 을 요구한다. 구조적으로 p_COOP = 0 이며, 이는
                협력 부재의 증거가 아니다. 대신 진단 플래그
                coop_candidate = (V_0 < theta) & (L1 < theta) & (LN >= theta)
                (":1 구 후보로는 못 여는데 N 구 constructive 로 열린다") 를 병기한다.
       AMB    : 그 외
4. **상태 표집 = 전 스텝** (stride 폐기 — 2026-08-09 preview 2회가 접근 구간 지배로
   단일 색이 되는 것을 보고 교정. 라벨·판정식은 불변): 모든 스텝에 **해석적 교전
   pre-screen** 을 적용한다. caught endpoint 는 cone 안 = Ball(apex,
   range_max·sec(theta_net)) 안이고 endpoint 이동은 |v|tau + a_max tau^2/2 이하이므로

       |p_att - apex| > range_max·sec(theta_net) + |v_att|·tau + a_att·tau^2/2
       => G = 0 (증인 어떤 것도 caught 불가) => 상한 0 => INF 즉시 (union 계산 불필요)

   sound (거리 필요조건) 이며 비용 O(1). union 계산은 pre-screen 통과 스텝에만.
5. **constructive 후보** (전부 명시적·결정론): probe 4 점 (경로 옆 1.2 r_kill) ·
   hold 위치. reachability 는 보수적 하한 d(T) = v T - v^2/(2a) (정지 출발 ramp 손실
   반영) + NK 존 밖 + 사출 시 인접중복 제거. g_theta = 1 (v >= theta AND not boxed)
   인 배치만 하한으로 인정 (docs/74 §3.2).

읽는 법 (docs/77 [E]): p_COOP(>0 불가) 대신 p_coop_candidate 참조. p_INF 지배 → ①-B ·
p_SINGLE 지배 + candidate 부재 → ①-A · p_AMB 지배 → ①-C (문제 정의 단순화).

torch-free.
"""
from __future__ import annotations

import argparse
import itertools
import json
import pathlib

import numpy as np

from shepherd.env_sys import RewardSpec, ratified_system
from shepherd.game import viability as V
from shepherd.m4_env import build_m4_env
from shepherd.scale_v2 import draw_threat_v3
from shepherd.scripts.cert_unblockable import unblockable_from_union
from shepherd.scripts.lattice_spec import AXIS_GRID
from shepherd.scripts.measure_harness import THETA, _lattice_hash, probe_placement
from shepherd.scripts.mission_rollout import ROLES, scripted_role_actions
from shepherd.scripts.pivot_manifest import stamp
from shepherd.scripts.threat_v3_gates import _base_env

# ── pilot 선언 (결과 전 고정) ────────────────────────────────────────────────
PILOT_CHI = AXIS_GRID["chi"][::4]                 # [0.4, 0.8, 1.2, 1.6, 2.0]
PILOT_KAPPA = AXIS_GRID["kappa"][::3]             # [0.2, 0.5, 0.8, 1.1]
PILOT_MU = 0.4                                    # 격자값 (선언 근거는 모듈 docstring)
PILOT_N = (1, 4)
ATT_SPEED_MID = 19.0                              # bracket (8,30) 중앙
RHO, TAU = 1.77, 0.30                             # 동결 절대값 (m4_config)
R_NK = 6.0

CELLS = [dict(chi=c, kappa=k, mu=PILOT_MU, N=n)
         for c in PILOT_CHI for k in PILOT_KAPPA for n in PILOT_N]


def _cell_world(z, seed, ep):
    """D_z^ref 선언 (docstring 2): v3 TRAIN draw + core 축 pin."""
    d = draw_threat_v3(seed, ep, "train")
    a_att = z["chi"] * 2.0 * RHO / TAU ** 2
    cfg = dict(d["cfg"])
    cfg.update({
        "physics.a_att_max": a_att,
        "physics.kill_radius": z["kappa"] * RHO,
        "physics.a_lim_max": z["mu"] * a_att,
        "physics.att_speed": ATT_SPEED_MID,
        "train.limits.limiter_v_max": 1.0 * ATT_SPEED_MID,
        "scenario.n_limiters": int(z["N"]),
    })
    return build_m4_env(0, ep, system=ratified_system(),
                        reward=RewardSpec(w_kill=0.5, enabled=True),
                        attacker=d["attacker"], spawn=d["spawn"],
                        standby=d["standby"], extra_cfg=cfg)


def _reach_ok(c, p0, T, v_max, a_max):
    """보수적 reachability: 정지 출발 ramp 손실 반영 최대 이동거리."""
    T = max(float(T), 0.0)
    t_ramp = v_max / max(a_max, 1e-9)
    d_max = (0.5 * a_max * T * T) if T <= t_ramp else (v_max * T - v_max ** 2 / (2 * a_max))
    return float(np.linalg.norm(np.asarray(c, float) - np.asarray(p0, float))) <= d_max


def _assignable(points, lim0, T, v_max, a_max):
    """k 점 <-> limiter 단사 배정 존재 여부 (N<=6, k<=4 -> 순열 전수)."""
    k = len(points)
    if k > len(lim0):
        return False
    ok = [[_reach_ok(p, l0, T, v_max, a_max) for l0 in lim0] for p in points]
    return any(all(ok[i][perm[i]] for i in range(k))
               for perm in itertools.permutations(range(len(lim0)), k))


def _admissible(points, asset):
    return all(float(np.linalg.norm(np.asarray(p) - asset)) > R_NK for p in points)


def _g_eval(union, layouts, kill_radius):
    """배치 목록 -> (v, g) 목록. g = 1[v >= theta AND not boxed] (docs/74 §3.2)."""
    res = V.eval_union_with_limiter_sets(union, layouts, kill_radius)
    return [(float(r.v_shot_soft), int(r.v_shot_soft >= THETA and not r.boxed_in))
            for r in res]


def _engaged(base, s):
    """해석적 교전 pre-screen (docstring 4). False -> G=0 certify -> INF 즉시."""
    apex = np.asarray(s["fin"], float)[0:3]
    tau = float(base.tau_deploy)
    reach = (float(base.cone_range_max) / max(np.cos(float(base.cone_half_angle)), 1e-9)
             + float(np.linalg.norm(s["v_att"])) * tau
             + 0.5 * float(base.a_att_max) * tau ** 2)
    return float(np.linalg.norm(s["p_att"] - apex)) <= reach


def label_state(base, s, *, asset, lim0, v_lim, a_lim, dt):
    kw = base._vshot_kwargs(s["p_att"], s["v_att"], s["fin"])
    union = V.build_reachable_union(
        s["p_att"], s["v_att"], tau=base.tau_deploy, a_att_max=base.a_att_max,
        n=2000, n_segments=4, n_dir=32, seed=int(s["t"]), **kw)
    r_kill = float(base.kill_radius)
    T = float(s["t"]) * dt

    v0, _ = _g_eval(union, [s["lim"]], r_kill)[0]
    m = unblockable_from_union(union, asset=asset, r_nk=R_NK, r_kill=r_kill)
    u_cheap = m["v_max"]

    probes = probe_placement(base, s)
    singles = [[p] for p in probes] + [[l] for l in s["lim"]]
    singles = [ly for ly in singles if _admissible(ly, asset)
               and _assignable(ly, lim0, T, v_lim, a_lim)]
    L1 = max((v for v, g in _g_eval(union, singles, r_kill) if g), default=0.0) \
        if singles else 0.0

    quads = [ly for ly in (probes, list(s["lim"]))
             if _admissible(ly, asset) and _assignable(ly, lim0, T, v_lim, a_lim)]
    LN = max([L1] + [v for v, g in _g_eval(union, quads, r_kill) if g]) \
        if quads else L1

    if v0 >= THETA:
        lab = "FREE"
    elif u_cheap < THETA:
        lab = "INF"
    elif L1 >= THETA:
        lab = "SINGLE"
    else:
        lab = "AMB"
    return dict(label=lab, V0=v0, U_cheap=u_cheap, L1=L1, LN=LN, U=m["U"],
                coop_candidate=int(lab == "AMB" and LN >= THETA))


def run_cell(z, episodes, *, log=print):
    rows, ep_stats = [], []
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
        ep_rows = []
        for t in range(1200):                       # 전 스텝 (stride 없음)
            lims, fin, att = base._states()
            s = dict(ep=int(ep), t=int(t),
                     p_att=base._p(att).copy(), v_att=base._v(att).copy(),
                     fin=np.asarray(fin, float).copy(),
                     lim=[base._p(x).copy() for x in lims])
            if _engaged(base, s):
                r = label_state(base, s, asset=asset, lim0=lim0,
                                v_lim=v_lim, a_lim=a_lim, dt=dt)
                r["engaged"] = 1
            else:                                   # 해석적 G=0 -> 상한 0 -> INF (공짜)
                r = dict(label="INF", V0=0.0, U_cheap=0.0, L1=0.0, LN=0.0,
                         U=0, coop_candidate=0, engaged=0)
            ep_rows.append(r)
            acts = scripted_role_actions(env, st.scn, st.lay, roles=ROLES,
                                         limiter_mode="hold", fire_mode="never",
                                         prev_clean=False, states=(lims, fin, att))
            _, _, te, tr, _ = env.step(acts)
            if any(te.values()) or any(tr.values()):
                break
        rows.extend(ep_rows)
        ep_stats.append(dict(                       # docs/74 §4 C_N^ep 형 exists 통계
            ep=int(ep), n_steps=len(ep_rows),
            n_engaged=sum(r["engaged"] for r in ep_rows),
            ep_FREE=int(any(r["label"] == "FREE" for r in ep_rows)),
            ep_L1=int(any(r["L1"] >= THETA for r in ep_rows)),
            ep_LN=int(any(r["LN"] >= THETA for r in ep_rows))))

    def _prev(rs):
        n = max(len(rs), 1)
        out = {f"p_{k}": sum(r["label"] == k for r in rs) / n
               for k in ("FREE", "SINGLE", "COOP", "INF", "AMB")}
        out["p_coop_candidate"] = sum(r["coop_candidate"] for r in rs) / n
        return out

    eng = [r for r in rows if r["engaged"]]
    return dict(
        z=z, n_states=len(rows), n_engaged=len(eng),
        prevalence=_prev(rows),                     # 공식 라벨 prevalence (전 스텝)
        prevalence_engaged=_prev(eng),              # 진단: 교전 상태 한정
        episode_stats=ep_stats,
        V0_max=float(max((r["V0"] for r in rows), default=0.0)),
        LN_max=float(max((r["LN"] for r in rows), default=0.0)))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Phase III coarse pilot (분기 판정)")
    ap.add_argument("--episodes", type=int, default=20)
    ap.add_argument("--cells", default="0:%d" % len(CELLS),
                    help="샤드 범위 i0:i1 (CELLS 인덱스)")
    ap.add_argument("--out", default="results/phase3/coarse_pilot.json")
    a = ap.parse_args(argv)
    i0, i1 = (int(x) for x in a.cells.split(":"))

    out_cells = []
    for i in range(i0, min(i1, len(CELLS))):
        z = CELLS[i]
        r = run_cell(z, range(a.episodes))
        out_cells.append(r)
        p, pe = r["prevalence"], r["prevalence_engaged"]
        print(f"[{i}] chi {z['chi']} kappa {z['kappa']} N {z['N']}: "
              f"eng {r['n_engaged']}/{r['n_states']} | all INF {p['p_INF']:.2f} "
              f"AMB {p['p_AMB']:.2f} | eng FREE {pe['p_FREE']:.2f} "
              f"SINGLE {pe['p_SINGLE']:.2f} INF {pe['p_INF']:.2f} "
              f"AMB {pe['p_AMB']:.2f} cc {pe['p_coop_candidate']:.2f} | "
              f"V0max {r['V0_max']:.2f} LNmax {r['LN_max']:.2f}", flush=True)

    out = dict(
        contract_doc="docs/75 게이트 11 · docs/77 [E] (coarse pilot)",
        declarations="모듈 docstring 1~5 (결과 열람 전 고정)",
        theta=THETA, pilot_grid=dict(chi=PILOT_CHI, kappa=PILOT_KAPPA,
                                     mu=PILOT_MU, N=list(PILOT_N)),
        episodes=a.episodes, cells=out_cells,
        note=("p_COOP = 0 은 구조적(도구 한계 — U^rel_{<=1} 은 게이트 7). "
              "coop_candidate 를 참조. 단일 색 지도 금지 (docs/77 [E])."),
        **stamp(artifact="phase3_coarse_pilot", lattice_hash=_lattice_hash()))
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"-> {p}")


if __name__ == "__main__":
    main()
