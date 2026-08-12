"""Phase III 게이트 10 — iso-Π reduction validation, Tier 1 (contract = docs/78 §1).

    python -m shepherd.scripts.gate10_isopi --tier1 --out results/phase3/gate10_tier1.json

변환 공식 (docs/78 §1 · 인벤토리 = temp_research_note/2026-08-13):
    길이 α · 시간 β:  x'=αx, t'=βt, v'=(α/β)v, a'=(α/β²)a, f'=f/β, ω'=ω/β
    T1-L = (α,β)=(2,1) · T1-T = (1,2). α·β 가 2의 거듭제곱이라 스케일 연산이
    float 에서 정확 → bit-수준 상사성이 기대되고, 1e-6 bar 는 그 위의 안전여유.

선언 (결과 열람 전 고정)
------------------------
1. 검사점: z = chi {0.8, 1.6} × kappa 0.5 × mu 0.4 × N 4 (Z_master 격자값),
   episodes 0..2, seed 0. 상태 = 전 스텝 (pairing key = step_idx).
2. fixture pin (양계 동일 규율): coarse_pilot 의 z-pin 5종에 더해
   **train.limits.adversary_v_max 를 1.5×att_speed 로 명시 pin** — 이유:
   m4_episode_config 의 draw_threat 가 절대 단위 bracket 에서 뽑은 값이 pilot
   pin 에 덮이지 않고 남는 유일한 키라서, pin 하지 않으면 그 자체가 숨은 차원
   상수가 된다 (CRN 규율, docs/78 §1). 나머지 차원 키 전부(길이 12·시간 2·
   속도 4·가속 3·각속도 3)를 양계에 **명시 override** 로 대칭 주입한다 —
   base 계는 α=β=1 의 동일 코드 경로 (비대칭 해석 경로 제거).
3. 판정 (docs/78 §1): 스텝별 (a) engaged mask 일치 (b) engaged 상태의 hold
   배치 v_shot_soft |Δ| ≤ 1e-6 (c) per-witness (caught ∧ turn_feasible) mask
   bit 일치 + witness 수 일치. 불일치는 boundary 조사 대상으로 상태 좌표 기록.
4. transform self-check (rollout 전): step 0 의 normalized invariants —
   p_att/ρ · v_att·τ/ρ · limiter/ρ · apex/ρ · |target−p_att|/ρ · a_att·τ²/ρ —
   양계 일치 ≤ 1e-9. 실패 시 v_shot 비교 전에 state-generation 문제로 판정
   (localization 순서: state → witness → judge, 인벤토리 노트).
5. 파이프라인 가정 (코드 감사로 폐쇄, 2026-08-13 인벤토리 2차): 가산 노이즈
   없음 · witness 는 attacker_turn_limited=False (omega_att_max 미사용 — env 의
   하드코딩 8.0 은 attacker_ladder 본문에서 미참조 = 실행 경로 비활성) ·
   viability _EPS 전 용례 numerical guard.

torch-free.
"""
from __future__ import annotations

import argparse
import json
import pathlib
from dataclasses import replace

import numpy as np

from shepherd.env_sys import RewardSpec, ratified_system
from shepherd.game import viability as V
from shepherd.m4_env import build_m4_env
from shepherd.scale_v2 import draw_threat_v3
from shepherd.scripts.coarse_pilot import RHO, TAU, _engaged
from shepherd.scripts.measure_harness import _lattice_hash
from shepherd.scripts.mission_rollout import ROLES, scripted_role_actions
from shepherd.scripts.pivot_manifest import stamp
from shepherd.scripts.threat_v3_gates import _base_env

ATT_SPEED0 = 19.0                           # pilot 과 동일 (bracket 중앙)
DT0 = 0.05                                  # m4 physics.dt (인벤토리 확정)
TRANSFORMS = {"T1L": (2.0, 1.0), "T1T": (1.0, 2.0)}
Z_POINTS = [dict(chi=c, kappa=0.5, mu=0.4, N=4) for c in (0.8, 1.6)]
EPISODES = range(3)
TOL_STATE, TOL_V = 1e-9, 1e-6

