"""에피소드 궤적 덤프 + 시각화 뷰어 생성 (viz/trajectory_viewer.html).

수치 진단의 한계 보완 (Hyunjun 지시, 2026-08-07): 스폰/대기 위치·버그·
"단순 A2 를 net 으로 왜 못 잡나" 를 눈으로 검사한다. miss 7판 + NET_CAPTURE
3판을 같은 hold/clean·F-flags 조건으로 재생해 나란히 본다.

덤프는 _Driver 재생(결정론) 그대로 -- 별도 물리 복제 없음. torch-free.
"""
from __future__ import annotations

import argparse, json, pathlib
import numpy as np

from shepherd.env_sys import commit_margin as _commit_margin
from shepherd.scripts.recoverability_probe import (MISS_EPISODES, _Driver,
                                                   _build, _sysenv)

CAPTURE_EPISODES = (1, 4, 10)          # handoff_audit hold NET_CAPTURE 앞 3판


def _build_v2(ep: int):
    from shepherd.agents.attacker_ladder import AttackerSpec
    from shepherd.env_sys import RewardSpec, SystemSpec
    from shepherd.m4_env import build_m4_env
    from shepherd.scale_v2 import SCALE_V2_CFG, SCALE_V2_SPAWN
    st = build_m4_env(
        0, ep,
        system=SystemSpec(enabled=True, contact_resolver=True,
                          miss_terminates=False, p_kill=1.0),
        reward=RewardSpec(w_kill=0.5, enabled=True),
        attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0),
        spawn=SCALE_V2_SPAWN, extra_cfg=dict(SCALE_V2_CFG))
    return st.env, st.scn, st.lay


def _build_v3(ep: int):
    """위협 계약 v3 NOMINAL FULL arm (docs/60 §7 · V3_ARMS['V3-FULL'])."""
    from shepherd.env_sys import RewardSpec, SystemSpec
    from shepherd.m4_env import build_m4_env
    from shepherd.scale_v2 import V3_ARMS
    arm = V3_ARMS["V3-FULL"]
    st = build_m4_env(
        0, ep,
        system=SystemSpec(enabled=True, contact_resolver=True,
                          miss_terminates=False, p_kill=1.0),
        reward=RewardSpec(w_kill=0.5, enabled=True),
        attacker=arm["attacker"], spawn=arm["spawn"], standby=arm["standby"],
        extra_cfg=dict(arm["cfg"]))
    return st.env, st.scn, st.lay


def _build_t1(ep: int):
    """★ curve_sweep._default_kw 와 **동일한 세계** (E2-A/E2-B 캠페인 재생용).

    ratified_system + T1 (route_gain 0.5 / sense_range 30.0) + 기본 SpawnSpec.
    이 빌더로 덤프해야 results/curve_intercept_reactive.json 의 에피소드 라벨과
    1:1 대응한다.
    """
    from shepherd.agents.attacker_ladder import AttackerSpec
    from shepherd.env_sys import RewardSpec, ratified_system
    from shepherd.m4_env import build_m4_env
    from shepherd.spawn_rand import SpawnSpec
    st = build_m4_env(
        0, ep,
        system=ratified_system(),
        reward=RewardSpec(w_kill=0.5, enabled=True),
        attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0,
                              route_gain=0.5, sense_range=30.0),
        spawn=SpawnSpec())
    return st.env, st.scn, st.lay


