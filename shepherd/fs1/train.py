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

from shepherd.fs1.world import DEFENDED, Z_DIM

DEF_ROLES = {"lim": (3, 1, 4), "fin": (4, 1, 1)}   # FCS 전술 행동: lim [a3|arm], fin [a3, r_fire|arm]
ATT_ROLES = {"att": (3, 0, 1)}
DEF_WIN = DEFENDED                      # net · fallback kinetic · K_FIRST (r3 A안)
SNAP_WIN, SNAP_EVERY = 0.6, 20          # G&B 문턱 미기재 → 선언값 (자기 iter 단위)
SNAP_MIN_OWN = 10                       # 승률 snapshot 최소 간격 (run2: 공격 pool 105 vs 방어 10)
DEF_PER_ATT = 2                         # 방어 iter : 공격 iter (run2: 공격자가 3배 빠른 lr 로 앞지름)
KFIRST_R = 50.0                         # scripted kinetic-first 변형 무장 거리 (31~32/32 성공 측정)
LAMBDA_DIST = 1e-5                      # 방어 거리 shaping /m/step (G&B 비율 맞춤)
LAMBDA_DIV = 5e-3                       # 공격자 다양성 패널티 /step (≤0: episode 늘려 보상 긁기 방지)
DISC_IN = 6                             # 판별기 입력: LOS 좌표계 속도 3 + 가속 3
FIRE_D = 12.0                           # scripted 방어 발사 거리 (sanity sweep 최적)

_W: dict = {}                           # 워커 프로세스 전역 (env·팀 캐시)


# ---------------------------------------------------------------- 행동 매핑 ---
def _r_fire(c, env):
    lo, hi = env.spec.r_fire_range
    return lo + (np.clip(c, -1, 1) + 1) / 2 * (hi - lo)


def _r_fire_c(r, env):
    lo, hi = env.spec.r_fire_range
    return 2 * (r - lo) / (hi - lo) - 1


def def_actions(out, env):
    """정책 출력 (정규화) → FCS 전술 행동. 이동 3채널 = 위치 목표 c∈[-1,1]³."""
    acts = {}
    for i, lid in enumerate(env.limiter_ids):
        a = out["lim"][1][i]
        acts[lid] = np.r_[np.clip(a[:3], -1, 1), a[3]]
    c = out["fin"][1][0]
    acts["finisher_0"] = np.r_[np.clip(c[:3], -1, 1), _r_fire(c[3], env), c[4]]
    return acts


def scripted_def_actions(env, kfirst_r=None):
    """scripted 방어 (FCS 공간): 전원 시작 위치 유지, finisher 무장·r_fire = FIRE_D.
    limiter 는 net 소진 (miss handoff) 후 무장 → FCS PN 인계 = B0 v3 'NET_FAIL 후 PN
    takeover' 조항. (run1: limiter 무장 0 을 BC 로 배워 kinetic fallback 이 탐색되지 않았다.)
    kfirst_r 를 주면 kinetic-first 변형: 공격자가 자산 kfirst_r m 안이면 limiter 무장 (r3)."""
    inn = env.inner
    d_att = float(np.linalg.norm(inn._p(inn._states()[2]) - np.asarray(inn.layout.target)))
    arm = 1.0 if (env.sys.net_spent or (kfirst_r is not None and d_att <= kfirst_r)) else 0.0
    st = env.start_station
    acts = {l: np.r_[st[l], arm] for l in env.limiter_ids}
    acts["finisher_0"] = np.r_[st["finisher_0"], FIRE_D, 1.0]
    return acts


def att_feat(env, v_prev):
    """판별기 입력: 공격자 속도·가속을 자산-LOS 좌표계 (radial, tangential, z) 로."""
    inn = env.inner
    att = inn._states()[2]
    p, v = inn._p(att), inn._v(att)
    r = p - np.asarray(inn.layout.target, float); r[2] = 0.0
    ur = r / max(np.linalg.norm(r), 1e-9); ut = np.array([-ur[1], ur[0], 0.0]); uz = np.array([0, 0, 1.0])
    a = (v - v_prev) / inn.dt
    return np.array([v @ ur / 25, v @ ut / 25, v @ uz / 25,
                     a @ ur / 20, a @ ut / 20, a @ uz / 20], np.float32), v