# 인벤토리 동결표 (2026-08-13 2차) — cfg 차원 키 전수. base 값은 resolved cfg 에서
# 읽지 않고 여기 명시한다 (양계 동일 override 경로 — 값 출처: m4_config M4_OVERRIDES
# + scale_v2 SCALE_V2_CFG + make_env 기본 layout. 틀리면 T1 이 아니라 base 구축이
# 즉시 실패하므로 자기검증적이다).
def _cfg_overrides(z, alpha, beta):
    L, T = alpha, beta
    vs, as_, ws = L / T, L / T ** 2, 1.0 / T
    rho, tau = RHO * L, TAU * T
    a_att = z["chi"] * 2.0 * rho / tau ** 2
    att_v = ATT_SPEED0 * vs
    return {
        # --- z pins (pilot 동일 + 스케일) ---
        "physics.a_att_max": a_att,
        "physics.kill_radius": z["kappa"] * rho,
        "physics.a_lim_max": z["mu"] * a_att,
        "physics.att_speed": att_v,
        "train.limits.limiter_v_max": 1.0 * att_v,
        "scenario.n_limiters": int(z["N"]),
        # --- CRN pin (선언 2) ---
        "train.limits.adversary_v_max": 1.5 * att_v,
        # --- 길이 ---
        "physics.net_radius": rho,
        "viability.cone.range_max": 8.22 * L,
        "viability.cone.range_min": 0.0 * L,
        # --- 시간 ---
        "physics.tau_deploy": tau,
        "physics.dt": DT0 * T,
        # --- 각속도 ---
        "attitude.omega_max": 2.0 * ws,
        "train.limits.limiter_omega": 2.5 * ws,
        "train.limits.adversary_omega": 10.0 * ws,
    }


def _layout_overrides(base_lay, alpha):
    """base 계의 resolved layout 을 α 배 (양계 대칭 — base 는 α=1 로 no-op)."""
    L = alpha
    return {
        "train.layout.target": tuple(float(x) * L for x in np.asarray(base_lay["target"])),
        "train.layout.ring_center": tuple(float(x) * L for x in np.asarray(base_lay["ring_center"])),
        "train.layout.ring_radius": base_lay["ring_radius"] * L,
        "train.layout.adversary_start_x": base_lay["adversary_start_x"] * L,
        "train.layout.finisher_p0": tuple(float(x) * L for x in np.asarray(base_lay["finisher_p0"])),
        "train.layout.target_radius": base_lay["target_radius"] * L,
        "train.layout.r_ring": base_lay["r_ring"] * L,
        "train.layout.x_fire": base_lay["x_fire"] * L,
    }


def _resolved_base_layout(d_cfg):
    """base nested cfg 에서 layout 원값 추출 (한 번만)."""
    from shepherd.m4_config import m4_config
    cfg = m4_config(dict(d_cfg))
    lo = cfg["train"]["layout"]
    return dict(target=lo["target"], ring_center=lo["ring_center"],
                ring_radius=float(lo["ring_radius"]),
                adversary_start_x=float(lo["adversary_start_x"]),
                finisher_p0=lo["finisher_p0"],
                target_radius=float(lo["target_radius"]),
                r_ring=float(lo["r_ring"]), x_fire=float(lo["x_fire"]))


def _scaled_specs(d, alpha, beta):
    att = d["attacker"]
    att2 = replace(
        att,
        sense_range=att.sense_range * alpha,
        sprint_range=att.sprint_range * alpha,
        slowdown_range=(att.slowdown_range[0] * alpha, att.slowdown_range[1] * alpha),
        jink_terminal_r=att.jink_terminal_r * alpha,
        jink_freq=att.jink_freq / beta,
        homing_gain=att.homing_gain / beta,
        bait_range=(att.bait_range[0] * alpha, att.bait_range[1] * alpha))
    sp = d["spawn"]
    # r_lat: THREAT_V3_SPAWN 이 명시하지 않는 기본값 5.0 m — T1-L 첫 스모크가
    # 잡아낸 숨은 길이 상수 (t=0 spawn 횡원판 반경). 반드시 스케일.
    sp2 = replace(sp, dx=sp.dx * alpha, r_lat=sp.r_lat * alpha,
                  r_range=(sp.r_range[0] * alpha, sp.r_range[1] * alpha))
    st2 = replace(d["standby"], R=d["standby"].R * alpha)
    return att2, sp2, st2


def build_world(z, ep, alpha, beta, base_lay):
    d = draw_threat_v3(0, int(ep), "train")
    att, sp, sb = _scaled_specs(d, alpha, beta)
    cfg = dict(d["cfg"])
    cfg.update(_cfg_overrides(z, alpha, beta))
    cfg.update(_layout_overrides(base_lay, alpha))
    return build_m4_env(0, int(ep), system=ratified_system(),
                        reward=RewardSpec(w_kill=0.5, enabled=True),
                        attacker=att, spawn=sp, standby=sb, extra_cfg=cfg)