def dump_episode(ep: int, *, v2: bool = False, v3: bool = False,
                 t1: bool = False, limiter_mode: str = "hold",
                 commit: bool = False, lead=None, lead_delta=None) -> dict:
    # lead_delta: E4-1c uniform lead (docs/83 §27). 네 limiter 에 동일 delta.
    #   frozen strong pursuit baseline = 0.125 s. limiter_mode="intercept" 에서만 의미.
    # lead: 리드타임 진단(docs/83 §17) 재생 -- lead_time_diag._build 와 동일 세계
    if lead is not None:
        from shepherd.scripts.lead_time_diag import _build as _build_lead
        st = _build_lead(ep, float(lead))
        env, scn, lay = st.env, st.scn, st.lay
    else:
        env, scn, lay = (_build_t1(ep) if t1 else _build_v3(ep) if v3
                         else _build_v2(ep) if v2 else _build(ep))
    d = _Driver(env, scn, lay, ep)
    se = d.se
    inner = se.inner

    static = dict(
        episode=ep,
        target=list(map(float, lay.target)),
        target_radius=float(lay.target_radius),
        r_nk=float(se.spec.r_nk),
        kill_radius=float(env.kill_radius),
        # --- R1 하드킬/접촉 기하 (2026-08-13 추가) -------------------------
        # 반경 3종은 SystemSpec 에서 키가 분리돼 있고 기본값이 전부 kill_radius
        # 로 폴백한다 (env_sys.py:99-107). 값이 같아도 **의미가 다르므로**
        # 뷰어에서 따로 그린다.
        r_commit=float(se.spec.r_commit if se.spec.r_commit is not None
                       else env.kill_radius),
        r_contact=float(se.spec.r_contact if se.spec.r_contact is not None
                        else env.kill_radius),
        tau_kill=float(se.spec.tau_kill),
        n_kill=int(max(round(se.spec.tau_kill / env.dt), 1)),
        p_kill=float(se.spec.p_kill),
        # 커밋 기하 판정 반경 -- env_sys.commit_margin 이 단일 정의원 (R-001).
        # a_lim < a_att 면 **음수**가 될 수 있다 -- 그때는 커밋해도 기하 미충족.
        commit_margin=float(_commit_margin(
            se.spec, kill_radius=env.kill_radius,
            a_lim_max=se.a_lim_max, a_att_max=env.a_att_max)),
        net_radius=float(env.net_radius),
        tau_deploy=float(env.tau_deploy),
        cone_half_angle=float(env.cone_half_angle),
        cone_range=float(env.cone_range_max),
        dt=float(env.dt),
        ring_p0=[list(map(float, p)) for p in lay.limiter_p0],
        finisher_p0=list(map(float, lay.finisher_p0)),
        threat=dict(a_att=float(env.a_att_max), speed=float(env.v_nominal)),
        limiter_mode=limiter_mode, baseline_commit=bool(commit),
        lead_delta=None if lead_delta is None else float(lead_delta),
    )

    steps = []
    # 소진 limiter 는 env_sys §5 에서 [0,0,60] 으로 **주차**된다. post-step 좌표를
    # 그대로 적으면 접촉이 일어난 바로 그 스텝이 63 m 로 기록돼 결정적 프레임이
    # 사라진다 (2026-08-14 발견). 주차된 limiter 는 **마지막 실좌표**로 고정해
    # 그린다. 측정이 아니라 표기 교정이며, 라벨/확률에는 영향이 없다.
    last_real = [None] * len(env.limiter_ids)
    fire_step = None
    net_center = None
    resolve_step = None
    hard_kill_step = None          # 하드킬이 성립한 스텝 (2026-08-13)
    terminal_step = None           # 에피소드가 실제로 끝난 스텝
    n_events = 0
    for t in range(int(lay.episode_len)):
        lims, fin, att = env._states()
        prev_state = inner.fsm.state.value
        fi = d.step(limiter_mode=limiter_mode, baseline_commit=commit,
                    limiter_kw=(None if lead_delta is None else
                                {"lead_deltas": [float(lead_delta)] * len(env.limiter_ids)}))
        lims2, fin2, att2 = env._states()
        if fi.get("fire_event") and fire_step is None:
            fire_step = t
            cm = inner.fsm.commit
            if cm is not None:
                net_center = list(map(float, cm.net_center))
        if (prev_state in ("DEPLOYING", "LOCKED")
                and inner.fsm.state.value in ("SPENT", "LOADED")
                and resolve_step is None):
            resolve_step = t
        new_ev = [dict(limiter=r.limiter_index, outcome=r.outcome,
                       d=round(r.d_nom, 3), source=r.source)
                  for r in se.commits[n_events:]]
        n_events = len(se.commits)
        p_att = env._p(att2)
        lim_pos = []
        for i, st_i in enumerate(lims2):
            q = env._p(st_i)
            if i in se.retired and last_real[i] is not None:
                q = last_real[i]                      # 주차 좌표 대신 마지막 실좌표
            else:
                last_real[i] = np.asarray(q, float).copy()
            lim_pos.append(list(map(float, q)))
        steps.append(dict(
            t=t,
            att=list(map(float, p_att)),
            att_v=list(map(float, env._v(att2))),
            lims=lim_pos,
            att_pre=list(map(float, env._p(att))),
            retired=sorted(se.retired),
            fin=list(map(float, env._p(fin2))),
            fin_e=list(map(float, env._e(fin2))),
            fsm=inner.fsm.state.value,
            # limiter 상태 3분 (2026-08-13): 미커밋 / 커밋했으나 미해소 / 소모완료.
            # `retired` 만으로는 "지금 날아가는 중" 을 볼 수 없었다.
            committed=sorted(se.pending.keys()),
            spent=sorted(se.retired),
            v_soft=round(float(fi.get("v_shot_soft", 0.0)), 3),
            v_worst=round(float(fi.get("v_shot_worst", 0.0)), 3),
            boxed=bool(fi.get("boxed_in", False)),
            clean=bool(fi.get("clean_net_threshold_crossed", False)),
            d_asset=round(float(np.linalg.norm(
                p_att - np.asarray(lay.target, float))), 3),
            # ★ R-014 -- 두 양을 **이름으로 구분**한다 (감사 Session 2 X-007).
            #   d_lim_min_display : 화면 좌표(주차 보정 포함) 위의 **끝점** 거리.
            #     표기용이며 R4 가 superseded 로 선언한 계열이다. 주차된 limiter 는
            #     마지막 실좌표에 고정돼 있으므로 은퇴 후에도 값이 계속 움직인다.
            #   d_swept_min : `_Driver.d_min` 의 누적 최소 = **R4 권위 측정**
            #     (swept 거리 · retired_pre 스냅샷 기준). 해소기와 같은 술어다.
            #   종전에는 앞의 것만 "최근접 limiter" 로 실려 권위값처럼 읽혔다.
            d_lim_min_display=round(min(
                float(np.linalg.norm(p_att - np.asarray(q, float)))
                for q in lim_pos), 3),
            d_swept_min=(None if not np.isfinite(float(np.min(d.d_min)))
                         else round(float(np.min(d.d_min)), 3)),
            events=new_ev,
        ))
        if hard_kill_step is None and bool(fi.get("hard_kill", False)):
            hard_kill_step = t
        if d.done:
            terminal_step = t
            break

    # 커밋 원장 (2026-08-13): 커밋 스텝과 해소 스텝을 **따로** 싣는다.
    # 기존 steps[].events 는 record 가 생긴 스텝에 outcome 을 읽었는데,
    # outcome 은 n_kill 틱 뒤 해소 때 채워지므로 그 시점엔 비어 있었다.
    commits = [dict(limiter=r.limiter_index, commit_step=r.commit_step,
                    resolve_step=r.resolve_step, outcome=r.outcome,
                    d_nom=round(float(r.d_nom), 3),
                    margin=round(float(r.margin), 3),
                    geometric_ok=bool(r.geometric_ok), source=r.source)
               for r in se.commits]

    # ★ R-014: 에피소드 수준 권위 기록 (docs/83 §29 R4 측정계약).
    #   호출부가 자체 거리 루프를 만들지 않도록 driver 값을 그대로 싣는다.
    proximity = dict(
        d_min=[None if not np.isfinite(float(x)) else round(float(x), 4)
               for x in d.d_min],
        t_min=[int(x) for x in d.t_min],
        n_unmeasured=int(d.n_unmeasured),
        contract="R4 (swept · retired_pre 스냅샷)")

    return dict(static=static, steps=steps, label=d.label,
                fire_step=fire_step, net_center=net_center,
                resolve_step=resolve_step, handoff_step=d.handoff_step,
                hard_kill_step=hard_kill_step, terminal_step=terminal_step,
                commits=commits, proximity=proximity,
                net_spent=bool(se.net_spent), group=None)


