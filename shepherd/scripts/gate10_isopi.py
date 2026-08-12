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


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Gate 10 iso-Pi Tier 1")
    ap.add_argument("--tier1", action="store_true")
    ap.add_argument("--tier1-cert", action="store_true",
                    help="docs/78 r2 addendum §C — 조건부 certificate similarity")
    ap.add_argument("--out", default="results/phase3/gate10_tier1.json")
    a = ap.parse_args(argv)
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
