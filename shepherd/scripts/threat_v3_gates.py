"""위협 계약 v3 게이트 P88 · P89 · P90 · P91a · P91b (docs/60 §5, 사전등록).

    python -m shepherd.scripts.threat_v3_gates --gate p88
    python -m shepherd.scripts.threat_v3_gates --gate p89
    python -m shepherd.scripts.threat_v3_gates --gate p90 --eps 0 100
    python -m shepherd.scripts.threat_v3_gates --gate p91a
    python -m shepherd.scripts.threat_v3_gates --gate p91b

판정식은 docs/60 §3.3·§4.3·§5 에 결과 전 고정. 전부 NOMINAL 에서 실행.

n_samples 축소 (2000 -> 64) 는 **fire_mode="never" 인 게이트에만** 적용한다:
발사가 없으면 v_shot 은 어떤 dynamics 소비자도 없어 (gate 미사용·bait_gain=0)
라벨·궤적이 sampler 해상도와 무관하다. P91a 의 v_shot 공변성 검사만 예외로
기본 해상도를 유지한다. torch-free.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib

import numpy as np

from dataclasses import replace

from shepherd.agents.attacker_ladder import _general_action, _route_accel
from shepherd.env_adv import attach_attacker
from shepherd.env_sys import RewardSpec, SystemSpec
from shepherd.m4_env import build_m4_env
from shepherd.scale_v2 import THREAT_V3_NOMINAL, V3_ARMS
from shepherd.scripts.mission_rollout import ROLES, run_episode, scripted_role_actions

__all__ = ["p88", "p89", "p90", "p91a", "p91b"]

RESULTS = pathlib.Path(__file__).resolve().parents[2] / "results"

# --- 사전등록 상수 (docs/60 §5) --------------------------------------------
P88_EPS = range(7)          # P84 동형 7판
P88_CHECK_D = 150.0         # m. checkpoint = d_asset 이 처음 이 값 이하가 되는 스텝
P88_T_POST = 12             # 처치 후 관측 스텝
P89_EPS = range(20)
P90_N = 100
P91A_EPS = (0, 1)
P91A_THETAS = (0.7, 2.4)    # rad (z-회전)
P91A_DYN_ATOL = 1e-6
P91A_VSHOT_TOL = 0.05       # 표본화 잡음 허용 (보고 + 선언 상한)
P91B_THETA = 0.5            # rad. spawn bearing ±
P91B_ATOL = 1e-6            # mirror 는 bit-exact 아님 (atan2 pi-반사 반올림 누적)
NS_FAST = {"viability.n_samples": 64}      # fire=never 전용 (헤더 정당화)

_EPS_N = 1e-12


def _unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if n > _EPS_N else v


def _stack(ep, *, attacker=None, extra=None, standby="arm", seed=0):
    arm = V3_ARMS["V3-FULL"]
    cfg = dict(arm["cfg"])
    if extra:
        cfg.update(extra)
    return build_m4_env(
        seed, ep,
        system=SystemSpec(enabled=True, contact_resolver=True,
                          miss_terminates=False, p_kill=1.0),
        reward=RewardSpec(w_kill=0.5, enabled=True),
        attacker=attacker or arm["attacker"], spawn=arm["spawn"],
        standby=(arm["standby"] if standby == "arm" else standby),
        extra_cfg=cfg)


def _base_env(env):
    """backend 를 실제로 소유한 안쪽 env (래퍼 사슬 .inner 를 걷는다)."""
    e = env
    while "backend" not in vars(e):
        e = vars(e)["inner"]
    return e


def _run(st, *, seed, steps, fire_mode="never", reset=True, stop=None,
         record=None, on_info=None):
    """hold/never|clean 구동. stop(env, states, t)=True 면 그 스텝 **이동 전** 정지.

    반환 = 실행한 스텝 수 (stop 시 그 시점 t). `on_info(fi, t)` 는 스텝 후 info.
    """
    env, scn, lay = st.env, st.scn, st.lay
    if reset:
        env.reset(seed=seed)
    prev_clean = False
    for t in range(steps):
        states = env._states()
        if stop is not None and stop(env, states, t):
            return t
        if record is not None:
            record(env, states, t)
        acts = scripted_role_actions(env, scn, lay, roles=ROLES,
                                     limiter_mode="hold", fire_mode=fire_mode,
                                     prev_clean=prev_clean, states=states)
        acts[env.adversary_id] = np.zeros(3, np.float32)
        _, _, term, trunc, info = env.step(acts)
        fi = info[env.finisher_id]
        if on_info is not None:
            on_info(fi, t)
        prev_clean = bool(fi.get("clean_net_threshold_crossed", False))
        if term[env.finisher_id] or trunc[env.finisher_id]:
            return t + 1
    return steps


def _teleport_limiters(base, positions):
    bk = base.backend
    for lid, p in zip(base.limiter_ids, positions):
        ag = bk.by_name(lid)
        ag.p = np.asarray(p, float).copy()
        ag.v = np.zeros(3)


def _att_pv(base):
    att = base._states()[2]
    return base._p(att).copy(), base._v(att).copy()


# ============================================================== P88 =======
def _basis(fwd):
    """_route_accel 과 동일한 횡단면 기저 (u, w)."""
    ref = np.array([0.0, 0.0, 1.0]) if abs(fwd[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = _unit(np.cross(fwd, ref))
    w = _unit(np.cross(fwd, u))
    return u, w


def _p88_configs(p_att, fwd, u):
    """처치 4종 + 대조 (사전등록). 전부 공격자 기준 이격 >= 2 m (contact 제외)."""
    return {
        # sense(30) 안 · 교전(0.75) 밖: +u 쪽 봉쇄 4기
        "side_pos": [p_att + fwd * (10.0 + 3.0 * i) + u * 4.0 for i in range(4)],
        "side_neg": [p_att + fwd * (10.0 + 3.0 * i) - u * 4.0 for i in range(4)],
        # sense 밖 (거리 ~40 > 30, 전방 성분 유지)
        "out_a": [p_att + fwd * (5.0 + 3.0 * i) + u * 40.0 for i in range(4)],
        "out_b": [p_att + fwd * (5.0 + 3.0 * i) - u * 40.0 for i in range(4)],
        # positive control: 1기 repel 반경(0.75) 안, 나머지 sense 밖
        "contact": [p_att + fwd * 0.6] + [p_att + fwd * (5.0 + 3.0 * i) + u * 40.0
                                          for i in range(1, 4)],
    }


def p88():
    """방향성 manipulation gate (docs/60 §3.3 a~e)."""
    rows = []
    for ep in P88_EPS:
        # 1) checkpoint 탐색: d_asset <= 150 이 되는 첫 스텝
        probe = _stack(ep, extra=NS_FAST)
        tgt = np.asarray(probe.lay.target, float)
        s0 = _run(probe, seed=ep, steps=2000,
                  stop=lambda e, s, t: float(np.linalg.norm(e._p(s[2]) - tgt))
                  <= P88_CHECK_D)

        def _arm(positions=None):
            st = _stack(ep, extra=NS_FAST)
            _run(st, seed=ep, steps=s0)                    # 결정론 재생
            base = _base_env(st.env)
            p0, v0 = _att_pv(base)
            if positions is not None:
                _teleport_limiters(base, positions)
            kw = base.backend._gather()                     # env 가 실제로 넘길 인자
            traj = []                                       # [0]=s0 이동 전 상태
            _run(st, seed=ep, steps=P88_T_POST, reset=False,
                 record=lambda e, s, t: traj.append(e._p(s[2]).copy()))
            return dict(p0=p0, v0=v0, kw=kw, traj=np.array(traj))

        ref0 = _arm(None)
        fwd = _unit(tgt - ref0["p0"])
        u, w = _basis(fwd)
        cfgs = _p88_configs(ref0["p0"], fwd, u)
        arms = {name: _arm(pos) for name, pos in cfgs.items()}

        # 첫 스텝 가속차 = 모듈 예측 (s0 상태 동일 -> route 항만 격리됨)
        spec = V3_ARMS["V3-FULL"]["attacker"]
        def a_pred(arm_):
            kw = dict(arm_["kw"])
            p, v = kw.pop("p_att"), kw.pop("v_att")
            return np.asarray(_general_action(spec, p, v, **kw)["a"], float)

        a_sp, a_sn, a_oa, a_ob, a_ct = (a_pred(arms[k]) for k in
                                        ("side_pos", "side_neg", "out_a", "out_b",
                                         "contact"))
        d_sp, d_sn = float((a_sp - a_oa) @ u), float((a_sn - a_oa) @ u)

        route_dir = _route_accel(
            spec, p_att=arms["side_pos"]["kw"]["p_att"],
            v_att=arms["side_pos"]["kw"]["v_att"], fwd=fwd,
            limiters=np.asarray(cfgs["side_pos"], float),
            kill_radius=arms["side_pos"]["kw"]["kill_radius"],
            repel_margin=arms["side_pos"]["kw"]["repel_margin"],
            a_lat_max=arms["side_pos"]["kw"]["a_att_max"],
            d_target=float(np.linalg.norm(tgt - arms["side_pos"]["kw"]["p_att"])))

        def dev(a, b):
            n = min(len(a["traj"]), len(b["traj"]))
            return float(np.max(np.linalg.norm(a["traj"][:n] - b["traj"][:n], axis=1)))

        checks = {
            # a) mirror: +u 봉쇄 -> -u 반응, -u 봉쇄 -> +u 반응 (부호 반전)
            "a_mirror_sign": bool(d_sp < 0.0 < d_sn),
            # b) direction: Δa(side_pos - out) 가 angular-gap 방향과 일치
            "b_direction": bool(float(_unit(a_sp - a_oa) @ _unit(route_dir)) > 0.7
                                if np.linalg.norm(route_dir) > 0 else False),
            # c) sense 안 처치 -> 궤적 발산
            "c_in_sense_diverges": bool(dev(arms["side_pos"], arms["out_a"]) > 0.0),
            # d) sense 밖 처치끼리 bit 동일
            "d_out_sense_identical": bool(dev(arms["out_a"], arms["out_b"]) == 0.0),
            # e) positive control: repel 안 1기 -> 1스텝 내 발산.
            #    contact resolver 가 즉시 종료시키면 (조기 절단) 그 자체가 발산이다
            "e_contact_diverges": bool(
                len(arms["contact"]["traj"]) != len(arms["out_a"]["traj"])
                or (len(arms["contact"]["traj"]) > 1
                    and float(np.linalg.norm(arms["contact"]["traj"][1]
                                             - arms["out_a"]["traj"][1])) > 0.0)),
        }
        rows.append(dict(episode=ep, s0=int(s0), d_sp=d_sp, d_sn=d_sn,
                         route_dir=[float(x) for x in route_dir],
                         dev_in=dev(arms["side_pos"], arms["out_a"]),
                         dev_out=dev(arms["out_a"], arms["out_b"]), **checks))
        print(f"ep{ep}: s0={s0} " + " ".join(
            f"{k.split('_')[0]}={'PASS' if rows[-1][k] else 'FAIL'}"
            for k in checks), flush=True)

    keys = ("a_mirror_sign", "b_direction", "c_in_sense_diverges",
            "d_out_sense_identical", "e_contact_diverges")
    verdict = {k: all(r[k] for r in rows) for k in keys}
    out = dict(contract="docs/60 §3.3 P88", n=len(rows), verdict=verdict,
               all_pass=all(verdict.values()), rows=rows)
    print("P88 verdict:", verdict, "-> ALL PASS" if out["all_pass"] else "-> FAIL")
    return out


# ============================================================== P89 =======
def p89():
    """능력 준수 + saturation audit (docs/60 §5 P89).

    채널: hold / fire=never (commit-후 dodge 는 미포함 -- v3 신규 조합
    jink+route+speed+homing 의 포화만 잰다. 격리 선언).
    """
    all_rows = []
    labels = {}
    for ep in P89_EPS:
        diags = []
        st = _stack(ep, extra=NS_FAST)
        base = _base_env(st.env)
        spec = V3_ARMS["V3-FULL"]["attacker"]

        def instrumented(p_att, v_att, **kw):
            d = {}
            out = _general_action(spec, p_att, v_att, diag=d, **kw)
            diags.append(d)
            return out
        attach_attacker(base, instrumented,
                        phase=float(getattr(base, "_attacker_phase", 0.0)))
        r = run_episode(st.env, st.scn, st.lay, seed=ep,
                        limiter_mode="hold", fire_mode="never")
        labels[r.label] = labels.get(r.label, 0) + 1
        a_max = float(base.adv_a_max)
        for d in diags:
            rq = np.asarray(d["route_req"], float)
            af = np.asarray(d["a_final"], float)
            nrq = float(np.linalg.norm(rq))
            d["route_realized"] = (float(af @ (rq / nrq)) if nrq > _EPS_N else 0.0)
            d["ratio_raw"] = d["a_raw"] / a_max
            d["speed_ratio"] = (d["speed"] / d["v_max"]) if d["v_max"] else None
        all_rows.append(dict(episode=ep, steps=len(diags),
                             clip_frac=float(np.mean([d["clipped"] for d in diags])),
                             max_ratio_raw=float(max(d["ratio_raw"] for d in diags)),
                             max_speed_ratio=float(max(d["speed_ratio"] for d in diags)),
                             route_req_mean=float(np.mean(
                                 [np.linalg.norm(d["route_req"]) for d in diags])),
                             route_realized_mean=float(np.mean(
                                 [d["route_realized"] for d in diags])),
                             sprint_clip_frac=float(np.mean(
                                 [d["clipped"] for d in diags
                                  if d["d_asset"] <= 60.0] or [0.0])),
                             sprint_route_realized=float(np.mean(
                                 [d["route_realized"] for d in diags
                                  if d["d_asset"] <= 60.0] or [0.0]))))
        print(f"ep{ep}: clip={all_rows[-1]['clip_frac']:.2f} "
              f"sprint_clip={all_rows[-1]['sprint_clip_frac']:.2f} "
              f"route {all_rows[-1]['route_req_mean']:.1f}->"
              f"{all_rows[-1]['route_realized_mean']:.1f} "
              f"maxv={all_rows[-1]['max_speed_ratio']:.3f}", flush=True)

    cap_ok = all(r["max_speed_ratio"] <= 1.0 + 1e-9 and r["max_ratio_raw"] >= 0.0
                 for r in all_rows)          # 속도 준수; |a|<=a_max 는 클립이 구조 보장
    agg = dict(
        clip_frac_mean=float(np.mean([r["clip_frac"] for r in all_rows])),
        clip_frac_max=float(max(r["clip_frac"] for r in all_rows)),
        sprint_clip_frac_mean=float(np.mean([r["sprint_clip_frac"] for r in all_rows])),
        route_authority_mean=float(np.mean(
            [r["route_realized_mean"] / max(r["route_req_mean"], 1e-9)
             for r in all_rows])),
        max_speed_ratio=float(max(r["max_speed_ratio"] for r in all_rows)))
    out = dict(contract="docs/60 §5 P89", n=len(all_rows), capability_ok=cap_ok,
               aggregate=agg, labels=labels, rows=all_rows,
               note=("판정: capability_ok 는 강제. 포화 '광범위' 여부의 임계는 "
                     "사전등록되지 않았다 -- 수치를 그대로 보고하고 route_gain "
                     "재비준 여부는 Hyunjun 판정 (docs/60 §8 r1)."))
    print(f"P89 capability_ok={cap_ok}  clip mean={agg['clip_frac_mean']:.3f} "
          f"max={agg['clip_frac_max']:.3f}  sprint_clip={agg['sprint_clip_frac_mean']:.3f} "
          f"route_authority={agg['route_authority_mean']:.3f} "
          f"max|v|/v_max={agg['max_speed_ratio']:.4f}")
    return out


# ============================================================== P90 =======
def p90(eps):
    """침투 능력 보존: defender 전원 제거 -> PENETRATED 100/100 (docs/60 §5)."""
    rows = []
    for ep in eps:
        st = _stack(ep, extra=NS_FAST, standby=None)
        base = _base_env(st.env)
        # defender 제거 = limiter 전기 10 km 밖 (sense/repel/route 전부 무효)
        far = [[10000.0, 10000.0 + 10.0 * i, 0.0] for i in range(len(base.limiter_ids))]
        for lid, p in zip(base.limiter_ids, far):
            ag = base.backend.by_name(lid)
            ag.p0 = list(p)
            ag.v0 = [0.0, 0.0, 0.0]
        base.layout.limiter_p0 = far
        r = run_episode(st.env, st.scn, st.lay, seed=ep,
                        limiter_mode="hold", fire_mode="never")
        rows.append(dict(episode=ep, label=r.label, steps=r.steps,
                         min_d=round(r.min_target_dist, 2)))
        print(f"ep{ep:>3}: {r.label:>11} steps={r.steps:>4} "
              f"min_d={r.min_target_dist:.2f}", flush=True)
    labs = {}
    for r in rows:
        labs[r["label"]] = labs.get(r["label"], 0) + 1
    ok = (labs.get("PENETRATED", 0) == len(rows))
    out = dict(contract="docs/60 §5 P90", n=len(rows), labels=labs, all_pass=ok,
               rows=rows,
               note=("TRUNCATED 발생 시 해석 금지 -- V6 전 horizon 재사전등록 "
                     "(episode_len 1000 은 이 gate 조건부 임시값)."))
    print(f"P90 labels={labs} -> {'PASS' if ok else 'FAIL'}")
    return out


# ============================================================= P91a =======
def _rotz(th):
    c, s = math.cos(th), math.sin(th)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _rotate_scene(st, R):
    """target 중심 z-회전을 전 장면(공격자·limiter·finisher, p0/v0/e0)에 적용."""
    base = _base_env(st.env)
    tgt = np.asarray(base.layout.target, float)
    for name in (*base.limiter_ids, base.finisher_id, base.adversary_id):
        ag = base.backend.by_name(name)
        ag.p0 = list(R @ (np.asarray(ag.p0, float) - tgt) + tgt)
        ag.v0 = list(R @ np.asarray(ag.v0, float))
        ag.e0 = list(R @ np.asarray(ag.e0, float))
    base.layout.limiter_p0 = [list(R @ (np.asarray(p, float) - tgt) + tgt)
                              for p in base.layout.limiter_p0]
    base.layout.adversary_p0 = list(R @ (np.asarray(base.layout.adversary_p0, float)
                                         - tgt) + tgt)
    base.layout.adversary_v0 = list(R @ np.asarray(base.layout.adversary_v0, float))


def _record_states(st, *, seed, steps, fire_mode):
    ps, vshot = [], []

    def rec(env, states, t):
        ps.append(np.array([env._p(s).copy()
                            for s in states[0] + [states[1], states[2]]]))

    n = _run(st, seed=seed, steps=steps, fire_mode=fire_mode, record=rec,
             on_info=lambda fi, t: vshot.append(float(fi.get("v_shot_soft", 0.0))))
    return np.array(ps), np.array(vshot), n


def p91a():
    """backend rotational covariance (docs/60 §4.3): finisher 포함 전체 z-회전.

    fire=never 이므로 dynamics 는 v_shot 과 독립 -> 엄격 공변성 (atol 1e-6).
    evaluator(v_shot) 공변성은 표본화 잡음 허용 0.05 (동일 world-frame 표본이
    회전 장면을 판정하므로 정확 동일이 아님 -- 기본 해상도 n=2000 유지).
    """
    rows = []
    T = 60
    for ep in P91A_EPS:
        ref = _stack(ep)
        p_ref, s_ref, n_ref = _record_states(ref, seed=ep, steps=T,
                                             fire_mode="never")
        for th in P91A_THETAS:
            rot = _stack(ep)
            R = _rotz(th)
            _rotate_scene(rot, R)
            p_rot, s_rot, n_rot = _record_states(rot, seed=ep, steps=T,
                                                 fire_mode="never")
            n = min(len(p_ref), len(p_rot))
            tgt = np.asarray(ref.lay.target, float)
            back = np.einsum("ij,tkj->tki", R.T, p_rot[:n] - tgt) + tgt
            dyn_dev = float(np.max(np.linalg.norm(back - p_ref[:n], axis=-1)))
            m = min(len(s_ref), len(s_rot))
            vshot_dev = float(np.max(np.abs(s_ref[:m] - s_rot[:m]))) if m else 0.0
            ok = bool(dyn_dev <= P91A_DYN_ATOL and n_ref == n_rot
                      and vshot_dev <= P91A_VSHOT_TOL)
            rows.append(dict(episode=ep, theta=th, steps=int(n),
                             dyn_dev=dyn_dev, vshot_dev=vshot_dev, ok=ok))
            print(f"ep{ep} th={th}: dyn_dev={dyn_dev:.2e} "
                  f"vshot_dev={vshot_dev:.3f} {'PASS' if ok else 'FAIL'}",
                  flush=True)
    ok = all(r["ok"] for r in rows)
    out = dict(contract="docs/60 §4.3 P91a", dyn_atol=P91A_DYN_ATOL,
               vshot_tol=P91A_VSHOT_TOL, all_pass=ok, rows=rows,
               note="실패 = hidden +x assumption -> 축 (iii) 동결 (배선 전 선언)")
    print(f"P91a -> {'PASS' if ok else 'FAIL'}")
    return out


# ============================================================== P94 =======
P94_EPS = range(50)
P94_DIV_M = 1.0             # m. 궤적 발산 최소 크기 (docs/61 §5 선언값)
P94_FRAC = 0.5              # green = 이 비율 이상의 판에서 발산 >= P94_DIV_M


def p94(eps=P94_EPS):
    """natural-state route paired ablation (docs/61 §5 P94 — 학습 전 필수).

    동일 seed 로 {route ON = nominal} vs {route OFF = route_gain 0} 를 자연
    발생 상태(hold/clean, teleport 개입 없음)에서 비교. green 전에는
    "학습 가능한 shepherding channel" 명칭 금지 (docs/62 §2).
    """
    spec_on = V3_ARMS["V3-FULL"]["attacker"]
    spec_off = replace(spec_on, route_gain=0.0, label="A2-v3-route-off")
    rows = []
    for ep in eps:
        arms = {}
        for tag, spec in (("on", spec_on), ("off", spec_off)):
            st = _stack(ep, attacker=spec)
            base = _base_env(st.env)
            diags = []

            def instr(p, v, _s=spec, _d=diags, **kw):
                d = {}
                out = _general_action(_s, p, v, diag=d, **kw)
                _d.append(d)
                return out

            attach_attacker(base, instr,
                            phase=float(getattr(base, "_attacker_phase", 0.0)))
            traj, vshot, last = [], [], {}
            fire = {"step": None}

            def on_info(fi, t, _f=fire, _v=vshot, _l=last):
                _v.append(float(fi.get("v_shot_soft", 0.0)))
                if fi.get("fire_event") and _f["step"] is None:
                    _f["step"] = t
                _l.clear(); _l.update(fi)

            _run(st, seed=ep, steps=2000, fire_mode="clean",
                 record=lambda e, s, t: traj.append(e._p(s[2]).copy()),
                 on_info=on_info)
            lab = ("HARD_KILL" if last.get("hard_kill") else
                   "CAPTURED" if last.get("captured") else
                   "PENETRATED" if last.get("penetrated") else "OTHER")
            arms[tag] = dict(traj=np.array(traj), vshot=np.array(vshot),
                             fire=fire["step"], label=lab,
                             route_frac=float(np.mean(
                                 [np.linalg.norm(d["route_req"]) > 0.0
                                  for d in diags])))
        n = min(len(arms["on"]["traj"]), len(arms["off"]["traj"]))
        dv = np.linalg.norm(arms["on"]["traj"][:n] - arms["off"]["traj"][:n],
                            axis=1)
        m = min(len(arms["on"]["vshot"]), len(arms["off"]["vshot"]))
        rows.append(dict(
            episode=ep,
            route_frac_on=round(arms["on"]["route_frac"], 4),
            first_div=(int(np.argmax(dv > 1e-6)) if (dv > 1e-6).any() else None),
            max_div=round(float(dv.max()), 3),
            steps_delta=int(len(arms["on"]["traj"]) - len(arms["off"]["traj"])),
            vshot_maxdiff=round(float(np.max(np.abs(
                arms["on"]["vshot"][:m] - arms["off"]["vshot"][:m]))), 3)
            if m else 0.0,
            fire_on=arms["on"]["fire"], fire_off=arms["off"]["fire"],
            label_on=arms["on"]["label"], label_off=arms["off"]["label"]))
        r = rows[-1]
        print(f"ep{ep:>3}: div_max={r['max_div']:>8} first@{r['first_div']} "
              f"route={r['route_frac_on']:.2f} "
              f"label {r['label_off']}->{r['label_on']} "
              f"fire {r['fire_off']}->{r['fire_on']}", flush=True)
    n_div = sum(1 for r in rows if r["max_div"] >= P94_DIV_M)
    n_label = sum(1 for r in rows if r["label_on"] != r["label_off"])
    n_fire = sum(1 for r in rows if r["fire_on"] != r["fire_off"])
    green = bool(n_div >= P94_FRAC * len(rows))
    out = dict(contract="docs/61 §5 P94", n=len(rows),
               n_div_ge_1m=n_div, n_label_changed=n_label,
               n_fire_changed=n_fire,
               route_frac_mean=float(np.mean([r["route_frac_on"] for r in rows])),
               green=green, rows=rows,
               note=("green 전 'shepherding channel 학습 가능' 명칭 금지. "
                     "red 여도 학습 금지 아님 -- 기전 서사 강등 후 재결정 "
                     "(docs/61 §5)."))
    print(f"P94: div>=1m {n_div}/{len(rows)} · label 변화 {n_label} · "
          f"fire 변화 {n_fire} -> {'GREEN' if green else 'RED'}")
    return out


# ============================================================= P91b =======
def p91b():
    """actual-v3 bearing sanity (docs/60 §4.3): finisher (2,0,0) 고정 ·
    standby phi0=pi/4 (y-대칭 집합) · spawn bearing ±theta -> 궤적 mirror.

    attacker 는 jink_amp=0 변형 (jink 위상 항은 mirror 비대칭이 정의상 존재 --
    v3 신규 채널 route/speed/homing 의 대칭만 검사. 격리 선언).
    """
    from shepherd.spawn_rand import SpawnDraw, apply_spawn
    spec = replace(THREAT_V3_NOMINAL, jink_amp=0.0, label="A2-v3-mirror")
    M = np.array([1.0, -1.0, 1.0])
    T = 900
    runs = {}
    for sgn, tag in ((+1.0, "pos"), (-1.0, "neg")):
        st = _stack(0, attacker=spec, extra=NS_FAST, standby=None)
        base = _base_env(st.env)
        tgt = np.asarray(base.layout.target, float)
        # standby phi0 = pi/4 강제 (y-mirror 대칭 집합) -- 게이트 전용 제어 배치
        ps = []
        for i, lid in enumerate(base.limiter_ids):
            ang = math.pi / 4.0 + 2.0 * math.pi * i / len(base.limiter_ids)
            p = tgt + 12.0 * np.array([math.cos(ang), math.sin(ang), 0.0])
            ag = base.backend.by_name(lid)
            ag.p0 = list(map(float, p))
            ag.v0 = [0.0, 0.0, 0.0]
            ps.append(list(map(float, p)))
        base.layout.limiter_p0 = ps
        # spawn bearing ±theta, r=300, r_lat 오프셋 없음 (순수 bearing 대조)
        th = sgn * P91B_THETA
        p0 = tgt + 300.0 * np.array([math.cos(th), math.sin(th), 0.0])
        dir0 = _unit(tgt - p0)
        speed = float(base.sc.adversary.speed)
        apply_spawn(base, SpawnDraw(tuple(p0), tuple(speed * dir0), tuple(dir0), ()))
        traj = []
        _run(st, seed=0, steps=T,
             record=lambda e, s, t: traj.append(e._p(s[2]).copy()))
        runs[tag] = np.array(traj)
    n = min(len(runs["pos"]), len(runs["neg"]))
    dev = float(np.max(np.linalg.norm(runs["pos"][:n] - M * runs["neg"][:n], axis=1)))
    ok = bool(dev <= P91B_ATOL and len(runs["pos"]) == len(runs["neg"]))
    out = dict(contract="docs/60 §4.3 P91b", theta=P91B_THETA, atol=P91B_ATOL,
               steps=int(n), mirror_dev=dev, all_pass=ok,
               note=("viability 의 bearing 의존은 실패가 아니라 기록 대상 "
                     "(finisher 방위 추종 실측 자료) -- V6/뷰어에서 관측."))
    print(f"P91b mirror_dev={dev:.2e} steps={n} -> {'PASS' if ok else 'FAIL'}")
    return out


# ============================================================== main ======
def main():
    ap = argparse.ArgumentParser(description="threat v3 gates (docs/60 §5)")
    ap.add_argument("--gate", required=True,
                    choices=["p88", "p89", "p90", "p91a", "p91b", "p94"])
    ap.add_argument("--eps", type=int, nargs=2, default=[0, P90_N],
                    metavar=("A", "B"), help="p90 샤딩 range [A, B)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    fn = {"p88": p88, "p89": p89, "p91a": p91a, "p91b": p91b,
          "p94": p94}.get(a.gate)
    out = fn() if fn else p90(range(a.eps[0], a.eps[1]))
    path = pathlib.Path(a.out) if a.out else (
        RESULTS / (f"threat_v3_{a.gate}.json" if a.gate != "p90"
                   else f"threat_v3_p90_{a.eps[0]}_{a.eps[1]}.json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"-> {path}")


if __name__ == "__main__":
    main()