def run_world(st, z, alpha, beta, n_steps=1200):
    """rollout 1 에피소드 → 스텝별 normalized 기록 (비교는 무차원 좌표에서만)."""
    env, base = st.env, _base_env(st.env)
    rho, tau = RHO * alpha, TAU * beta
    target = np.asarray(st.lay.target, float)
    env.reset(seed=0)
    recs = []
    for t in range(n_steps):
        lims, fin, att = base._states()
        p, v = base._p(att).copy(), base._v(att).copy()
        finv = np.asarray(fin, float).copy()
        s = dict(ep=0, t=int(t), p_att=p, v_att=v, fin=finv,
                 lim=[base._p(x).copy() for x in lims])
        eng = bool(_engaged(base, s))
        rec = dict(
            t=t, engaged=eng,
            pn=(p / rho), vn=(v * tau / rho),
            limn=np.array([l / rho for l in s["lim"]]),
            apexn=finv[0:3] / rho,
            dtgt=float(np.linalg.norm(target - p)) / rho)
        if eng:
            kw = base._vshot_kwargs(p, v, finv)
            union = V.build_reachable_union(
                p, v, tau=base.tau_deploy, a_att_max=base.a_att_max,
                n=2000, n_segments=4, n_dir=32, seed=int(t), **kw)
            r = V.eval_union_with_limiter_sets(union, [s["lim"]],
                                               float(base.kill_radius))[0]
            good = (np.asarray(union.caught, bool)
                    & np.asarray(union.turn_feasible, bool))
            rec.update(v0=float(r.v_shot_soft), n_wit=int(union.n_total),
                       mask=np.packbits(good).tobytes(),
                       boxed=bool(r.boxed_in))
        recs.append(rec)
        acts = scripted_role_actions(env, st.scn, st.lay, roles=ROLES,
                                     limiter_mode="hold", fire_mode="never",
                                     prev_clean=False, states=(lims, fin, att))
        _, _, te, tr, _ = env.step(acts)
        if any(te.values()) or any(tr.values()):
            break
    return recs


def compare(base_recs, sc_recs):
    n = min(len(base_recs), len(sc_recs))
    out = dict(n_steps_base=len(base_recs), n_steps_scaled=len(sc_recs),
               len_mismatch=(len(base_recs) != len(sc_recs)),
               max_state_dev=0.0, engaged_mismatch=0, n_engaged=0,
               max_dv=0.0, mask_mismatch=0, wit_mismatch=0, boxed_mismatch=0,
               worst=[])
    for i in range(n):
        a, b = base_recs[i], sc_recs[i]
        dev = max(float(np.abs(a[k] - b[k]).max()) for k in
                  ("pn", "vn", "limn", "apexn")) if a["limn"].shape == b["limn"].shape \
            else float("inf")
        dev = max(dev, abs(a["dtgt"] - b["dtgt"]))
        out["max_state_dev"] = max(out["max_state_dev"], dev)
        if a["engaged"] != b["engaged"]:
            out["engaged_mismatch"] += 1
            out["worst"].append(dict(t=a["t"], why="engaged"))
            continue
        if a["engaged"]:
            out["n_engaged"] += 1
            dv = abs(a["v0"] - b["v0"])
            out["max_dv"] = max(out["max_dv"], dv)
            if a["n_wit"] != b["n_wit"]:
                out["wit_mismatch"] += 1
            if a["mask"] != b["mask"]:
                out["mask_mismatch"] += 1
            if a["boxed"] != b["boxed"]:
                out["boxed_mismatch"] += 1
            if dv > TOL_V or a["mask"] != b["mask"]:
                out["worst"].append(dict(t=a["t"], dv=dv,
                                         mask_eq=(a["mask"] == b["mask"])))
    out["worst"] = out["worst"][:10]
    out["pass"] = (not out["len_mismatch"] and out["engaged_mismatch"] == 0
                   and out["max_dv"] <= TOL_V and out["mask_mismatch"] == 0
                   and out["wit_mismatch"] == 0 and out["boxed_mismatch"] == 0
                   and out["max_state_dev"] <= 1e-6)   # 상태는 진단 bar (1e-9 목표)
    return out


# ── T1-*.cert (docs/78 r2 addendum §C) ──────────────────────────────────────
CERT_EPISODES = range(10, 15)               # untouched (dev = 0..2)


def _cert_eval(p, v, lim, kw, *, tau, a_att, r_kill, seed):
    """한 (상태, 파라미터) 조합의 certificate — coarse_pilot 와 동일 호출."""
    union = V.build_reachable_union(p, v, tau=tau, a_att_max=a_att,
                                    n=2000, n_segments=4, n_dir=32,
                                    seed=int(seed), **kw)
    r = V.eval_union_with_limiter_sets(union, [lim], float(r_kill))[0]
    good = np.asarray(union.caught, bool) & np.asarray(union.turn_feasible, bool)
    return dict(v0=float(r.v_shot_soft), n_wit=int(union.n_total),
                mask=np.packbits(good).tobytes(), boxed=bool(r.boxed_in),
                G=int(good.sum()))


