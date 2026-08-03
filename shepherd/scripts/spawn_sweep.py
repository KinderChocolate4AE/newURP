"""스폰 랜덤화 영향 실측 — 배선 후 학습 전 필수 확인 (docs/36 §4).

고정 스폰 vs 랜덤 스폰에서 임무 라벨 분포가 어떻게 달라지는지 본다.
**결과를 보고 스폰 범위를 조정하지 않는다** -- 범위는 선언값이고, 이 실행은
"시나리오가 여전히 적형인가"를 확인하는 게이트다 (P26 의 임무 레벨 버전).

  python -m shepherd.scripts.spawn_sweep --episodes 40
"""
from __future__ import annotations

import argparse
from collections import Counter

import numpy as np

from shepherd.params import as_config
from shepherd.train.make_env import make_train_env
from shepherd.spawn_rand import SpawnSpec, spawn_for_episode
from shepherd.scripts.mission_rollout import run_episode, summarize


def run(spec: SpawnSpec, *, episodes: int, seed0: int, limiter_mode: str,
        fire_mode: str, overrides=None):
    cfg = as_config(overrides or {})
    out = []
    lat, xs = [], []
    for ep in range(episodes):
        env, scn, lay = make_train_env(cfg)
        d = spawn_for_episode(env, spec, seed=seed0, episode=ep)
        xs.append(d.p[0]); lat.append(float(np.hypot(d.p[1], d.p[2])))
        out.append(run_episode(env, scn, lay, seed=seed0 + ep,
                               limiter_mode=limiter_mode, fire_mode=fire_mode))
    return out, np.array(xs), np.array(lat)


def _fmt(tag, res, xs, lat):
    s = summarize(res)
    c = Counter(r.label for r in res)
    print(f"\n[{tag}]  n={s['n']}   spawn: x {xs.min():.1f}-{xs.max():.1f}"
          f"  lat {lat.min():.2f}-{lat.max():.2f} (mean {lat.mean():.2f})")
    print(f"   라벨       {dict(c)}")
    print(f"   침투저지율 {s['interdiction_rate']:.3f}   침투율 {s['penetration_rate']:.3f}")
    print(f"   비손실비율 {s['nondestructive_frac']:.3f}   무접촉 {s['contact_free_frac']:.3f}")
    print(f"   평균접촉   {s['mean_contact']:.2f}   평균 최소거리 {s['mean_min_dist']:.2f}")
    print(f"   clean교차  {sum(r.clean_crossings for r in res)}"
          f"   발사 {sum(1 for r in res if r.fire_step is not None)}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=40)
    ap.add_argument("--seed0", type=int, default=0)
    ap.add_argument("--limiter", default="ring")
    ap.add_argument("--fire", default="clean")
    a = ap.parse_args(argv)

    for tag, spec in (("FIXED (현행)", SpawnSpec(enabled=False)),
                      ("RANDOM (선언)", SpawnSpec()),
                      ("RANDOM lat=2.5", SpawnSpec(r_lat=2.5)),
                      ("RANDOM psi=0.15", SpawnSpec(psi=0.15))):
        res, xs, lat = run(spec, episodes=a.episodes, seed0=a.seed0,
                           limiter_mode=a.limiter, fire_mode=a.fire)
        _fmt(tag, res, xs, lat)


if __name__ == "__main__":
    main()
