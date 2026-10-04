"""FS1 MAPPO + PFSP 동시학습 루프 (docs/123).

    python -m shepherd.fs1.train --out artifacts/fs1/run0 --workers 22 --iters 1000
    python -m shepherd.fs1.train --out artifacts/fs1/smoke --workers 2 --iters 4 --steps-per-worker 1500

교대 학습: 짝수 iter = 방어, 홀수 iter = 공격. episode 마다 상대 1개 고정 —
50% 최신 상대 / 50% PFSP (f(x)=(1−x)², x = 그 상대 대비 학습자 승률 EMA).
snapshot: 학습자 iter 승률 ≥ SNAP_WIN 또는 SNAP_EVERY 자기 iter 경과 → 자기 pool 에 추가.
"""
from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import os
import pathlib
import time
from collections import Counter

import numpy as np

DEF_ROLES = {"lim": (3, 1, 4), "fin": (7, 1, 1)}
ATT_ROLES = {"att": (3, 0, 1)}
DEF_WIN = ("NET_CAPTURE", "CAPTURE_WITH_CONTACT", "HARD_KILL")
SNAP_WIN, SNAP_EVERY = 0.6, 20          # G&B 문턱 미기재 → 선언값
LAMBDA_DIST = 1e-5                      # 방어 거리 shaping /m/step (G&B 비율 맞춤)
FIRE_D = 12.0                           # scripted 방어 발사 거리 (sanity sweep 최적)

_W: dict = {}                           # 워커 프로세스 전역 (env·팀 캐시)


# ---------------------------------------------------------------- 행동 매핑 ---
def def_actions(out, env):
    lim_a = float(env.inner.sc.limiter.a_max)
    fin_a = float(env.inner.backend.by_name("finisher_0").limits.a_max)
    acts = {}
    for i, lid in enumerate(env.limiter_ids):
        a = out["lim"][1][i]
        acts[lid] = np.r_[np.clip(a[:3], -1, 1) * lim_a, a[3]]
    c = out["fin"][1][0]
    acts["finisher_0"] = np.r_[c[0:3], np.clip((c[3] + 1) / 2, 0, 1), c[7],
                               np.clip(c[4:7], -1, 1) * fin_a]
    return acts


def scripted_def_actions(env):
    """고정 finisher 가 예측 net 중심 조준, FIRE_D 안에서 1회 발사. limiter 정지."""
    inn = env.inner
    lims, fin, att = inn._states()
    pa, pf = inn._p(att), inn._p(fin)
    nc = np.asarray(inn._net_center(pa, inn._v(att)))
    ax = (nc - pf) / max(np.linalg.norm(nc - pf), 1e-9)
    fire = 1.0 if (np.linalg.norm(pa - pf) < FIRE_D and inn.fsm.state.value == "LOADED") else 0.0
    acts = {l: np.zeros(4) for l in env.limiter_ids}
    acts["finisher_0"] = np.r_[ax, 1.0, fire, 0, 0, 0]
    return acts


def ladder_pool():
    from scripts.p1_ladder_manifest import load
    out = []
    for c in load()["attacker"]["configs"]:
        ov = {k: (float("inf") if v == "inf" else v) for k, v in c["overrides"].items()} \
            if "overrides" in c else {k: v for k, v in c.items() if k != "label"}
        out.append({"kind": "script", "name": c["label"], "ov": ov})
    return out


# ---------------------------------------------------------------- 워커 ---
def _init_worker(spec_kw):
    import torch
    torch.set_num_threads(1)
    from shepherd.fs1.world import FS1Env, FS1Spec
    _W["env"] = FS1Env(FS1Spec(**spec_kw), seed=os.getpid())


def _team(roles, snap, obs_dim):
    from shepherd.fs1.nets import Team
    t = Team(obs_dim, roles); t.load_snapshot(snap); t.eval()
    return t


def _set_opponent(env, side, opp, obs_dim, cache):
    """opp: {"kind": "nn"|"script", ...}. 반환 = 상대 행동 함수 (obs → dict) 또는 None."""
    from shepherd.agents.attacker_ladder import AttackerSpec, make_attacker
    if side == "def":                           # 상대 = 공격자
        if opp["kind"] == "script":
            env.set_scripted_attacker(make_attacker(AttackerSpec(level="A2", **opp["ov"])))
            return None
        env.set_scripted_attacker(None)
        t = cache.setdefault(id(opp["snap"]), _team(ATT_ROLES, opp["snap"], obs_dim))
        att_a = env.att_a_max
        return lambda obs: {"adversary_0": np.clip(t.act(obs)[0]["att"][1][0], -1, 1) * att_a}
    env.set_scripted_attacker(None)            # 학습자 = 공격자 (RL)
    if opp["kind"] == "script":
        return lambda obs: scripted_def_actions(env)
    t = cache.setdefault(id(opp["snap"]), _team(DEF_ROLES, opp["snap"], obs_dim))
    return lambda obs: def_actions(t.act(obs)[0], env)


