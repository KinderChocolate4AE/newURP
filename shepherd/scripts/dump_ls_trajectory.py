"""학습 정책(LS) 궤적 덤프 — viz-first 진단 (기존 뷰어 스키마 호환).

LS 최종 0.163 (FREE 0.36 / SHAPING 0) 의 "왜" 를 수치 전에 눈으로 본다:
limiter 가 standby 에서 실제로 무엇을 하나 — 재배치인가 제자리 진동인가,
arc/hold 와 질적으로 다른가.

    # 서버 (torch): LS 정책 팔
    python -m shepherd.scripts.dump_ls_trajectory --arm ls \\
        --ckpt results/m4_v3_train_LS/seed0 --out results/viz_ls.json
    # 로컬 (torch-free): 비교 팔 (같은 eval 에피소드·같은 draw)
    python -m shepherd.scripts.dump_ls_trajectory --arm arc --out results/viz_arc.json
    python -m shepherd.scripts.dump_ls_trajectory --arm hold --out results/viz_hold.json
    # 병합 + HTML (기존 템플릿 재사용)
    python -m shepherd.scripts.dump_ls_trajectory --merge \\
        results/viz_ls.json results/viz_arc.json results/viz_hold.json \\
        --out results/viz_ls_compare.json
    python -m shepherd.scripts.dump_trajectory --from-json results/viz_ls_compare.json \\
        --out-html viz/trajectory_viewer_ls.html

세계 = final eval 과 동일 namespace (eval_seed0=500000, threat_layer=train,
ratified 계약). ★ caveat: LS 팔은 에피소드별 재시드 표본추출이라 final eval
과 RNG 위상이 달라 **라벨이 판별로 재현되지 않을 수 있다** — 이 덤프는 정성
진단 전용이며 어떤 판정에도 쓰지 않는다.
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np

from shepherd.env_sys import RewardSpec, ratified_system
from shepherd.m4_env import build_m4_env
from shepherd.scripts.mission_rollout import ROLES, scripted_role_actions

EVAL_SEED0 = 500_000                 # train_m4: seed0=0 -> eval_seed0
ARC_KW = dict(r_d=9.0, dphi=0.5235987755982988)   # docs/63 §7 SELECTED c5


def _sysenv(env):
    e = env
    while not hasattr(e, "commits"):
        e = e.inner
    return e


def _world_kw():
    return dict(system=ratified_system(),
                reward=RewardSpec(w_kill=0.5, enabled=True),
                threat_layer="train")


def _record_episode(ep: int, actor, label_of) -> dict:
    """dump_trajectory.dump_episode 와 동일 스키마로 한 판 기록.

    `actor(env, scn, lay, states, obs, flags, prev_clean) -> acts` 가 행동을
    낸다 (LS = 정책+scripted finisher / arc·hold = 전 역할 scripted).
    """
    st = build_m4_env(EVAL_SEED0, ep, **_world_kw())
    env, scn, lay = st.env, st.scn, st.lay
    se = _sysenv(env)
    obs_d, _ = env.reset(seed=EVAL_SEED0 + ep)
    obs = obs_d[env.limiter_ids[0]]
    flags: dict = {}
    prev_clean = False

    static = dict(
        episode=ep,
        target=list(map(float, lay.target)),
        target_radius=float(lay.target_radius),
        r_nk=float(se.spec.r_nk),
        kill_radius=float(env.kill_radius),
        net_radius=float(env.net_radius),
        tau_deploy=float(env.tau_deploy),
        cone_half_angle=float(env.cone_half_angle),
        cone_range=float(env.cone_range_max),
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
    contact = False
    last_fi: dict = {}
    for t in range(int(lay.episode_len)):
        states = env._states()
        prev_state = env.fsm.state.value
        acts = actor(env, scn, lay, states, obs, flags, prev_clean)
        acts[env.adversary_id] = np.zeros(3, np.float32)
        obs_next, _, term, trunc, info = env.step(acts)
        fi = info[env.finisher_id]
        last_fi = fi
        obs = obs_next[env.limiter_ids[0]]
        flags = fi
        prev_clean = bool(fi.get("clean_net_threshold_crossed", False))

        lims2, fin2, att2 = env._states()
        p_att = env._p(att2)
        contact = contact or any(
            float(np.linalg.norm(p_att - env._p(s))) <= env.kill_radius
            for s in lims2)
        if fi.get("fire_event") and fire_step is None:
            fire_step = t
            cm = env.fsm.commit
            if cm is not None:
                net_center = list(map(float, cm.net_center))
        if (prev_state in ("DEPLOYING", "LOCKED")
                and env.fsm.state.value in ("SPENT", "LOADED")
                and resolve_step is None):
            resolve_step = t
        new_ev = [dict(limiter=r.limiter_index, outcome=r.outcome,
                       d=round(r.d_nom, 3), source=r.source)
                  for r in se.commits[n_events:]]
        n_events = len(se.commits)
        steps.append(dict(
            t=t,
            att=list(map(float, p_att)),
            att_v=list(map(float, env._v(att2))),
            lims=[list(map(float, env._p(s))) for s in lims2],
            retired=sorted(se.retired),
            fin=list(map(float, env._p(fin2))),
            fin_e=list(map(float, env._e(fin2))),
            fsm=env.fsm.state.value,
            v_soft=round(float(fi.get("v_shot_soft", 0.0)), 3),
            v_worst=round(float(fi.get("v_shot_worst", 0.0)), 3),
            boxed=bool(fi.get("boxed_in", False)),
            clean=prev_clean,
            d_asset=round(float(np.linalg.norm(
                p_att - np.asarray(lay.target, float))), 3),
            d_lim_min=round(min(float(np.linalg.norm(p_att - env._p(s)))
                                for s in lims2), 3),
            events=new_ev,
        ))
        if (term and term.get(env.finisher_id)) or \
                (trunc and trunc.get(env.finisher_id)):
            break

    label = label_of(last_fi, contact)
    return dict(static=static, steps=steps, label=label,
                fire_step=fire_step, net_center=net_center,
                resolve_step=resolve_step,
                handoff_step=None, net_spent=bool(se.net_spent), group=None)


def _label_of(fi: dict, contact: bool) -> str:
    if fi.get("hard_kill"):
        return "HARD_KILL"
    if fi.get("captured"):
        return "CAPTURE_WITH_CONTACT" if contact else "NET_CAPTURE"
    if fi.get("penetrated"):
        return "PENETRATED"
    return "TRUNCATED"


def _scripted_actor(mode: str):
    kw = ARC_KW if mode == "arc" else None

    def actor(env, scn, lay, states, obs, flags, prev_clean):
        return scripted_role_actions(env, scn, lay, roles=ROLES,
                                     limiter_mode=mode, fire_mode="clean",
                                     prev_clean=prev_clean, states=states,
                                     limiter_kw=kw)
    return actor


def _ls_actor(ckpt: str):
    import torch
    import yaml

    from shepherd.scripts.train_m4 import M4Runner
    run_cfg = yaml.safe_load(open("configs/l2_mappo.yaml"))
    runner = M4Runner(run_cfg, 0, "cpu", **_world_kw(),
                      attacker=None, spawn=None, finisher_policy="scripted")
    got = runner.restore(pathlib.Path(ckpt), tag="final")
    assert got > 0, f"체크포인트 복원 실패: {ckpt} (tag=final)"
    policy = runner.policy_fn(deterministic=False)

    def actor(env, scn, lay, states, obs, flags, prev_clean):
        acts = dict(policy(obs, flags))
        acts.update(scripted_role_actions(
            env, scn, lay, roles=("finisher",), fire_mode="clean",
            prev_clean=prev_clean, states=states))
        return acts

    def seed_ep(ep):                      # 에피소드별 재시드 (정성 재현성)
        torch.manual_seed(EVAL_SEED0 + ep)
    actor.seed_ep = seed_ep
    return actor


def main() -> None:
    ap = argparse.ArgumentParser(description="LS 정책 궤적 덤프 (viz-first)")
    ap.add_argument("--arm", choices=["ls", "arc", "hold"])
    ap.add_argument("--ckpt", default="results/m4_v3_train_LS/seed0")
    ap.add_argument("--eps", type=int, nargs="*", default=None)
    ap.add_argument("--scan", type=int, default=40,
                    help="--eps 없으면 0..N 스캔해 NET/PEN 각 4판 수집")
    ap.add_argument("--out", required=False)
    ap.add_argument("--merge", nargs="*", default=None,
                    help="JSON 들을 병합 (arm 접두 group 유지)")
    a = ap.parse_args()

    if a.merge:
        eps = []
        note = []
        for f in a.merge:
            d = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
            eps += d["episodes"]
            note.append(d.get("note", ""))
        out = dict(note=" | ".join(n for n in note if n), episodes=eps)
        p = pathlib.Path(a.out or "results/viz_ls_compare.json")
        p.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
        print(f"-> {p} ({len(eps)} episodes)")
        return

    assert a.arm, "--arm ls|arc|hold 또는 --merge"
    actor = _ls_actor(a.ckpt) if a.arm == "ls" else _scripted_actor(a.arm)
    tag = a.arm.upper()

    episodes = []
    if a.eps is not None:
        targets = a.eps
    else:
        targets = range(a.scan)
    want = dict(NET_CAPTURE=4, PENETRATED=4)
    for ep in targets:
        if a.eps is None and all(v <= 0 for v in want.values()):
            break
        if hasattr(actor, "seed_ep"):
            actor.seed_ep(ep)
        e = _record_episode(ep, actor, _label_of)
        keep = (a.eps is not None) or want.get(e["label"], 0) > 0
        if a.eps is None and e["label"] in want:
            want[e["label"]] -= 1
        if keep:
            e["group"] = f"{tag}-{e['label']}"
            episodes.append(e)
        print(f"[{tag}] ep{ep:>3} {e['label']:>11} steps={len(e['steps'])} "
              f"{'keep' if keep else 'skip'}", flush=True)

    data = dict(note=f"{tag} · eval ns (seed0={EVAL_SEED0}) · threat_layer=train "
                     "· 정성 진단 전용 (판정 사용 금지)",
                episodes=episodes)
    p = pathlib.Path(a.out or f"results/viz_{a.arm}.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"-> {p} ({len(episodes)} episodes)")


if __name__ == "__main__":
    main()
