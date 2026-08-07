"""에피소드 궤적 덤프 + 시각화 뷰어 생성 (viz/trajectory_viewer.html).

수치 진단의 한계 보완 (Hyunjun 지시, 2026-08-07): 스폰/대기 위치·버그·
"단순 A2 를 net 으로 왜 못 잡나" 를 눈으로 검사한다. miss 7판 + NET_CAPTURE
3판을 같은 hold/clean·F-flags 조건으로 재생해 나란히 본다.

덤프는 _Driver 재생(결정론) 그대로 -- 별도 물리 복제 없음. torch-free.
"""
from __future__ import annotations

import argparse, json, pathlib
import numpy as np

from shepherd.scripts.recoverability_probe import (MISS_EPISODES, _Driver,
                                                   _build, _sysenv)

CAPTURE_EPISODES = (1, 4, 10)          # handoff_audit hold NET_CAPTURE 앞 3판
EPISODE_LEN = 80


def dump_episode(ep: int) -> dict:
    env, scn, lay = _build(ep)
    d = _Driver(env, scn, lay, ep)
    se = d.se
    inner = se.inner

    static = dict(
        episode=ep,
        target=list(map(float, lay.target)),
        target_radius=float(lay.target_radius),
        r_nk=float(se.spec.r_nk),
        kill_radius=float(env.kill_radius),
        net_radius=float(env.net_radius),
        tau_deploy=float(env.tau_deploy),
        dt=float(env.dt),
        ring_p0=[list(map(float, p)) for p in lay.limiter_p0],
        finisher_p0=list(map(float, lay.finisher_p0)),
        threat=dict(a_att=float(env.a_att_max), speed=float(env.v_nominal)),
    )

    steps = []
    fire_step = None
    net_center = None
    resolve_step = None
    n_events = 0
    for t in range(EPISODE_LEN):
        lims, fin, att = env._states()
        prev_state = inner.fsm.state.value
        fi = d.step()
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
        steps.append(dict(
            t=t,
            att=list(map(float, p_att)),
            att_v=list(map(float, env._v(att2))),
            lims=[list(map(float, env._p(s))) for s in lims2],
            retired=sorted(se.retired),
            fin=list(map(float, env._p(fin2))),
            fin_e=list(map(float, env._e(fin2))),
            fsm=inner.fsm.state.value,
            v_soft=round(float(fi.get("v_shot_soft", 0.0)), 3),
            v_worst=round(float(fi.get("v_shot_worst", 0.0)), 3),
            boxed=bool(fi.get("boxed_in", False)),
            clean=bool(fi.get("clean_net_threshold_crossed", False)),
            d_asset=round(float(np.linalg.norm(
                p_att - np.asarray(lay.target, float))), 3),
            d_lim_min=round(min(float(np.linalg.norm(p_att - env._p(s)))
                                for s in lims2), 3),
            events=new_ev,
        ))
        if d.done:
            break

    return dict(static=static, steps=steps, label=d.label,
                fire_step=fire_step, net_center=net_center,
                resolve_step=resolve_step, handoff_step=d.handoff_step,
                net_spent=bool(se.net_spent), group=None)


def main() -> None:
    ap = argparse.ArgumentParser(description="궤적 덤프 + 뷰어 생성")
    ap.add_argument("--template", default="viz/trajectory_viewer_template.html")
    ap.add_argument("--out-html", default="viz/trajectory_viewer.html")
    ap.add_argument("--out-json", default="results/viz_trajectories.json")
    a = ap.parse_args()

    episodes = []
    for ep in CAPTURE_EPISODES:
        e = dump_episode(ep)
        e["group"] = "CAPTURE"
        episodes.append(e)
        print(f"ep{ep:>3} {e['label']:>11} steps={len(e['steps'])}", flush=True)
    for ep in MISS_EPISODES:
        e = dump_episode(ep)
        e["group"] = "MISS"
        episodes.append(e)
        print(f"ep{ep:>3} {e['label']:>11} steps={len(e['steps'])}", flush=True)

    data = dict(note="hold/clean · F-flags (contact_resolver on, miss nonterminal) · Pk=1",
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
