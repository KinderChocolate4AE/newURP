"""FS1 BC 초기화 (docs/123 §3 A안): scripted 방어 ↔ P1a scripted 공격자 교전을 모방.

    python -m shepherd.fs1.bc --out artifacts/fs1/bc --episodes 3000 --workers 8

방어 (FCS 전술 공간): finisher = 정지·무장·r_fire=FIRE_D, limiter = 정지, net 소진 후 무장 (PN 인계).
episode 의 KFIRST_P 는 kinetic-first 변형 (공격자 KFIRST_R m 안이면 limiter 무장, r3).
공격: P1a 사다리 24 config 의 실제 가속 (att_a_max 로 정규화).
critic 은 같은 rollout 의 할인 return (학습 루프와 같은 보상·shaping) 으로 사전학습.
초기화일 뿐 — 이후 PFSP RL 에서 정책은 제약 없이 벗어날 수 있다.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import pathlib

import numpy as np

from shepherd.fs1.train import (ATT_ROLES, DEF_ROLES, KFIRST_R, LAMBDA_DIST, _W, _init_worker,
                                _r_fire_c, def_shaping, ladder_attacker, ladder_pool,
                                scripted_def_actions)

# def: 위치목표 노이즈 0.135×STATION ≈ 11 m (확률적 BC 검증에서 fallback 유지가 가장 좋음)
INIT_LOG_STD = {"def": {"lim": -2.0, "fin": -2.0}, "att": {"att": -1.6}}   # att = residual (×2·a_max)
GAMMA = 0.997
DART = 0.15                                 # 실행 위치목표 노이즈 (정규화 단위, ×STATION)
KFIRST_P = 0.3                              # kinetic-first 변형 episode 비율 (r3: 탐색 출발점)


def _returns(r, gamma=GAMMA):
    out, g = np.zeros(len(r)), 0.0
    for t in reversed(range(len(r))):
        g = r[t] + gamma * g
        out[t] = g
    return out


def collect(args):
    n_eps, seed = args
    env = _W["env"]
    rng = np.random.default_rng(seed)
    pool = ladder_pool()
    O, FIN_T, FIRE, LIM_T, LIM_ARM, ATT_T, RD, RA, labels = [], [], [], [], [], [], [], [], []
    for _ in range(n_eps):
        cfg = pool[int(rng.integers(len(pool)))]
        base = ladder_attacker(cfg["ov"])
        last = {}

        def cb(p, v, **kw):
            out = base(p, v, **kw); last["a"] = np.asarray(out["a"], float); return out
        env.set_scripted_attacker(cb)
        obs, _ = env.reset(seed=int(rng.integers(2**31)))
        inn, done, rd, ra = env.inner, False, [], []
        prev_phi = -float(np.linalg.norm(inn._p(inn._states()[2]) - np.asarray(inn.layout.target))) / 100
        pot = env.spec.obs_time                      # stack r4p 와 동일 플래그 (D1+D2 결합)
        _, fin0, att0 = inn._states()
        prev_phi_d = -LAMBDA_DIST / (1.0 - GAMMA) * float(np.linalg.norm(inn._p(fin0) - inn._p(att0)))
        kfr = KFIRST_R if rng.random() < KFIRST_P else None
        while not done:
            o = obs["finisher_0"]
            acts = scripted_def_actions(env, kfr)
            f = acts["finisher_0"].copy()
            # 라벨 = scripted 전술 행동 (FCS 공간): 시작위치 유지 · r_fire=FIRE_D · 무장,
            # limiter 는 net 소진 후 무장
            O.append(o); FIN_T.append(np.r_[f[:3], _r_fire_c(f[3], env)]); FIRE.append(f[4])
            LIM_T.append(np.stack([acts[l][:3] for l in env.limiter_ids]))
            LIM_ARM.append(acts[env.limiter_ids[0]][3])
            # DART: 실행 위치목표에만 노이즈 (상태 분포 확장, 라벨 불변)
            acts["finisher_0"] = np.r_[f[:3] + rng.normal(0, DART, 3), f[3], f[4]]
            for lid in env.limiter_ids:
                acts[lid] = np.r_[acts[lid][:3] + rng.normal(0, DART, 3), acts[lid][3]]
            obs, rew, done, info = env.step(acts)
            ATT_T.append(np.clip(last.get("a", np.zeros(3)) / env.att_a_max, -1, 1))
            _, fin, att = inn._states()
            dr, prev_phi_d = def_shaping(float(np.linalg.norm(inn._p(fin) - inn._p(att))),
                                         prev_phi_d, GAMMA, done, pot)
            rd.append(rew["finisher_0"] + dr)
            phi = -float(np.linalg.norm(inn._p(att) - np.asarray(inn.layout.target))) / 100
            ra.append(rew["adversary_0"] + GAMMA * (0.0 if done else phi) - prev_phi); prev_phi = phi
        RD.append(_returns(np.array(rd))); RA.append(_returns(np.array(ra)))
        labels.append(info["finisher_0"]["fs1_label"])
    return {"obs": np.array(O, np.float32), "fin": np.array(FIN_T, np.float32),
            "fire": np.array(FIRE, np.float32), "lim_arm": np.array(LIM_ARM, np.float32),
            "lim_t": np.array(LIM_T, np.float32), "att": np.array(ATT_T, np.float32),
            "ret_def": np.concatenate(RD).astype(np.float32),
            "ret_att": np.concatenate(RA).astype(np.float32), "labels": labels}


def fit(team, obs, targets: dict, ret, *, epochs=8, mb=4096, lr=1e-3, pos_weight=None):
    """targets = {role: (cont_target, bin_target | None[, bin_mask (T,)])}. bin_mask 가 0 인
    샘플은 이산 손실에서 뺀다 (FIRE 는 LOADED 일 때만 의미가 있다)."""
    import torch
    import torch.nn.functional as F
    team.norm.update(obs)
    on = team.norm(obs)
    opt = torch.optim.Adam([p for n, p in team.named_parameters() if "log_std" not in n], lr=lr)
    T = len(obs); hist = []
    for ep in range(epochs):
        perm = np.random.permutation(T); tot = 0.0
        for s in range(0, T, mb):
            idx = perm[s:s + mb]
            x = torch.as_tensor(on[idx])
            loss = F.mse_loss(team.critic(x)[:, 0], torch.as_tensor(ret[idx]))
            for r, tg in targets.items():
                ct, bt = tg[0], tg[1]
                bm = tg[2] if len(tg) > 2 else None
                n = team.roles[r][2]
                xi = x if n == 1 else torch.cat(
                    [x.repeat_interleave(n, 0), torch.eye(n).repeat(len(idx), 1)], 1)
                out = team.actors[r].net(xi)
                # 공유 라벨 (T, d) 는 복제, 개체별 라벨 (T, n, d) 는 xi 순서대로 펼침
                c_t = (torch.as_tensor(ct[idx]).reshape(len(idx) * n, -1) if ct.ndim == 3
                       else torch.as_tensor(ct[idx]).repeat_interleave(n, 0))
                loss = loss + F.mse_loss(out[:, :team.roles[r][0]], c_t)
                if bt is not None:
                    b_t = torch.as_tensor(bt[idx]).repeat_interleave(n, 0)
                    pw = None if pos_weight is None else torch.tensor([pos_weight.get(r, 1.0)])
                    bl = F.binary_cross_entropy_with_logits(
                        out[:, team.roles[r][0]:], b_t, pos_weight=pw, reduction="none").mean(1)
                    if bm is not None:
                        w = torch.as_tensor(bm[idx]).repeat_interleave(n, 0)
                        bl = (bl * w).sum() / w.sum().clamp_min(1.0)
                    else:
                        bl = bl.mean()
                    loss = loss + bl
            opt.zero_grad(); loss.backward(); opt.step(); tot += float(loss.detach()) * len(idx)
        hist.append(round(tot / T, 5))
    return hist


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True)
    ap.add_argument("--episodes", type=int, default=3000)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--stack", choices=["r4", "r4p"], default="r4",
                    help="r4p = r4' (관측 t/T 채널 + potential 거리 shaping 의 BC 재현)")
    ap.add_argument("--k-viab", type=float, default=0.0, help="arm B: critic return 에 κ 항 재현")
    a = ap.parse_args(argv)
    import torch
    from collections import Counter
    from shepherd.fs1.nets import Team
    from shepherd.fs1.world import FS1Spec
    torch.manual_seed(a.seed); np.random.seed(a.seed)
    torch.set_num_threads(min(4, a.workers))     # fit 단계 (수집 후 워커는 종료됨)
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    per = -(-a.episodes // a.workers)
    with mp.get_context("spawn").Pool(a.workers, initializer=_init_worker,
                                      initargs=(FS1Spec(obs_time=a.stack == "r4p",
                                                        k_viab=a.k_viab).__dict__,)) as P:
        parts = P.map(collect, [(per, a.seed * 1000 + w) for w in range(a.workers)])
    cat = lambda k: np.concatenate([p[k] for p in parts])
    obs, fire = cat("obs"), cat("fire")
    labels = Counter(l for p in parts for l in p["labels"])
    n_pos = max(int(fire.sum()), 1)
    D = Team(obs.shape[1], DEF_ROLES, INIT_LOG_STD["def"])
    lim_arm = cat("lim_arm")
    hd = fit(D, obs, {"lim": (cat("lim_t"), lim_arm[:, None]),
                      "fin": (cat("fin"), fire[:, None])}, cat("ret_def"), epochs=a.epochs)
    torch.save({"def": D.snapshot(), "init_log_std": INIT_LOG_STD},
               out / "bc_snapshots.pt")
    rep = {"episodes": sum(len(p["labels"]) for p in parts), "samples": int(len(obs)),
           "arm_positives": n_pos, "scripted_labels": dict(labels),
           "lim_arm_frac": float(lim_arm.mean()), "loss_def": hd}
    (out / "bc_report.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