def _scale_kwargs(kw, alpha):
    """judge kwargs 의 길이 차원만 α배 (각도·단위벡터·judge 종류 불변)."""
    out = dict(kw)
    for k in ("net_apex", "net_center"):
        if k in out:
            out[k] = np.asarray(out[k], float) * alpha
    for k in ("range_min", "range_max", "net_radius"):
        if k in out:
            out[k] = float(out[k]) * alpha
    return out


def run_cert_tranche(z, episodes, base_lay, *, log=print):
    """base rollout 1회 → 상태 해석 변환 → 양 표현 certificate 비교 (attacker 재적분 없음)."""
    rows = {name: [] for name in TRANSFORMS}
    inv_dev = 0.0
    for ep in episodes:
        st = build_world(z, ep, 1.0, 1.0, base_lay)
        env, base = st.env, _base_env(st.env)
        tau0, a0, rk0 = float(base.tau_deploy), float(base.a_att_max), float(base.kill_radius)
        env.reset(seed=0)
        for t in range(1200):
            lims, fin, att = base._states()
            p, v = base._p(att).copy(), base._v(att).copy()
            finv = np.asarray(fin, float).copy()
            s = dict(p_att=p, v_att=v, fin=finv,
                     lim=[base._p(x).copy() for x in lims])
            if _engaged(base, s):
                kw0 = base._vshot_kwargs(p, v, finv)
                lim0 = np.asarray(s["lim"], float)
                A = _cert_eval(p, v, lim0, kw0, tau=tau0, a_att=a0,
                               r_kill=rk0, seed=t)
                for name, (al, be) in TRANSFORMS.items():
                    p2, v2 = p * al, v * (al / be)
                    a2, tau2 = a0 * (al / be ** 2), tau0 * be
                    B = _cert_eval(p2, v2, lim0 * al, _scale_kwargs(kw0, al),
                                   tau=tau2, a_att=a2, r_kill=rk0 * al, seed=t)
                    # 사전 assert: normalized invariants
                    rho0, rho2 = RHO, RHO * al
                    inv_dev = max(
                        inv_dev,
                        float(np.abs(p / rho0 - p2 / rho2).max()),
                        float(np.abs(v * tau0 / rho0 - v2 * tau2 / rho2).max()),
                        abs(a0 * tau0 ** 2 / rho0 - a2 * tau2 ** 2 / rho2))
                    rows[name].append(dict(
                        ep=int(ep), t=int(t), dv=abs(A["v0"] - B["v0"]),
                        mask_eq=(A["mask"] == B["mask"]),
                        wit_eq=(A["n_wit"] == B["n_wit"]),
                        boxed_eq=(A["boxed"] == B["boxed"]),
                        G=A["G"], v0=A["v0"]))
            acts = scripted_role_actions(env, st.scn, st.lay, roles=ROLES,
                                         limiter_mode="hold", fire_mode="never",
                                         prev_clean=False, states=(lims, fin, att))
            _, _, te, tr, _ = env.step(acts)
            if any(te.values()) or any(tr.values()):
                break
        log(f"  ep {ep}: cert states {len(rows['T1L'])}", flush=True)
    out = {}
    for name, rs in rows.items():
        out[name] = dict(
            n=len(rs), max_dv=max((r["dv"] for r in rs), default=0.0),
            mask_mismatch=sum(not r["mask_eq"] for r in rs),
            wit_mismatch=sum(not r["wit_eq"] for r in rs),
            boxed_mismatch=sum(not r["boxed_eq"] for r in rs),
            worst=[dict(ep=r["ep"], t=r["t"], dv=r["dv"], v0=r["v0"])
                   for r in sorted(rs, key=lambda r: -r["dv"])[:5]])
        out[name]["pass"] = (out[name]["n"] > 0
                             and out[name]["max_dv"] <= TOL_V
                             and out[name]["mask_mismatch"] == 0
                             and out[name]["wit_mismatch"] == 0
                             and out[name]["boxed_mismatch"] == 0)
    out["max_norm_invariant_dev"] = inv_dev
    out["invariants_ok"] = bool(inv_dev <= 1e-9)
    return out


# ── Tier 2 (docs/78 r3 addendum §C-3) ───────────────────────────────────────
import itertools

from shepherd.scripts import coarse_pilot as CP

TIER2_Z = [dict(chi=c, kappa=0.5, mu=0.4, N=4) for c in (0.4, 0.8, 1.6)]
TIER2_EPISODES = range(10, 15)
PERT = (0.8, 1.25)                          # r1 §2.1 교란 크기 승계
CAP_STATES = 120                            # z 당 상태 상한 (episode 순 결정론)
Q_KEYS = ("V0", "U_cheap", "L1", "LN")
BAR_MED, BAR_P95, MIN_INFORMATIVE = 0.02, 0.05, 50
GROUP_CLASS = {"alpha": "P", "lam": "P", "nu": "P", "sig_as": "P",
               "eta": "Z", "sig_sb": "Z"}   # sig_dt = G → 게이트 11


