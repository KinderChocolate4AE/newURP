"""FS1 BC 초기화 (docs/123 §3 A안): scripted 방어 ↔ P1a scripted 공격자 교전을 모방.

    python -m shepherd.fs1.bc --out artifacts/fs1/bc --episodes 3000 --workers 8

방어 (FCS 전술 공간): finisher = 정지·무장·r_fire=FIRE_D, limiter = 정지·비무장.
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

from shepherd.fs1.train import (ATT_ROLES, DEF_ROLES, LAMBDA_DIST, _W, _init_worker,
                                _r_fire_c, ladder_pool, scripted_def_actions)

INIT_LOG_STD = {"def": {"lim": -1.0, "fin": -1.0}, "att": {"att": -1.6}}   # att = residual (×2·a_max)
GAMMA = 0.997
DART = 0.3                                  # 실행 노이즈 (a_max 대비 표준편차)


def _returns(r, gamma=GAMMA):
    out, g = np.zeros(len(r)), 0.0
    for t in reversed(range(len(r))):
        g = r[t] + gamma * g
        out[t] = g
    return out


def collect(args):
    n_eps, seed = args
    from shepherd.agents.attacker_ladder import AttackerSpec, make_attacker
    env = _W["env"]
    rng = np.random.default_rng(seed)
    pool = ladder_pool()
    O, FIN_T, FIRE, ATT_T, RD, RA, labels = [], [], [], [], [], [], []
    for _ in range(n_eps):
        cfg = pool[int(rng.integers(len(pool)))]
        base = make_attacker(AttackerSpec(level="A2", **cfg["ov"]))
        last = {}

        def cb(p, v, **kw):
            out = base(p, v, **kw); last["a"] = np.asarray(out["a"], float); return out
        env.set_scripted_attacker(cb)
        obs, _ = env.reset(seed=int(rng.integers(2**31)))
        inn, done, rd, ra = env.inner, False, [], []
        fa = float(inn.backend.by_name("finisher_0").limits.a_max); la = float(inn.sc.limiter.a_max)
        prev_phi = -float(np.linalg.norm(inn._p(inn._states()[2]) - np.asarray(inn.layout.target))) / 100
        while not done:
            o = obs["finisher_0"]
            acts = scripted_def_actions(env)
            f = acts["finisher_0"]
            # 라벨 = scripted 전술 행동 (FCS 공간): 정지 · r_fire=FIRE_D · 무장
            O.append(o); FIN_T.append(np.r_[0.0, 0.0, 0.0, _r_fire_c(f[3], env)]); FIRE.append(f[4])
            # DART: 실행 행동에만 무작위 가속 (방어자 상태 분포 확장, 라벨 불변)
            acts["finisher_0"] = np.r_[rng.normal(0, DART * fa, 3), f[3], f[4]]
            for lid in env.limiter_ids:
                acts[lid] = np.r_[rng.normal(0, DART * la, 3), 0.0]
            obs, rew, done, info = env.step(acts)
            ATT_T.append(np.clip(last.get("a", np.zeros(3)) / env.att_a_max, -1, 1))
            _, fin, att = inn._states()
            rd.append(rew["finisher_0"] - LAMBDA_DIST * float(np.linalg.norm(inn._p(fin) - inn._p(att))))
            phi = -float(np.linalg.norm(inn._p(att) - np.asarray(inn.layout.target))) / 100
            ra.append(rew["adversary_0"] + GAMMA * (0.0 if done else phi) - prev_phi); prev_phi = phi
        RD.append(_returns(np.array(rd))); RA.append(_returns(np.array(ra)))
        labels.append(info["finisher_0"]["fs1_label"])
    return {"obs": np.array(O, np.float32), "fin": np.array(FIN_T, np.float32),
            "fire": np.array(FIRE, np.float32), "att": np.array(ATT_T, np.float32),
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
                c_t = torch.as_tensor(ct[idx]).repeat_interleave(n, 0)
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
    a = ap.parse_args(argv)
    import torch
    from collections import Counter
    from shepherd.fs1.nets import Team
    from shepherd.fs1.world import FS1Spec
    torch.manual_seed(a.seed); np.random.seed(a.seed)
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    per = -(-a.episodes // a.workers)
    with mp.get_context("spawn").Pool(a.workers, initializer=_init_worker,
                                      initargs=(FS1Spec().__dict__,)) as P:
        parts = P.map(collect, [(per, a.seed * 1000 + w) for w in range(a.workers)])
    cat = lambda k: np.concatenate([p[k] for p in parts])
    obs, fire = cat("obs"), cat("fire")
    labels = Counter(l for p in parts for l in p["labels"])
    n_pos = max(int(fire.sum()), 1)
    D = Team(obs.shape[1], DEF_ROLES, INIT_LOG_STD["def"])
    zl = np.zeros((len(obs), 3), np.float32)
    hd = fit(D, obs, {"lim": (zl, np.zeros((len(obs), 1), np.float32)),
                      "fin": (cat("fin"), fire[:, None])}, cat("ret_def"), epochs=a.epochs)
    torch.save({"def": D.snapshot(), "init_log_std": INIT_LOG_STD},
               out / "bc_snapshots.pt")
    rep = {"episodes": sum(len(p["labels"]) for p in parts), "samples": int(len(obs)),
           "arm_positives": n_pos, "scripted_labels": dict(labels),
           "loss_def": hd}
    (out / "bc_report.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