def rollout(args):
    side, snap, opps, n_steps, gamma, lam, seed, deterministic = args
    env = _W["env"]
    np.random.seed(seed)
    obs0, _ = env.reset(seed=seed)
    obs_dim = len(next(iter(obs0.values())))
    roles = DEF_ROLES if side == "def" else ATT_ROLES
    me = _team(roles, snap, obs_dim)
    cache: dict = {}
    buf = {"obs": [], "obs_n": [], "val": [], "rew": [], "done": [],
           "roles": {r: ([], [], [], []) for r in roles}}
    results, steps, k = [], 0, 0
    while steps < n_steps:
        oi, opp = opps[k % len(opps)]; k += 1
        opp_fn = _set_opponent(env, side, opp, obs_dim, cache)
        obs, _ = env.reset(seed=int(np.random.randint(2**31)))
        done, ep_len = False, 0
        inn = env.inner
        prev_phi = -float(np.linalg.norm(inn._p(inn._states()[2]) - np.asarray(inn.layout.target))) / 100.0
        while not done:
            o = obs["finisher_0"]
            out, v, on = me.act(o, deterministic)
            if side == "def":
                acts = def_actions(out, env)
                if opp_fn is not None:
                    acts.update(opp_fn(o))
            else:
                acts = opp_fn(o)
                acts["adversary_0"] = np.clip(out["att"][1][0], -1, 1) * env.att_a_max
            obs, rew, done, info = env.step(acts)
            r = rew["finisher_0"] if side == "def" else rew["adversary_0"]
            inn = env.inner; _, fin, att = inn._states()
            if side == "def":
                r -= LAMBDA_DIST * float(np.linalg.norm(inn._p(fin) - inn._p(att)))
            else:   # potential-based (최적정책 불변): Φ = −d_asset/100
                phi = -float(np.linalg.norm(inn._p(att) - np.asarray(inn.layout.target))) / 100.0
                if ep_len > 0:
                    r += gamma * (0.0 if done else phi) - prev_phi
                prev_phi = phi
            ti = len(buf["rew"])
            buf["obs"].append(o); buf["obs_n"].append(on); buf["val"].append(v)
            buf["rew"].append(r); buf["done"].append(done)
            for rn, (x, a, lp) in out.items():
                R = buf["roles"][rn]
                R[0].append(x); R[1].append(a); R[2].append(lp); R[3].append(np.full(len(lp), ti))
            ep_len += 1
        label = info["finisher_0"]["fs1_label"]
        win = (label in DEF_WIN) if side == "def" else (label == "PENETRATED")
        results.append((oi, label, bool(win), ep_len))
        steps += ep_len
    from shepherd.fs1.nets import gae
    adv, ret = gae(np.array(buf["rew"]), np.array(buf["val"]), np.array(buf["done"]), gamma, lam)
    roles_out = {r: (np.concatenate(R[0]).astype(np.float32), np.concatenate(R[1]).astype(np.float32),
                     np.concatenate(R[2]).astype(np.float32), np.concatenate(R[3]))
                 for r, R in buf["roles"].items()}
    return {"obs": np.array(buf["obs"], np.float32), "obs_n": np.array(buf["obs_n"], np.float32),
            "adv": adv.astype(np.float32), "ret": ret.astype(np.float32),
            "roles": roles_out, "results": results}


def merge(parts):
    off, roles = 0, {}
    for p in parts:
        for r, (x, a, lp, ti) in p["roles"].items():
            roles.setdefault(r, []).append((x, a, lp, ti + off))
        off += len(p["ret"])
    cat = lambda k: np.concatenate([p[k] for p in parts])
    return {"obs": cat("obs"), "obs_n": cat("obs_n"), "adv": cat("adv"), "ret": cat("ret"),
            "roles": {r: tuple(np.concatenate(z) for z in zip(*v)) for r, v in roles.items()},
            "results": [x for p in parts for x in p["results"]]}