def _admissible_r(points, asset, r_nk):
    return all(float(np.linalg.norm(np.asarray(p) - asset)) > r_nk for p in points)


def _label_with_union(base, s, union, *, asset, lim0, v_lim, a_lim, dt,
                      r_kill, r_nk):
    """coarse_pilot.label_state 를 union 재사용 형태로 mirror (정의 동일 —
    base arm 에서 label_state 와 값 일치를 assert 로 봉인)."""
    from shepherd.scripts.cert_unblockable import unblockable_from_union
    T = float(s["t"]) * dt
    v0, _ = CP._g_eval(union, [s["lim"]], r_kill)[0]
    m = unblockable_from_union(union, asset=asset, r_nk=r_nk, r_kill=r_kill)
    probes = CP.probe_placement(base, s)
    singles = [[p] for p in probes] + [[l] for l in s["lim"]]
    singles = [ly for ly in singles if _admissible_r(ly, asset, r_nk)
               and CP._assignable(ly, lim0, T, v_lim, a_lim)]
    L1 = max((v for v, g in CP._g_eval(union, singles, r_kill) if g), default=0.0) \
        if singles else 0.0
    quads = [ly for ly in (probes, list(s["lim"]))
             if _admissible_r(ly, asset, r_nk)
             and CP._assignable(ly, lim0, T, v_lim, a_lim)]
    LN = max([L1] + [v for v, g in CP._g_eval(union, quads, r_kill) if g]) \
        if quads else L1
    lab = ("FREE" if v0 >= CP.THETA else
           "INF" if m["v_max"] < CP.THETA else
           "SINGLE" if L1 >= CP.THETA else "AMB")
    return dict(V0=v0, U_cheap=m["v_max"], L1=L1, LN=LN, label=lab)


def _union_of(base, p, v, kw, *, tau, a_att, seed):
    return V.build_reachable_union(p, v, tau=tau, a_att_max=a_att, n=2000,
                                   n_segments=4, n_dir=32, seed=int(seed), **kw)


def _tier2_state(base, s, *, asset, lim0, v_lim, a_lim, dt, r_kill, r_nk,
                 union_base, kw0, tau0, a0, checked):
    """한 상태의 base + 6군×2교란 Q. 반환 (base_Q, {(group,f): (Q, admissible)})."""
    kwargs0 = dict(asset=asset, lim0=lim0, v_lim=v_lim, a_lim=a_lim, dt=dt,
                   r_kill=r_kill, r_nk=r_nk)
    qb = _label_with_union(base, s, union_base, **kwargs0)
    if not checked[0]:                       # 정의 동일성 봉인 (1회)
        ref = CP.label_state(base, s, asset=asset, lim0=lim0, v_lim=v_lim,
                             a_lim=a_lim, dt=dt)
        assert all(abs(qb[k] - ref[k]) < 1e-12 for k in Q_KEYS), (qb, ref)
        checked[0] = True
    out = {}
    a_lo, a_hi = 8.0, 30.0                   # THREAT_BRACKET att_speed
    for g, f in itertools.product(GROUP_CLASS, PERT):
        adm = True
        if g in ("alpha", "lam"):            # judge 파라미터 → union 재생성
            old = (base.cone_half_angle, base.cone_range_max)
            if g == "alpha":
                base.cone_half_angle = old[0] * f
            else:
                base.cone_range_max = old[1] * f
            kw = base._vshot_kwargs(s["p_att"], s["v_att"], s["fin"])
            u = _union_of(base, s["p_att"], s["v_att"], kw, tau=tau0, a_att=a0,
                          seed=s["t"])
            q = _label_with_union(base, s, u, **kwargs0)
            base.cone_half_angle, base.cone_range_max = old
        elif g == "nu":                      # reachability 속도 한계
            q = _label_with_union(base, s, union_base,
                                  **dict(kwargs0, v_lim=v_lim * f))
        elif g == "sig_as":                  # R_NK admissibility
            q = _label_with_union(base, s, union_base,
                                  **dict(kwargs0, r_nk=r_nk * f))
        elif g == "eta":                     # 상태 좌표 ‖v‖
            v2 = s["v_att"] * f
            adm = (a_lo <= float(np.linalg.norm(v2)) <= a_hi)
            s2 = dict(s, v_att=v2)
            adm = adm and bool(_engaged(base, s2))
            kw = base._vshot_kwargs(s2["p_att"], v2, s2["fin"])
            u = _union_of(base, s2["p_att"], v2, kw, tau=tau0, a_att=a0, seed=s["t"])
            q = _label_with_union(base, s2, u, **kwargs0)
        else:                                # sig_sb — limiter 배치 반경
            c = np.mean(np.asarray(s["lim"], float), axis=0)
            lim2 = [c + f * (np.asarray(l, float) - c) for l in s["lim"]]
            adm = _admissible_r(lim2, asset, r_nk)
            s2 = dict(s, lim=lim2)
            q = _label_with_union(base, s2, union_base,
                                  **dict(kwargs0, lim0=[np.asarray(l) for l in lim2]))
        out[(g, f)] = (q, adm)
    return qb, out


