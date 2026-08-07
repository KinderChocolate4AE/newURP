"""Phase 2C MAPPO runner on the frozen shepherd env (docs/09 SS5 Phase 2C).

2B actors unchanged + ONE central critic on the shared 63-dim obs (ratified
2026-07-04: strict superset of the literal env.state() -- see
shepherd/train/mappo.py). Value-target normalization + orthogonal init ON
(ratified). Everything else mirrors the stabilized 2B runner: [-1,1] action
convention, obs RunningNorm, attacker-family randomization (train only),
LR anneal, 20-episode evals, LAST-3-EVAL-MEAN judgment, wandb optional.

CLI:
    python -m shepherd.scripts.train_mappo --config configs/l2_mappo.yaml \
        --seed 0 --device cuda --output results/mappo_run1

2C DoD (docs/09 SS5): MAPPO return >= 2B(IPPO) + stable training (NaN 0, KL
normal). The runner therefore also loads the 2B reference results
(``ippo_ref`` in the config) and logs ``vs_ippo`` margins.
"""
from __future__ import annotations

import argparse
import copy
import json
import pathlib
import time
from typing import Dict, List, Optional

import numpy as np
import torch
import yaml

from shepherd.train.adapter import ShepherdAdapter
from shepherd.train.attacker_rand import build_attacker_env, sample_attacker_params
from shepherd.train.ippo import limiter_inputs
from shepherd.train.make_env import make_train_env
from shepherd.train.mappo import MAPPOConfig, MAPPORollout, MAPPOTrainer
from shepherd.train.obs_norm import RunningNorm
from shepherd.scripts.train_ippo import (eval_bundle, hold_bundle,
                                         make_scripted_ctx, scripted_bundle,
                                         seed_everything)


def load_ippo_ref(path: Optional[str]) -> Optional[dict]:
    """Mean last-3 return of the 2B reference seeds (results/ippo_run2)."""
    if not path:
        return None
    root = pathlib.Path(path)
    rets = {}
    for f in sorted(root.glob("seed*/summary.json")):
        d = json.loads(f.read_text())
        if "return_mean_last3" in d:
            rets[d["seed"]] = float(d["return_mean_last3"])
    if not rets:
        return None
    return {"per_seed": rets, "mean": float(np.mean(list(rets.values())))}