# ---------------------------------------------------------------- 메인 ---
def pfsp_pick(rng, pool, wr, n, latest_idx):
    w = np.array([(1.0 - wr[i]) ** 2 + 1e-3 for i in range(len(pool))])
    w = w / w.sum()
    return [latest_idx if rng.random() < 0.5 else int(rng.choice(len(pool), p=w))
            for _ in range(n)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=max(1, mp.cpu_count() - 2))
    ap.add_argument("--iters", type=int, default=1000)
    ap.add_argument("--steps-per-worker", type=int, default=4096)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--gamma", type=float, default=0.997)
    ap.add_argument("--lam", type=float, default=0.95)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--ckpt-every", type=int, default=20)
    a = ap.parse_args(argv)

    import torch
    from shepherd.fs1.nets import Team, ppo_update
    from shepherd.fs1.world import FS1Env, FS1Spec
    torch.manual_seed(a.seed)
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    spec = FS1Spec()
    probe = FS1Env(spec, seed=0)
    obs_dim = len(next(iter(probe.reset(seed=0)[0].values())))
    del probe
    teams = {"def": Team(obs_dim, DEF_ROLES), "att": Team(obs_dim, ATT_ROLES)}
    opts = {s: torch.optim.Adam(t.parameters(), lr=a.lr) for s, t in teams.items()}
    pools = {"def": [{"kind": "script", "name": "scripted_fin12"},
                     {"kind": "nn", "name": "def_init", "snap": teams["def"].snapshot()}],
             "att": ladder_pool() + [{"kind": "nn", "name": "att_init",
                                      "snap": teams["att"].snapshot()}]}
    other = {"def": "att", "att": "def"}
    wr = {s: [0.5] * len(pools[other[s]]) for s in teams}     # 학습자 s 의 상대별 승률 EMA
    last_snap = {"def": 0, "att": 0}
    rng = np.random.default_rng(a.seed)
    total = 0
    log = open(out / "log.jsonl", "a", encoding="utf-8")
    (out / "config.json").write_text(json.dumps({**vars(a), "spec": spec.__dict__,
                                                 "snap_win": SNAP_WIN, "snap_every": SNAP_EVERY,
                                                 "lambda_dist": LAMBDA_DIST}, default=str), "utf-8")
    ctx = mp.get_context("spawn")
    with ctx.Pool(a.workers, initializer=_init_worker, initargs=(spec.__dict__,)) as P:
        for it in range(a.iters):
            t0 = time.time()
            side = "def" if it % 2 == 0 else "att"
            opp_pool = pools[other[side]]
            latest = {"kind": "nn", "name": f"{other[side]}_latest",
                      "snap": teams[other[side]].snapshot()}
            cand = opp_pool + [latest]
            wr_s = wr[side] + [0.5]
            n_eps = max(8, math.ceil(a.steps_per_worker / 120))
            jobs = []
            for w in range(a.workers):
                picks = pfsp_pick(rng, cand, wr_s, n_eps, len(cand) - 1)
                jobs.append((side, teams[side].snapshot(), [(i, cand[i]) for i in picks],
                             a.steps_per_worker, a.gamma, a.lam, int(rng.integers(2**31)), False))
            batch = merge(P.map(rollout, jobs))
            team = teams[side]
            st = ppo_update(team, opts[side], batch)
            team.norm.update(batch["obs"])
            n = len(batch["ret"]); total += n
            res = batch["results"]
            for oi, _, win, _ in res:
                if oi < len(wr[side]):
                    wr[side][oi] = 0.95 * wr[side][oi] + 0.05 * float(win)
            win_rate = float(np.mean([r[2] for r in res]))
            own_iters = (it - last_snap[side]) // 2
            snapped = False
            if (win_rate >= SNAP_WIN and own_iters >= 2) or own_iters >= SNAP_EVERY:
                pools[side].append({"kind": "nn", "name": f"{side}_it{it}",
                                    "snap": team.snapshot()})
                wr[other[side]].append(0.5)
                last_snap[side] = it; snapped = True
            labels = Counter(r[1] for r in res)
            by_kind = Counter((cand[r[0]]["kind"], r[2]) for r in res)
            rec = {"it": it, "side": side, "steps": n, "total_steps": total,
                   "win_rate": round(win_rate, 4), "n_eps": len(res),
                   "mean_len": round(float(np.mean([r[3] for r in res])), 1),
                   "labels": dict(labels), "vs_script_win": _rate(by_kind, "script"),
                   "vs_nn_win": _rate(by_kind, "nn"), "pool": {s: len(p) for s, p in pools.items()},
                   "snapped": snapped, "sps": round(n / (time.time() - t0), 1), **st}
            log.write(json.dumps(rec) + "\n"); log.flush()
            print(json.dumps(rec), flush=True)
            if (it + 1) % a.ckpt_every == 0 or it == a.iters - 1:
                torch.save({"teams": {s: t.snapshot() for s, t in teams.items()},
                            "pools": {s: [{k: v for k, v in e.items() if k != "snap"} for e in p]
                                      for s, p in pools.items()},
                            "pool_snaps": {s: [e.get("snap") for e in p] for s, p in pools.items()},
                            "wr": wr, "it": it, "total_steps": total}, out / "ckpt.pt")
    log.close()


def _rate(c, kind):
    w, l = c.get((kind, True), 0), c.get((kind, False), 0)
    return round(w / (w + l), 4) if w + l else None


if __name__ == "__main__":
    main()