# ── r4 (docs/78 r4 addendum §C-4) — shape + eta 만, 나머지 정의 불변 ─────────
R4_GROUPS = {"shape": "P", "eta": "Z"}
R4_CAP, R4_EPISODES = 300, range(10, 20)
V_MAX_STATE = 1.5 * ATT_SPEED0              # 등록 adversary_v_max (att_speed pin)


def _r4_state(base, s, *, asset, lim0, v_lim, a_lim, dt, r_kill, r_nk,
              union_base, tau0, a0, rho_eff0, checked):
    kwargs0 = dict(asset=asset, lim0=lim0, v_lim=v_lim, a_lim=a_lim, dt=dt,
                   r_kill=r_kill, r_nk=r_nk)
    qb = _label_with_union(base, s, union_base, **kwargs0)
    if not checked[0]:
        ref = CP.label_state(base, s, asset=asset, lim0=lim0, v_lim=v_lim,
                             a_lim=a_lim, dt=dt)
        assert all(abs(qb[k] - ref[k]) < 1e-12 for k in Q_KEYS), (qb, ref)
        checked[0] = True
    out = {}
    for f in PERT:
        # --- R4-A: cone shape, rho_eff 고정 ---
        old = (base.cone_half_angle, base.cone_range_max)
        base.cone_range_max = old[1] * f
        base.cone_half_angle = float(np.arctan(np.tan(old[0]) / f))
        rho_eff = base.cone_range_max * np.tan(base.cone_half_angle)
        assert abs(rho_eff - rho_eff0) <= 1e-12, (rho_eff, rho_eff0)   # 봉인 assert
        kw = base._vshot_kwargs(s["p_att"], s["v_att"], s["fin"])
        u = _union_of(base, s["p_att"], s["v_att"], kw, tau=tau0, a_att=a0,
                      seed=s["t"])
        out[("shape", f)] = (_label_with_union(base, s, u, **kwargs0), True)
        base.cone_half_angle, base.cone_range_max = old
        # --- R4-B: eta, 물리 상태공간 admissibility ---
        v2 = s["v_att"] * f
        nv = float(np.linalg.norm(v2))
        s2 = dict(s, v_att=v2)
        adm = (0.0 <= nv <= V_MAX_STATE) and bool(_engaged(base, s2))
        kw2 = base._vshot_kwargs(s2["p_att"], v2, s2["fin"])
        u2 = _union_of(base, s2["p_att"], v2, kw2, tau=tau0, a_att=a0, seed=s["t"])
        out[("eta", f)] = (_label_with_union(base, s2, u2, **kwargs0), adm)
    return qb, out