def att_action(out, env):
    return np.clip(out["att"][1][0], -1, 1) * 2.0 * env.att_a_max      # 전권 residual


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


def _team(roles, snap, obs_dim, disc=None):
    from shepherd.fs1.nets import Team
    t = Team(obs_dim, roles, disc=disc); t.load_snapshot(snap); t.eval()
    return t


def _set_opponent(env, side, opp, obs_dim, cache):
    """opp: {"kind": "nn"|"script", ...}. 반환 = 상대 행동 함수 (obs → dict) 또는 None."""
    from shepherd.agents.attacker_ladder import AttackerSpec, make_attacker
    if side == "def":                           # 상대 = 공격자
        if opp["kind"] == "script":
            env.set_scripted_attacker(make_attacker(AttackerSpec(level="A2", **opp["ov"])))
            return None
        env.set_scripted_attacker(None)
        t = cache.setdefault(id(opp["snap"]), _team(ATT_ROLES, opp["snap"], obs_dim + Z_DIM,
                                                    disc=(DISC_IN, Z_DIM)))
        return lambda obs: {"adversary_0": att_action(t.act(env.att_obs(obs))[0], env)}
    env.set_scripted_attacker(None)            # 학습자 = 공격자 (RL)
    if opp["kind"] == "script":
        return lambda obs: scripted_def_actions(env, opp.get("kfirst_r"))
    t = cache.setdefault(id(opp["snap"]), _team(DEF_ROLES, opp["snap"], obs_dim))
    return lambda obs: def_actions(t.act(obs)[0], env)


def rollout(args):
    import torch
    side, snap, opps, n_steps, gamma, lam, seed, deterministic = args
    env = _W["env"]
    np.random.seed(seed)
    obs0, _ = env.reset(seed=seed)
    obs_dim = len(next(iter(obs0.values())))
    roles = DEF_ROLES if side == "def" else ATT_ROLES
    me = (_team(roles, snap, obs_dim) if side == "def"
          else _team(roles, snap, obs_dim + Z_DIM, disc=(DISC_IN, Z_DIM)))
    feats, zs = [], []
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
        v_prev = inn._v(inn._states()[2])
        while not done:
            o = obs["finisher_0"]
            z_t = env.z.copy()
            oo = o if side == "def" else env.att_obs(o)      # 공격자 관측 = obs + 스타일 z
            out, v, on = me.act(oo, deterministic)
            if side == "def":
                acts = def_actions(out, env)
                if opp_fn is not None:
                    acts.update(opp_fn(o))
            else:
                acts = opp_fn(o)
                acts["adversary_0"] = att_action(out, env)
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
                f, v_prev = att_feat(env, v_prev)          # 다양성 (DIAYN 식, 이산 스킬)
                with torch.no_grad():
                    q = torch.softmax(me.disc(torch.as_tensor(f)[None])[0], 0).numpy()
                r -= LAMBDA_DIV * (1.0 - float(q[int(np.argmax(z_t))]))   # 판별 실패만큼 패널티
                feats.append(f); zs.append(z_t)
            ti = len(buf["rew"])
            buf["obs"].append(oo); buf["obs_n"].append(on); buf["val"].append(v)
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
            "roles": roles_out, "results": results,
            "feat": np.array(feats, np.float32).reshape(-1, DISC_IN),
            "z": np.array(zs, np.float32).reshape(-1, Z_DIM)}