class MAPPORunner:
    """Rollout collection for the single-value-stream MAPPO trainer."""

    def __init__(self, env_cfg: dict, run_cfg: dict, seed: int, device: str):
        self.env_cfg = env_cfg
        loop = run_cfg["loop"]
        self.rollout_env_steps = int(loop["rollout_env_steps"])
        self.seed = int(seed)

        env, _, _ = make_train_env(copy.deepcopy(env_cfg))
        ad = ShepherdAdapter(env)
        self.n = len(ad.limiter_ids)
        self.obs_dim = ad.obs_dim
        lim_low, lim_high = ad.action_bounds(ad.limiter_ids[0])
        fin_low, fin_high = ad.action_bounds(ad.finisher_id)
        if not (np.allclose(lim_low, -lim_high) and np.allclose(fin_low[:3], -fin_high[:3])):
            raise ValueError("action Boxes are expected symmetric for [-1,1] scaling")
        self.lim_scale = lim_high.astype(np.float32)
        self.fin_axis_scale = fin_high[:3].astype(np.float32)

        self.norm = RunningNorm(self.obs_dim)
        total = int(loop["total_env_steps"])
        cfg = MAPPOConfig.from_dict({**run_cfg["mappo"], "seed": seed,
                                     "device": device,
                                     "rollout_steps": self.rollout_env_steps,
                                     "total_timesteps": total})
        self.tr = MAPPOTrainer(self.obs_dim, self.n, cfg)
        self.buf = MAPPORollout(self.rollout_env_steps, self.obs_dim, self.n,
                                lim_dim=self.tr.lim_dim)

        self.rand_cfg = run_cfg.get("randomize")
        self.rand_rng = np.random.default_rng(seed * 9973 + 17)
        self.base_seed = seed * 1_000_003 + 1
        self.eval_seed0 = seed * 1_000_003 + 500_000

        self.env_steps = 0
        self.ep_records: List[dict] = []
        self._ep_idx = 0
        self._adapter: Optional[ShepherdAdapter] = None
        self._obs: Optional[np.ndarray] = None
        self._ep: Dict[str, float] = {}

    # ------------------------------------------------------------ episodes ---
    def _begin_episode(self) -> None:
        params = sample_attacker_params(self.rand_cfg, self.rand_rng)
        env, _, _ = build_attacker_env(self.env_cfg, params)
        self._adapter = ShepherdAdapter(env)
        obs_d, _ = self._adapter.reset(seed=self.base_seed + self._ep_idx)
        self._obs = obs_d[self._adapter.limiter_ids[0]]
        self._ep = {"ret": 0.0, "headline": 0.0, "limiter_loss": 0.0,
                    "coma_sum": 0.0, "fire_events": 0.0, "steps": 0.0,
                    "clean": 0.0}
        self._ep_params = params

    def _finish_episode(self, r) -> None:
        steps = max(self._ep["steps"], 1.0)
        self.ep_records.append({
            "ret": self._ep["ret"], "len": int(steps),
            "headline_sum": self._ep["headline"],
            "coma_D_mean": self._ep["coma_sum"] / steps,
            "limiter_loss_sum": self._ep["limiter_loss"],
            "fire_events": self._ep["fire_events"],
            "clean": bool(self._ep["clean"]),
            "wasted": float(r.flags["wasted_fire"]),
            "captured": bool(r.flags["captured"]),
            "penetrated": bool(r.flags["penetrated"]),
            "truncated": bool(r.truncated),
            "attacker_params": dict(self._ep_params),
        })
        if len(self.ep_records) > 500:
            del self.ep_records[:-500]
        self._ep_idx += 1

    # -------------------------------------------------------- 역할 동결 훅 ---
    #   역할 분리 실험(docs/48)이 학습 롤아웃에서 한 역할을 스크립트로 고정할 수
    #   있게 하는 자리다. 여기에 두는 이유는 `collect_rollout` 을 자식이 복사하지
    #   않게 하기 위해서다 -- 이 리포에서 반복된 사고는 전부 "같은 규칙이 두 곳에
    #   있고 한쪽만 갱신됐다" 였다. 기본 구현은 **항등/no-op** 이므로 2B/2C/M2/M3
    #   경로는 bit-identical (P56).
    def _override_live(self, live: Dict[str, np.ndarray], ad: ShepherdAdapter):
        return live

    def _observe_step(self, r) -> None:
        return None

    def _bc_target(self, ad: ShepherdAdapter):
        """조준 BC 라벨 (docs/49). 기본 None -> 버퍼에 아무것도 안 쓴다."""
        return None

    # ------------------------------------------------------------- rollout ---
    def collect_rollout(self) -> None:
        if self._adapter is None:
            self._begin_episode()
        device = self.tr.device
        # Phase 2D causality: env.step computes coma_D on the PRE-move state,
        # so step t's returned D belongs to action t-1. prev_row tracks the
        # buffer row to write back into; None at episode/rollout starts (the
        # last action of an episode/rollout keeps D=0).
        prev_row = None
        for _ in range(self.rollout_env_steps):
            ad = self._adapter
            obs = self._obs
            nobs = self.norm.normalize(obs, update=True)

            x_l = limiter_inputs(nobs, self.n)
            raw_l_t, logp_l = self.tr.lim_actor.act(
                torch.as_tensor(x_l, device=device))
            raw_l = raw_l_t.cpu().numpy()
            # 연속 차원만 클립한다. M4 커밋 비트(idx 3)는 Bernoulli 표본 {0,1} 이라
            # finisher 의 발사 비트와 같은 규약으로 raw 를 그대로 흘려보낸다.
            # lim_dim == 3 이면 이 두 줄은 기존 np.clip(raw_l, -1, 1) 과 동일하다.
            clip_l = raw_l.copy()
            clip_l[:, :3] = np.clip(raw_l[:, :3], -1.0, 1.0)

            raw_f_t, logp_f = self.tr.fin_actor.act(
                torch.as_tensor(nobs[None, :], device=device))
            raw_f = raw_f_t[0].cpu().numpy()
            clip_f = raw_f.copy()
            clip_f[:3] = np.clip(raw_f[:3], -1.0, 1.0)

            value = self.tr.value_np(nobs)               # central V(s_t), denorm

            live = {lid: (clip_l[i] * self.lim_scale).astype(np.float32)
                    for i, lid in enumerate(ad.limiter_ids)}
            live[ad.finisher_id] = np.concatenate(
                [clip_f[:3] * self.fin_axis_scale, clip_f[3:]]).astype(np.float32)

            live = self._override_live(live, ad)     # 역할 동결 훅 (기본 항등)
            # ★ 라벨은 **스텝 전** 상태에서 (obs 와 같은 시점). 스텝 뒤에 뽑으면
            #   한 칸 밀려서 조용히 틀린 것을 가르치게 된다.
            bc_t = self._bc_target(ad)
            bc_kw = {} if bc_t is None else {"bc_target": bc_t}
            r = ad.step(live)
            self._observe_step(r)                    # 스텝 관찰 훅 (기본 no-op)
            next_obs = r.obs[ad.limiter_ids[0]]
            if r.terminated:
                next_value = 0.0
            else:
                next_value = self.tr.value_np(self.norm.normalize(next_obs))

            if prev_row is not None:               # shift-back D(s_t) -> a_{t-1}
                self.buf.coma_D[prev_row] = np.array(
                    [r.coma_D[lid] for lid in ad.limiter_ids], np.float32)
            prev_row = self.buf._i
            # 조준 BC 라벨은 **행동을 내기 전 상태**에서 뽑아야 nobs 와 짝이 맞는다.
            # `_bc_target` 을 ad.step 앞에서 부른 이유가 그것이다 (아래 bc_kw).
            self.buf.add(**bc_kw, obs=nobs, lim_raw=raw_l, lim_clip=clip_l,
                         lim_logp=logp_l.cpu().numpy(),
                         fin_raw=raw_f, fin_clip=clip_f,
                         fin_logp=float(logp_f[0].item()),
                         rewards=r.rewards[ad.finisher_id],
                         values=value, next_values=next_value,
                         dones=1.0 if r.done else 0.0)

            self._ep["ret"] += r.rewards[ad.finisher_id]
            self._ep["headline"] += r.headline
            self._ep["limiter_loss"] += float(r.flags["limiter_loss"])
            self._ep["coma_sum"] += float(np.mean(list(r.coma_D.values())))
            self._ep["fire_events"] += 1.0 if r.flags["fire_event"] else 0.0
            self._ep["clean"] = max(self._ep["clean"],
                                    1.0 if r.flags["clean_net_threshold_crossed"] else 0.0)
            self._ep["steps"] += 1.0
            self.env_steps += 1

            if r.done:
                self._finish_episode(r)
                self._begin_episode()
                prev_row = None                    # no D credit across episodes
            else:
                self._obs = next_obs

    def update(self) -> Dict[str, float]:
        stats = self.tr.update(self.buf)
        self.buf.reset()
        return stats

    def rolling(self, k: int = 20) -> Dict[str, float]:
        recs = self.ep_records[-k:]
        if not recs:
            return {}
        return {
            "train/ep_return": float(np.mean([x["ret"] for x in recs])),
            "train/ep_len": float(np.mean([x["len"] for x in recs])),
            "train/headline_sum": float(np.mean([x["headline_sum"] for x in recs])),
            # ★ diagnostic only (docs/65 D1/D2): coma_mix=0 이면 gradient 미도달.
            #   키 이름은 기존 dump 와의 비교성 때문에 유지 -- 학습 신호로 읽지 말 것.
            "train/coma_D_mean": float(np.mean([x["coma_D_mean"] for x in recs])),
            "train/limiter_loss_sum": float(np.mean([x["limiter_loss_sum"] for x in recs])),
            "train/fire_events": float(np.mean([x["fire_events"] for x in recs])),
            "train/wasted": float(np.mean([x["wasted"] for x in recs])),
            "train/captured_rate": float(np.mean([x["captured"] for x in recs])),
            "train/penetrated_rate": float(np.mean([x["penetrated"] for x in recs])),
            "train/clean_cross_rate": float(np.mean([x["clean"] for x in recs])),
        }

    # ----------------------------------------------------------- eval / io ---
    def learned_bundle(self):
        device = self.tr.device

        def limiter_fn(obs, flags):
            nobs = self.norm.normalize(obs)
            t = torch.as_tensor(limiter_inputs(nobs, self.n), device=device)
            raw, _ = self.tr.lim_actor.act(t, deterministic=True)
            raw = raw.cpu().numpy()
            act = raw.copy()                      # 커밋 비트는 클립하지 않는다
            act[:, :3] = np.clip(raw[:, :3], -1.0, 1.0)   # lim_dim==3 이면 기존과 동일
            return (act * self.lim_scale).astype(np.float32)

        def finisher_fn(obs, flags):
            nobs = self.norm.normalize(obs)
            t = torch.as_tensor(nobs[None, :], device=device)
            raw, _ = self.tr.fin_actor.act(t, deterministic=True)
            raw = raw[0].cpu().numpy()
            axis = np.clip(raw[:3], -1.0, 1.0) * self.fin_axis_scale
            return np.concatenate([axis, raw[3:]]).astype(np.float32)

        return limiter_fn, finisher_fn

    def evaluate(self, episodes: int) -> dict:
        lim_fn, fin_fn = self.learned_bundle()
        return eval_bundle(self.env_cfg, lim_fn, fin_fn, episodes, self.eval_seed0)

    def save(self, out_dir: pathlib.Path, tag: str = "latest") -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        self.tr.save(out_dir / f"ckpt_mappo_{tag}.pt")
        (out_dir / f"obs_norm_{tag}.json").write_text(
            json.dumps(self.norm.state_dict()))
        (out_dir / f"run_state_{tag}.json").write_text(json.dumps({
            "env_steps": self.env_steps, "episodes": self._ep_idx,
            "seed": self.seed}))