def run_tier2_cell(z, episodes, *, log=print, r4=False):
    groups = R4_GROUPS if r4 else GROUP_CLASS
    cap = R4_CAP if r4 else CAP_STATES
    base_lay = _resolved_base_layout(draw_threat_v3(0, 0, "train")["cfg"])
    acc = {(g, f): [] for g in groups for f in PERT}
    drop = {(g, f): 0 for g in groups for f in PERT}
    n_states, checked = 0, [False]
    for ep in episodes:
        if n_states >= cap:
            break
        st = build_world(z, ep, 1.0, 1.0, base_lay)
        env, base = st.env, _base_env(st.env)
        asset = np.asarray(st.lay.target, float)
        dt = float(base.dt) if hasattr(base, "dt") else 0.05
        v_lim = ATT_SPEED0
        a_lim = z["mu"] * z["chi"] * 2.0 * RHO / TAU ** 2
        tau0, a0, rk0 = float(base.tau_deploy), float(base.a_att_max), \
            float(base.kill_radius)
        env.reset(seed=0)
        lims, fin, att = base._states()
        lim0 = [base._p(x).copy() for x in lims]
        for t in range(1200):
            lims, fin, att = base._states()
            s = dict(ep=int(ep), t=int(t), p_att=base._p(att).copy(),
                     v_att=base._v(att).copy(),
                     fin=np.asarray(fin, float).copy(),
                     lim=[base._p(x).copy() for x in lims])
            if _engaged(base, s) and n_states < cap:
                kw0 = base._vshot_kwargs(s["p_att"], s["v_att"], s["fin"])
                ub = _union_of(base, s["p_att"], s["v_att"], kw0, tau=tau0,
                               a_att=a0, seed=t)
                common = dict(asset=asset, lim0=lim0, v_lim=v_lim, a_lim=a_lim,
                              dt=dt, r_kill=rk0, r_nk=CP.R_NK, union_base=ub,
                              tau0=tau0, a0=a0, checked=checked)
                if r4:
                    rho_eff0 = float(base.cone_range_max
                                     * np.tan(base.cone_half_angle))
                    qb, pert = _r4_state(base, s, rho_eff0=rho_eff0, **common)
                else:
                    qb, pert = _tier2_state(base, s, kw0=kw0, **common)
                n_states += 1
                for key, (q, adm) in pert.items():
                    if not adm:
                        drop[key] += 1
                        continue
                    inf = (0.0 < qb["V0"] < 1.0) or (0.0 < q["V0"] < 1.0)
                    acc[key].append(dict(
                        informative=inf,
                        d={k: abs(qb[k] - q[k]) for k in Q_KEYS},
                        sgn={k: float(np.sign(q[k] - qb[k])) for k in Q_KEYS},
                        flip=(qb["label"] != q["label"])))
            acts = scripted_role_actions(env, st.scn, st.lay, roles=ROLES,
                                         limiter_mode="hold", fire_mode="never",
                                         prev_clean=False, states=(lims, fin, att))
            _, _, te, tr, _ = env.step(acts)
            if any(te.values()) or any(tr.values()):
                break
        log(f"  ep {ep}: states {n_states}", flush=True)

    rows = []
    for g in groups:
        stat = {}
        for f in PERT:
            rs = [r for r in acc[(g, f)] if r["informative"]]
            if rs:
                med = {k: float(np.median([r["d"][k] for r in rs])) for k in Q_KEYS}
                p95 = {k: float(np.quantile([r["d"][k] for r in rs], 0.95))
                       for k in Q_KEYS}
            else:
                med = p95 = {k: 0.0 for k in Q_KEYS}
            stat[f] = dict(n_informative=len(rs), n_eval=len(acc[(g, f)]),
                           n_dropped=drop[(g, f)],
                           med={k: round(v, 5) for k, v in med.items()},
                           p95={k: round(v, 5) for k, v in p95.items()},
                           flip=sum(r["flip"] for r in rs),
                           mean_sign={k: round(float(np.mean(
                               [r["sgn"][k] for r in rs])), 3) for k in Q_KEYS}
                           if rs else {})
        n_inf = min(stat[f]["n_informative"] for f in PERT)
        if n_inf < MIN_INFORMATIVE:
            verdict = "INCONCLUSIVE"
        elif all(stat[f]["med"][k] <= BAR_MED and stat[f]["p95"][k] <= BAR_P95
                 for f in PERT for k in Q_KEYS):
            verdict = "PASS"
        else:
            verdict = "FAIL"
        rows.append(dict(group=g, cls=groups[g], verdict=verdict,
                         n_informative=n_inf, per_factor=stat))
    return dict(z=z, n_states=n_states, groups=rows)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Gate 10 iso-Pi Tier 1")
    ap.add_argument("--tier1", action="store_true")
    ap.add_argument("--tier1-cert", action="store_true",
                    help="docs/78 r2 addendum §C — 조건부 certificate similarity")
    ap.add_argument("--tier2", action="store_true",
                    help="docs/78 r3 addendum §C-3 — P/Z 부류 conditioning 교란")
    ap.add_argument("--r4", action="store_true",
                    help="docs/78 r4 addendum §C-4 — shape(rho_eff 고정) + eta(정정)")
    ap.add_argument("--chi", type=float, default=None, help="tier2 샤딩 (단일 chi)")
    ap.add_argument("--out", default="results/phase3/gate10_tier1.json")
    a = ap.parse_args(argv)
    if a.tier2:
        zs = [z for z in TIER2_Z if a.chi is None or abs(z["chi"] - a.chi) < 1e-9]
        eps = R4_EPISODES if a.r4 else TIER2_EPISODES
        cells = []
        for z in zs:
            print(f"tier2{'-r4' if a.r4 else ''} chi {z['chi']} kappa {z['kappa']} "
                  f"eps {eps.start}..{eps.stop - 1}:", flush=True)
            r = run_tier2_cell(z, eps, r4=a.r4)
            cells.append(r)
            for g in r["groups"]:
                f0 = g["per_factor"][PERT[0]]
                print(f"  {g['group']:>7} [{g['cls']}] {g['verdict']:>12} "
                      f"n_inf {g['n_informative']:>3} drop "
                      f"{f0['n_dropped']:>3} | med {f0['med']} flip {f0['flip']}",
                      flush=True)
        out = dict(contract_doc=("docs/78 r4 addendum §C-4 (shape+eta 수리)" if a.r4
                                 else "docs/78 r3 addendum §C-3 (Tier 2, P/Z 부류)"),
                   note=("6군 전체 단일 PASS/FAIL headline 금지 — 결론은 "
                         "'어느 좌표가 conditional viability map 을 충분히 "
                         "매개변수화하는가'. sig_dt(G)는 게이트 11 소관. "
                         "tranche = shared frozen validation (ep10..14); "
                         "no Tier-2 outcomes inspected before r3 freeze."),
                   bar=dict(median=BAR_MED, p95=BAR_P95,
                            min_informative=MIN_INFORMATIVE),
                   perturbations=list(PERT), episodes=list(TIER2_EPISODES),
                   cells=cells,
                   **stamp(artifact="phase3_gate10_tier2",
                           lattice_hash=_lattice_hash()))
        p = pathlib.Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"-> {p}")
        return
    if a.tier1_cert:
        d0 = draw_threat_v3(0, 0, "train")
        base_lay = _resolved_base_layout(d0["cfg"])
        cells, ok = [], True
        for z in Z_POINTS:
            print(f"cert chi {z['chi']} kappa {z['kappa']} eps "
                  f"{CERT_EPISODES.start}..{CERT_EPISODES.stop - 1}:", flush=True)
            r = run_cert_tranche(z, CERT_EPISODES, base_lay)
            r["z"] = z
            cells.append(r)
            ok &= bool(r["invariants_ok"] and r["T1L"]["pass"] and r["T1T"]["pass"])
            print(f"  -> inv_dev {r['max_norm_invariant_dev']:.2e} | "
                  f"T1L n {r['T1L']['n']} dv {r['T1L']['max_dv']:.2e} "
                  f"mask_mis {r['T1L']['mask_mismatch']} | "
                  f"T1T n {r['T1T']['n']} dv {r['T1T']['max_dv']:.2e} "
                  f"mask_mis {r['T1T']['mask_mismatch']}", flush=True)
        print("TIER1-CERT:", "PASS" if ok else "FAIL")
        out = dict(contract_doc="docs/78 r2 addendum §C (conditional certificate)",
                   note=("표기 규율: PASS 여도 'T1-T PASS' 금지 — 정본 = "
                         "'full-system T1-T failed (hidden k_f·tau); "
                         "conditional-certificate T1-T passed'."),
                   episodes=list(CERT_EPISODES), z_points=Z_POINTS,
                   cells=cells, tier1_cert_pass=bool(ok),
                   **stamp(artifact="phase3_gate10_tier1_cert",
                           lattice_hash=_lattice_hash()))
        p = pathlib.Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"-> {p}")
        return
    if not a.tier1:
        ap.error("현재 지원: --tier1 | --tier1-cert")

    d0 = draw_threat_v3(0, 0, "train")
    base_lay = _resolved_base_layout(d0["cfg"])

    results, all_pass = [], True
    for name, (alpha, beta) in TRANSFORMS.items():
        for z in Z_POINTS:
            for ep in EPISODES:
                stA = build_world(z, ep, 1.0, 1.0, base_lay)
                stB = build_world(z, ep, alpha, beta, base_lay)
                rA = run_world(stA, z, 1.0, 1.0)
                rB = run_world(stB, z, alpha, beta)
                c = compare(rA, rB)
                c.update(transform=name, z=z, ep=int(ep))
                results.append(c)
                all_pass &= c["pass"]
                print(f"{name} chi {z['chi']} ep {ep}: steps {c['n_steps_base']} "
                      f"eng {c['n_engaged']} | state_dev {c['max_state_dev']:.2e} "
                      f"dv {c['max_dv']:.2e} mask_mis {c['mask_mismatch']} "
                      f"eng_mis {c['engaged_mismatch']} -> "
                      f"{'PASS' if c['pass'] else 'FAIL'}", flush=True)

    print("TIER1:", "PASS" if all_pass else "FAIL")
    out = dict(contract_doc="docs/78 §1 (Tier 1) · 선언 = 모듈 docstring 1~5",
               transforms={k: list(v) for k, v in TRANSFORMS.items()},
               z_points=Z_POINTS, episodes=list(EPISODES),
               tol=dict(state=TOL_STATE, v=TOL_V),
               results=results, tier1_pass=bool(all_pass),
               **stamp(artifact="phase3_gate10_tier1",
                       lattice_hash=_lattice_hash()))
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"-> {p}")


if __name__ == "__main__":
    main()