def merge(parts):
    off, roles = 0, {}
    for p in parts:
        for r, (x, a, lp, ti) in p["roles"].items():
            roles.setdefault(r, []).append((x, a, lp, ti + off))
        off += len(p["ret"])
    cat = lambda k: np.concatenate([p[k] for p in parts])
    return {"obs": cat("obs"), "obs_n": cat("obs_n"), "adv": cat("adv"), "ret": cat("ret"),
            "feat": cat("feat"), "z": cat("z"),
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
    ap.add_argument("--lr", type=float, default=3e-5,
                    help="방어 팀 lr (BC 초기화된 좁은 정책 — 1e-4 에서 step 당 KL 0.1~0.3)")
    ap.add_argument("--lr-att", type=float, default=1e-4, help="공격 팀 lr")
    ap.add_argument("--gamma", type=float, default=0.997)
    ap.add_argument("--lam", type=float, default=0.95)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--ckpt-every", type=int, default=20)
    ap.add_argument("--torch-threads", type=int, default=2)
    ap.add_argument("--init", default=None, help="BC 스냅샷 (shepherd.fs1.bc 산출물)")
    ap.add_argument("--total-steps", type=float, default=None,
                    help="이 env step 수에 도달하면 종료 (워커 수와 무관한 예산)")
    a = ap.parse_args(argv)

    import torch
    from shepherd.fs1.nets import Team, ppo_update
    from shepherd.fs1.world import FS1Env, FS1Spec
    torch.manual_seed(a.seed)
    torch.set_num_threads(a.torch_threads)      # 공용 서버: 총 코어 = workers + torch_threads
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    spec = FS1Spec()
    probe = FS1Env(spec, seed=0)
    obs_dim = len(next(iter(probe.reset(seed=0)[0].values())))
    del probe
    from shepherd.fs1.bc import INIT_LOG_STD
    teams = {"def": Team(obs_dim, DEF_ROLES, INIT_LOG_STD["def"]),
             "att": Team(obs_dim + Z_DIM, ATT_ROLES, INIT_LOG_STD["att"], disc=(DISC_IN, Z_DIM))}
    tag = "init"
    if a.init:                                   # BC 초기화 (docs/123 A안)
        bc = torch.load(a.init, weights_only=False)
        teams["def"].load_snapshot(bc["def"])      # 공격자는 autopilot + residual 0 에서 출발
        with torch.no_grad():                      # 탐색 std 는 BC 스냅샷이 아니라 선언값
            for r_, v_ in INIT_LOG_STD["def"].items():
                teams["def"].actors[r_].log_std.fill_(v_)
        tag = "bc"
    lrs = {"def": a.lr, "att": a.lr_att}
    opts = {s: torch.optim.Adam(t.parameters(), lr=lrs[s]) for s, t in teams.items()}
    pools = {"def": [{"kind": "script", "name": "scripted_fin12"},
                     {"kind": "script", "name": "scripted_kfirst50", "kfirst_r": KFIRST_R},
                     {"kind": "nn", "name": f"def_{tag}", "snap": teams["def"].snapshot()}],
             "att": ladder_pool() + [{"kind": "nn", "name": f"att_{tag}",
                                      "snap": teams["att"].snapshot()}]}
    other = {"def": "att", "att": "def"}
    wr = {s: [0.5] * len(pools[other[s]]) for s in teams}     # 학습자 s 의 상대별 승률 EMA
    since_snap = {"def": 0, "att": 0}                         # 자기 iter 수 (마지막 snapshot 이후)
    rng = np.random.default_rng(a.seed)
    total = 0
    log = open(out / "log.jsonl", "a", encoding="utf-8")
    (out / "config.json").write_text(json.dumps({**vars(a), "spec": spec.__dict__,
                                                 "snap_win": SNAP_WIN, "snap_every": SNAP_EVERY,
                                                 "lambda_dist": LAMBDA_DIST, "lambda_div": LAMBDA_DIV,
                                                 "snap_min_own": SNAP_MIN_OWN, "def_per_att": DEF_PER_ATT,
                                                 "kfirst_r": KFIRST_R, "z_dim": Z_DIM},
                                                default=str), "utf-8")
    ctx = mp.get_context("spawn")
    with ctx.Pool(a.workers, initializer=_init_worker, initargs=(spec.__dict__,)) as P:
        for it in range(a.iters):
            t0 = time.time()
            side = "att" if it % (DEF_PER_ATT + 1) == DEF_PER_ATT else "def"
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
            if side == "att":
                st["disc_ce"], st["disc_acc"] = train_disc(team, batch["feat"], batch["z"])
            team.norm.update(batch["obs"])
            n = len(batch["ret"]); total += n
            res = batch["results"]
            for oi, _, win, _ in res:
                if oi < len(wr[side]):
                    wr[side][oi] = 0.95 * wr[side][oi] + 0.05 * float(win)
            win_rate = float(np.mean([r[2] for r in res]))
            since_snap[side] += 1
            snapped = False
            if ((win_rate >= SNAP_WIN and since_snap[side] >= SNAP_MIN_OWN)
                    or since_snap[side] >= SNAP_EVERY):
                pools[side].append({"kind": "nn", "name": f"{side}_it{it}",
                                    "snap": team.snapshot()})
                wr[other[side]].append(0.5)
                since_snap[side] = 0; snapped = True
            labels = Counter(r[1] for r in res)
            by_kind = Counter((cand[r[0]]["kind"], r[2]) for r in res)
            # mode 감시: 상대 유형별 종료 라벨 (net / K_FIRST / fallback HARD_KILL / 침투)
            mode_by_kind = {k: dict(Counter(r[1] for r in res if cand[r[0]]["kind"] == k))
                            for k in ("script", "nn")}
            rec = {"it": it, "side": side, "steps": n, "total_steps": total,
                   "win_rate": round(win_rate, 4), "n_eps": len(res),
                   "mean_len": round(float(np.mean([r[3] for r in res])), 1),
                   "labels": dict(labels), "vs_script_win": _rate(by_kind, "script"),
                   "vs_nn_win": _rate(by_kind, "nn"), "labels_by_kind": mode_by_kind,
                   "pool": {s: len(p) for s, p in pools.items()},
                   "snapped": snapped, "sps": round(n / (time.time() - t0), 1), **st}
            log.write(json.dumps(rec) + "\n"); log.flush()
            print(json.dumps(rec), flush=True)
            last = it == a.iters - 1 or (a.total_steps is not None and total >= a.total_steps)
            if (it + 1) % a.ckpt_every == 0 or last:
                torch.save({"teams": {s: t.snapshot() for s, t in teams.items()},
                            "pools": {s: [{k: v for k, v in e.items() if k != "snap"} for e in p]
                                      for s, p in pools.items()},
                            "pool_snaps": {s: [e.get("snap") for e in p] for s, p in pools.items()},
                            "wr": wr, "it": it, "total_steps": total}, out / "ckpt.pt")
            if last:
                break
    log.close()


def train_disc(team, feat, z, epochs=3, mb=4096, lr=1e-3):
    import torch
    opt = getattr(team, "_disc_opt", None) or torch.optim.Adam(team.disc.parameters(), lr=lr)
    team._disc_opt = opt
    import torch.nn.functional as Fn
    F, K = torch.as_tensor(feat), torch.as_tensor(z).argmax(1)   # one-hot 스킬 → 클래스
    loss = torch.zeros(())
    for _ in range(epochs):
        perm = torch.randperm(len(F))
        for s in range(0, len(F), mb):
            i = perm[s:s + mb]
            loss = Fn.cross_entropy(team.disc(F[i]), K[i])
            opt.zero_grad(); loss.backward(); opt.step()
    with torch.no_grad():
        acc = float((team.disc(F).argmax(1) == K).float().mean())
    return round(float(loss.detach()), 4), round(acc, 4)          # 우연 수준 acc = 1/Z_DIM


def _rate(c, kind):
    w, l = c.get((kind, True), 0), c.get((kind, False), 0)
    return round(w / (w + l), 4) if w + l else None


if __name__ == "__main__":
    main()
