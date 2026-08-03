"""파일럿 진단 — 결정론 평가가 발사를 통째로 버리는가.

관측 (파일럿 3런):
    학습 롤아웃  발사(free) 0.31~0.45   free_cap 0.13~0.33   <- 표본추출
    최종 평가    무력화 0.000  침투 1.000                     <- 결정론

`mappo.py:177`  fire = (dist_b.probs > 0.5).float() if deterministic else dist_b.sample()
`train_mappo.py:235`  self.tr.fin_actor.act(t, deterministic=True)

즉 학습된 발사 확률이 어디서도 0.5 를 못 넘으면 **평가에서는 한 번도 안 쏜다.**
그러면 "학습이 신호를 못 찾았다"가 아니라 "찾은 것을 평가가 버렸다"가 된다.
둘은 처방이 완전히 다르므로 여기서 가른다.

    python scripts/diag_fire.py [체크포인트디렉터리] [--episodes 100]
    예: python scripts/diag_fire.py results/m4_pilot/s0/seed0
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np
import torch

import yaml

from shepherd.m4_env import build_m4_env, mission_eval
from shepherd.scripts.train_m4 import (M4Runner, build_parser_defaults,
                                       build_specs)
from shepherd.train.adapter import ShepherdAdapter
from shepherd.train.ippo import limiter_inputs
from shepherd.train.make_env import pad_env_action


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("ckpt_dir")
    ap.add_argument("--episodes", type=int, default=100)
    ap.add_argument("--tag", default="final")
    a = ap.parse_args(argv)

    d = build_parser_defaults()
    specs = build_specs(d)
    run_cfg = yaml.safe_load(open(pathlib.Path(d.config)))
    seed = int(pathlib.Path(a.ckpt_dir).name.replace("seed", "") or 0)
    runner = M4Runner(run_cfg, seed, "cpu", **specs)
    n = runner.restore(pathlib.Path(a.ckpt_dir), tag=a.tag)
    if not n:
        print(f"!! 체크포인트를 못 읽었다: {a.ckpt_dir}  (tag={a.tag})")
        return 1
    # restore() 는 `_adapter` 를 None 으로 되돌린다 (다음 롤아웃에서 재조립).
    # 롤아웃 없이 평가만 하려면 여기서 직접 채워야 한다.
    runner._adapter = ShepherdAdapter(build_m4_env(runner.eval_seed0, 0, **runner._m4).env)
    print(f"복원 완료: {a.ckpt_dir}  env_steps={n:,}\n")

    # ── 1. 평가 상태에서 발사 확률이 실제로 얼마인가 ──────────────────────
    probs = []
    for ep in range(12):
        stk = build_m4_env(runner.eval_seed0, ep, **runner._m4)
        env = stk.env
        ad = ShepherdAdapter(env)
        obs_d, _ = env.reset(seed=runner.eval_seed0 + ep)
        obs = obs_d[ad.limiter_ids[0]]
        for _ in range(int(stk.lay.episode_len)):
            nobs = runner.norm.normalize(obs)
            t = torch.as_tensor(nobs[None, :], device=runner.tr.device)
            with torch.no_grad():
                dist_g, dist_b = runner.tr.fin_actor._dists(t)   # (연속, 베르누이)
            probs.append(float(dist_b.probs.reshape(-1)[0]))
            break                                                # 첫 스텝만
    p = np.asarray(probs)
    print(f"발사 확률 (평가 상태 {p.size}개):  중앙값 {np.median(p):.4f}  "
          f"최대 {p.max():.4f}  >0.5 인 비율 {float((p > 0.5).mean()):.3f}")
    print("  -> 최대가 0.5 미만이면 결정론 평가는 **한 번도 안 쏜다**\n")

    # ── 2. 결정론 vs 표본추출 평가 ───────────────────────────────────────
    def bundle(det: bool):
        dev = runner.tr.device

        def lim_fn(obs, flags):
            nobs = runner.norm.normalize(obs)
            t = torch.as_tensor(limiter_inputs(nobs, runner.n), device=dev)
            raw, _ = runner.tr.lim_actor.act(t, deterministic=det)
            return (np.clip(raw.cpu().numpy(), -1.0, 1.0) * runner.lim_scale).astype(np.float32)

        def fin_fn(obs, flags):
            nobs = runner.norm.normalize(obs)
            t = torch.as_tensor(nobs[None, :], device=dev)
            raw, _ = runner.tr.fin_actor.act(t, deterministic=det)
            raw = raw[0].cpu().numpy()
            axis = np.clip(raw[:3], -1.0, 1.0) * runner.fin_axis_scale
            return np.concatenate([axis, raw[3:]]).astype(np.float32)
        return lim_fn, fin_fn

    ids = None

    def make_policy(det, pad=False):
        lim_fn, fin_fn = bundle(det)

        def policy(obs, flags):
            nonlocal ids
            if ids is None:
                ids = (runner._adapter.limiter_ids, runner._adapter.finisher_id)
            lim = lim_fn(obs, flags)
            acts = {lid: np.asarray(lim[i], np.float32) for i, lid in enumerate(ids[0])}
            acts[ids[1]] = np.asarray(fin_fn(obs, flags), np.float32)
            if pad:
                # ★ 학습 롤아웃은 adapter.step 이 pad_env_action 을 건다 (adapter.py:90).
                #   평가 경로(run_episode(policy=...))는 안 건다. finisher live 는 4차원
                #   (axis3+fire)인데 env Box 는 5차원이고 fire 자리는 idx4 다. 패딩 없이
                #   넣으면 fire 가 idx3(예약 slew)으로 가서 **발사가 env 에 안 닿는다**.
                acts = {aid: pad_env_action(aid, a) for aid, a in acts.items()}
            return acts
        return policy

    for det, pad, name in ((True, False, "결정론 · 패딩 없음 (현행)"),
                           (False, False, "표본추출 · 패딩 없음"),
                           (True, True, "결정론 · 패딩 적용 ★"),
                           (False, True, "표본추출 · 패딩 적용 ★")):
        ids = None
        r = mission_eval(runner.eval_seed0, a.episodes, policy=make_policy(det, pad),
                         **runner._m4)
        c = r["counts"]
        print(f"{name:26s}  무력화 {r['neutralized_rate']:.3f}  "
              f"침투 {r['penetrated_rate']:.3f}  "
              f"| NET {c['NET_CAPTURE']} HARD {c['HARD_KILL']} "
              f"SPENT {c['SPENT_FAIL']} PEN {c['PENETRATED']}")
    print("\n★ 행이 크게 높으면 -> 평가 경로에 패딩이 빠진 것. 학습 실패가 아니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