def main() -> None:
    ap = argparse.ArgumentParser(description="궤적 덤프 + 뷰어 생성")
    ap.add_argument("--template", default="viz/trajectory_viewer_template.html")
    ap.add_argument("--out-html", default="viz/trajectory_viewer.html")
    ap.add_argument("--out-json", default="results/viz_trajectories.json")
    ap.add_argument("--v2", action="store_true", help="스케일 v2 (docs/59)")
    ap.add_argument("--v3", action="store_true",
                    help="위협 v3 NOMINAL FULL (docs/60 -- standby·방위 스폰)")
    ap.add_argument("--lead", type=float, default=None,
                    help="리드타임 진단 재생 (start_x 값). docs/83 §17 과 동일 세계")
    ap.add_argument("--lead-delta", type=float, default=None,
                    help="E4-1c uniform lead delta (docs/83 §27). "
                         "frozen strong pursuit baseline = 0.125")
    ap.add_argument("--t1", action="store_true",
                    help="curve_sweep 과 동일 세계 (ratified + T1 route 0.5/sense 30)")
    ap.add_argument("--limiter-mode", default="hold",
                    help="hold | intercept | ring | arc ...")
    ap.add_argument("--commit", action="store_true",
                    help="limiter 하드킬 커밋 허용 (baseline_commit). "
                         "끄면 _zero_commit 이 걸려 커밋/SPENT 가 안 보인다")
    ap.add_argument("--eps", type=int, nargs="*", default=None,
                    help="에피소드 목록 override (그룹 = 실측 라벨)")
    ap.add_argument("--from-json", default=None,
                    help="재시뮬 없이 기존 JSON 에서 HTML 만 재생성 (서버 분업용)")
    a = ap.parse_args()

    if a.from_json:
        data = json.loads(pathlib.Path(a.from_json).read_text(encoding="utf-8"))
        tpl = pathlib.Path(a.template).read_text(encoding="utf-8")
        html = tpl.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
        pathlib.Path(a.out_html).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.out_html).write_text(html, encoding="utf-8")
        print(f"-> {a.out_html} (from {a.from_json})")
        return

    episodes = []
    if a.eps is not None:
        for ep in a.eps:
            e = dump_episode(ep, v2=a.v2, v3=a.v3, t1=a.t1, lead=a.lead,
                             limiter_mode=a.limiter_mode, commit=a.commit,
                             lead_delta=a.lead_delta)
            e["group"] = e["label"]
            episodes.append(e)
            print(f"ep{ep:>3} {e['label']:>11} steps={len(e['steps'])}", flush=True)
    else:
        for ep in CAPTURE_EPISODES:
            e = dump_episode(ep, v2=a.v2, v3=a.v3, t1=a.t1, lead=a.lead,
                             limiter_mode=a.limiter_mode, commit=a.commit,
                             lead_delta=a.lead_delta)
            e["group"] = "CAPTURE"
            episodes.append(e)
            print(f"ep{ep:>3} {e['label']:>11} steps={len(e['steps'])}", flush=True)
        for ep in MISS_EPISODES:
            e = dump_episode(ep, v2=a.v2, v3=a.v3, t1=a.t1, lead=a.lead,
                             limiter_mode=a.limiter_mode, commit=a.commit,
                             lead_delta=a.lead_delta)
            e["group"] = "MISS"
            episodes.append(e)
            print(f"ep{ep:>3} {e['label']:>11} steps={len(e['steps'])}", flush=True)

    data = dict(note=("threat v3 NOMINAL FULL (docs/60) · " if a.v3
                      else "scale v2 (docs/59) · " if a.v2 else "legacy · ")
                     + "hold/clean · F-flags · Pk=1",
                episodes=episodes)
    pathlib.Path(a.out_json).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out_json).write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8")

    tpl = pathlib.Path(a.template).read_text(encoding="utf-8")
    html = tpl.replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
    pathlib.Path(a.out_html).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out_html).write_text(html, encoding="utf-8")
    print(f"-> {a.out_json}\n-> {a.out_html}")


if __name__ == "__main__":
    main()