# --------------------------------------------------------------------- main ---
def run_one(run_cfg: dict, env_cfg: dict, seed: int, device: str,
            out_root: pathlib.Path, use_wandb: bool) -> dict:
    seed_everything(seed)
    loop = run_cfg["loop"]
    total = int(loop["total_env_steps"])
    eval_every = int(loop["eval_interval_updates"])
    save_every = int(loop.get("save_interval_updates", eval_every))
    eval_eps = int(loop["eval_episodes"])
    anneal = str(loop.get("lr_anneal", "none")).lower()
    # recipe-v2: anneal FLOOR (e.g. 0.1 -> LR decays to 10% and holds) keeps
    # late-training refinement alive instead of freezing into the first basin
    # (2C run-1 seeds 2/5 plateaued low under floor=0).
    anneal_floor = float(loop.get("lr_anneal_floor", 0.0))
    out_dir = out_root / f"seed{seed}"
    out_dir.mkdir(parents=True, exist_ok=True)

    runner = MAPPORunner(env_cfg, run_cfg, seed, device)
    n_updates = max(1, total // runner.rollout_env_steps)
    ippo_ref = load_ippo_ref(run_cfg.get("ippo_ref"))
    mappo_ref = load_ippo_ref(run_cfg.get("mappo_ref"))   # same summary schema

    wb = None
    if use_wandb:
        try:
            import wandb
            wcfg = run_cfg.get("wandb", {})
            wb = wandb.init(project=wcfg.get("project", "newurp-l2"),
                            group=wcfg.get("group", "phase2c-mappo"),
                            name=f"mappo_seed{seed}",
                            config={"seed": seed, "device": device,
                                    "run_cfg": run_cfg})
        except Exception as e:
            print(f"[wandb disabled] {type(e).__name__}: {e}")
            wb = None

    ctx = make_scripted_ctx(env_cfg)
    baselines = {
        "hold_position": eval_bundle(env_cfg, *hold_bundle(ctx),
                                     episodes=eval_eps, seed0=runner.eval_seed0),
        "scripted_shaping": eval_bundle(env_cfg, *scripted_bundle(ctx),
                                        episodes=eval_eps, seed0=runner.eval_seed0),
    }
    (out_dir / "baselines.json").write_text(json.dumps(baselines, indent=2))
    base_best = max(v["return_mean"] for v in baselines.values())
    for name, v in baselines.items():
        print(f"[baseline {name}] return={v['return_mean']:.3f}"
              f"+-{v['return_std']:.3f} captured={v['captured_rate']:.2f}")
    if ippo_ref:
        print(f"[ippo ref] mean_last3_return={ippo_ref['mean']:.3f} "
              f"per_seed={ippo_ref['per_seed']}")
    if mappo_ref:
        print(f"[mappo ref] mean_last3_return={mappo_ref['mean']:.3f} "
              f"per_seed={mappo_ref['per_seed']}")

    eval_curve, train_curve = [], []
    best3 = float("-inf")
    t0 = time.monotonic()
    for upd in range(1, n_updates + 1):
        lr_frac = 1.0
        if anneal == "linear":
            lr_frac = (anneal_floor + (1.0 - anneal_floor)
                       * (1.0 - (upd - 1) / n_updates))
            runner.tr.set_lr(runner.tr.cfg.lr * lr_frac)
        runner.collect_rollout()
        stats = runner.update()
        roll = runner.rolling()
        sps = runner.env_steps / max(time.monotonic() - t0, 1e-9)
        train_curve.append({"step": runner.env_steps,
                            **{k: roll.get(k, float("nan")) for k in
                               ("train/ep_return", "train/captured_rate",
                                "train/penetrated_rate", "train/wasted")}})
        if wb:
            wb.log({**stats, **roll, "perf/env_steps_per_sec": sps,
                    "perf/lr_frac": lr_frac}, step=runner.env_steps)
        print(f"[seed {seed}] upd {upd}/{n_updates} step={runner.env_steps} "
              f"ep_ret={roll.get('train/ep_return', float('nan')):.3f} "
              f"cap={roll.get('train/captured_rate', float('nan')):.2f} "
              f"kl_l={stats['limiter/approx_kl']:.4f} "
              f"kl_f={stats['finisher/approx_kl']:.4f} "
              f"ev={stats['critic/explained_var']:.2f} sps={sps:.1f}")

        if upd % eval_every == 0 or upd == n_updates:
            ev = runner.evaluate(eval_eps)
            margin = ev["return_mean"] - base_best
            point = {"step": runner.env_steps, **ev, "dod_margin": margin}
            if ippo_ref:
                point["vs_ippo"] = ev["return_mean"] - ippo_ref["mean"]
            if mappo_ref:
                point["vs_mappo"] = ev["return_mean"] - mappo_ref["mean"]
            eval_curve.append(point)
            # best-sustained checkpoint: rolling last-3 margin (judgment
            # metric) -- keeps the best policy artifact for GIFs / warm
            # starts even if the final snapshot dips (2C run-1 seed 2).
            roll3 = float(np.mean([p["dod_margin"] for p in eval_curve[-3:]]))
            if roll3 > best3:
                best3 = roll3
                runner.save(out_dir, tag="best")
                (out_dir / "best.json").write_text(json.dumps(
                    {"step": runner.env_steps, "last3_margin": roll3,
                     "return_mean": ev["return_mean"]}))
            print(f"  [eval] return={ev['return_mean']:.3f}+-{ev['return_std']:.3f} "
                  f"captured={ev['captured_rate']:.2f} wasted={ev['wasted_mean']:.2f} "
                  f"clean={ev['clean_cross_rate']:.2f} DoD_margin={margin:+.3f}"
                  + (f" vs_ippo={point['vs_ippo']:+.3f}" if ippo_ref else ""))
            if wb:
                wb.log({f"eval/{k}": v for k, v in point.items()
                        if isinstance(v, (int, float))}, step=runner.env_steps)
            (out_dir / "eval_curve.json").write_text(json.dumps(eval_curve, indent=2))
            (out_dir / "train_curve.json").write_text(json.dumps(train_curve, indent=2))
        if upd % save_every == 0 or upd == n_updates:
            runner.save(out_dir, tag="latest")

    final = eval_curve[-1] if eval_curve else {}
    lastk = eval_curve[-3:]
    margin_last3 = (float(np.mean([p["dod_margin"] for p in lastk]))
                    if lastk else float("nan"))
    return_last3 = (float(np.mean([p["return_mean"] for p in lastk]))
                    if lastk else float("nan"))
    summary = {"seed": seed, "env_steps": runner.env_steps,
               "final_eval": final, "baselines": baselines,
               "dod_margin": final.get("dod_margin", float("nan")),
               "dod_margin_last3": margin_last3,
               "return_mean_last3": return_last3}
    if ippo_ref:
        summary["ippo_ref_mean_last3"] = ippo_ref["mean"]
        summary["vs_ippo_last3"] = return_last3 - ippo_ref["mean"]
    if mappo_ref:
        summary["mappo_ref_mean_last3"] = mappo_ref["mean"]
        summary["vs_mappo_last3"] = return_last3 - mappo_ref["mean"]
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    maybe_plot(eval_curve, baselines, ippo_ref, out_dir)
    if wb:
        wb.summary["dod_margin_last3"] = margin_last3
        wb.summary["return_mean_last3"] = return_last3
        if ippo_ref:
            wb.summary["vs_ippo_last3"] = summary["vs_ippo_last3"]
        wb.finish()
    return summary


def maybe_plot(eval_curve: list, baselines: dict, ippo_ref: Optional[dict],
               out_dir: pathlib.Path) -> None:
    if not eval_curve:
        return
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    steps = [p["step"] for p in eval_curve]
    ax.plot(steps, [p["return_mean"] for p in eval_curve], marker="o",
            label="MAPPO (deterministic eval)")
    for name, v in baselines.items():
        ax.axhline(v["return_mean"], linestyle="--", alpha=0.7, label=name)
    if ippo_ref:
        ax.axhline(ippo_ref["mean"], linestyle=":", alpha=0.9, color="k",
                   label="IPPO (2B, mean last3)")
    ax.set_xlabel("env steps")
    ax.set_ylabel("eval return (J sum, nominal env)")
    ax.set_title("Phase 2C MAPPO vs baselines / 2B IPPO")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "eval_curves.png", dpi=120)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description="Phase 2C MAPPO trainer (shepherd env)")
    ap.add_argument("--config", default="configs/l2_mappo.yaml")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--seeds", type=int, nargs="+", default=None)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--output", default="results/mappo")
    ap.add_argument("--total-env-steps", type=int, default=None)
    ap.add_argument("--eval-episodes", type=int, default=None)
    ap.add_argument("--no-wandb", action="store_true")
    ap.add_argument("--no-randomize", action="store_true")
    args = ap.parse_args()

    run_cfg = yaml.safe_load(open(pathlib.Path(args.config)))
    env_cfg = yaml.safe_load(open(pathlib.Path(run_cfg["env_config"])))
    if args.total_env_steps is not None:
        run_cfg["loop"]["total_env_steps"] = args.total_env_steps
    if args.eval_episodes is not None:
        run_cfg["loop"]["eval_episodes"] = args.eval_episodes
    if args.no_randomize and run_cfg.get("randomize"):
        run_cfg["randomize"]["enabled"] = False
    use_wandb = (not args.no_wandb) and bool(
        run_cfg.get("wandb", {}).get("enabled", True))

    seeds = args.seeds if args.seeds is not None else [args.seed]
    out_root = pathlib.Path(args.output)
    results = [run_one(run_cfg, env_cfg, s, args.device, out_root, use_wandb)
               for s in seeds]

    print("\n=== summary (last-3-eval mean; 2C DoD: >=IPPO / 2D DoD: >=MAPPO) ===")
    for res in results:
        vs_i = res.get("vs_ippo_last3")
        vs_m = res.get("vs_mappo_last3")
        print(f"  seed {res['seed']}: last3_return={res['return_mean_last3']:.3f} "
              f"last3_margin={res['dod_margin_last3']:+.3f}"
              + (f" vs_ippo={vs_i:+.3f}" if vs_i is not None else "")
              + (f" vs_mappo={vs_m:+.3f}" if vs_m is not None else ""))


if __name__ == "__main__":
    main()
