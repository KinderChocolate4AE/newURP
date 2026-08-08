"""IID 대역 paired 평가 러너 — headline + docs/71 ablation **공용 구현**.

    # scripted 팔 (torch 불요, 로컬 가능)
    python -m shepherd.scripts.eval_iid --arm hold --episode-start 10300 --episodes 300 \\
        --out results/iid_abl/hold.json
    # 학습 정책 팔 (서버, torch)
    python -m shepherd.scripts.eval_iid --arm ls-live --training-seed 1 \\
        --policy-checkpoint results/m4_v3_train_LS/seed1 \\
        --episode-start 10300 --episodes 300 --out results/iid_abl/ls-live_seed1.json
    python -m shepherd.scripts.eval_iid --arm ls-off --training-seed 1 \\
        --config configs/l2_mappo_nocommit.yaml \\
        --policy-checkpoint results/m4_v3_train_LS_off/seed1 \\
        --episode-start 10300 --episodes 300 --out results/iid_abl/ls-off_seed1.json

규약 (결과 전 잠금 — docs/71 §1.1)
----------------------------------
**training seed 는 policy replication 을 식별하고, IID episode id 는 world
replication 을 식별한다. 두 축은 독립이며 같은 episode id 는 모든 arm x
training-seed 평가에서 bit-identical world draw 를 만든다.**

  world  = `build_m4_env(EVAL_WORLD_SEED=0, ep, threat_layer="iid")`
           + `run_episode(seed=ep)`   -- arm/training seed 와 무관
  policy = (arm, training_seed) -- ckpt 에서만 들어온다
  band   = ABLATION 10300..10599 | HEADLINE 10000..10299 **둘 중 하나만**
           (선언 안 된 대역은 거부 -- 새 대역을 즉흥으로 열지 못하게)
  regime = **rollout 전에** world spec 에서 결정 (pre-treatment, docs/71 §0.1③).
           `regime_of` 는 (a_att, tau, net_radius) 의 순함수라 controller·
           policy·궤적과 무관하다. rollout 결과로 다시 계산하지 않는다.
  policy 표본추출 RNG = `torch.manual_seed(POLICY_RNG_BASE + ep)` (에피소드별
           재시드 -- 평가는 표본추출이다, docs/47. 같은 ep 에서 모든 팔이 같은
           스트림에서 출발한다)

산출 JSON 은 provenance 를 자체 포함한다 (arm / training_seed /
action_profile / eval_layer / episode_start·end / distribution_hash /
world_contract_hash / train_contract_hash / checkpoint_hash / world_hash 열).
`analyze_ls_commit.py` 가 이 파일들만 읽고 primary 를 낸다.

torch-free (학습 정책 팔에서만 torch 를 늦게 import).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
from dataclasses import asdict, is_dataclass
from typing import Optional

from shepherd.env_sys import RewardSpec, ratified_system
from shepherd.m4_env import build_m4_env, label_rates, regime_of
from shepherd.notify import ntfy
from shepherd.scale_v2 import draw_threat_v3, v3_distribution_hash
from shepherd.scripts.dump_ls_trajectory import ARC_KW      # docs/63 §7 SELECTED c5
from shepherd.scripts.mission_rollout import LABELS, run_episode

__all__ = ["BANDS", "EVAL_WORLD_SEED", "POLICY_RNG_BASE", "SCRIPTED_ARMS",
           "POLICY_ARMS", "world_kw", "world_hash", "eval_episodes", "run_band"]

# ── 결과 전 잠금 상수 ────────────────────────────────────────────────────────
EVAL_WORLD_SEED = 0          # world namespace. policy training seed 와 독립이다
EVAL_LAYER = "iid"           # 이 러너는 IID 전용 (train 대역 평가는 학습기 몫)
POLICY_RNG_BASE = 700_000_000    # torch 표본추출 시드 base (학습 namespace 와 분리)
BANDS = {                    # 이름 -> (episode_start, n). 그 외 대역은 거부한다
    "headline": (10_000, 300),      # docs/63 headline (이미 열람됨)
    "ablation": (10_300, 300),      # docs/71 §1.1 신설 (LS-off 결과 전 동결)
}
SCRIPTED_ARMS = {                   # arm -> run_episode kwargs
    "hold": dict(limiter_mode="hold", fire_mode="clean"),
    "arc": dict(limiter_mode="arc", fire_mode="clean", limiter_kw=dict(ARC_KW)),
}
POLICY_ARMS = {                     # arm -> 기대 limiter_commit (config 혼동 방지)
    "ls-live": True,
    "ls-off": False,
}


def _git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       text=True).strip()
    except Exception:                                        # pragma: no cover
        return "unknown"


def _band_of(ep0: int, n: int) -> str:
    for name, (s, k) in BANDS.items():
        if (ep0, n) == (s, k):
            return name
    raise SystemExit(
        f"선언되지 않은 평가 대역이다: start={ep0} n={n}. 허용 = "
        + " / ".join(f"{k}: {v[0]}..{v[0] + v[1] - 1}" for k, v in BANDS.items())
        + " (docs/71 §1.1 -- 새 대역은 사전등록 없이 열지 않는다)")


def world_kw() -> dict:
    """평가 world 구성. MARL 학습과 같은 비준 계약, layer 만 IID."""
    return dict(system=ratified_system(),
                reward=RewardSpec(w_kill=0.5, enabled=True),
                threat_layer=EVAL_LAYER)


def world_hash(ep: int, st=None) -> str:
    """이 episode id 의 **world 정체성** 해시 (arm/seed 비의존).

    두 산출 파일의 같은 행이 같은 world 였는지 사후에 증명하는 열이다 --
    contract hash 는 분포 참조(layer + distribution hash)까지만 보므로
    에피소드별 draw 가 섞였는지는 잡지 못한다.
    """
    d = draw_threat_v3(EVAL_WORLD_SEED, ep, EVAL_LAYER)
    if st is None:                       # 러너는 이미 만든 스택을 넘긴다 (재조립 방지)
        st = build_m4_env(EVAL_WORLD_SEED, ep, **world_kw())
    payload = {
        "episode": int(ep), "layer": EVAL_LAYER, "seed": EVAL_WORLD_SEED,
        "threat": {k: round(float(v), 9) for k, v in sorted(st.threat.items())},
        "cell": list(d["cell"]),
        **{k: (asdict(d[k]) if is_dataclass(d[k]) else d[k])
           for k in ("attacker", "spawn", "standby")},
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True,
                                     default=str).encode()).hexdigest()[:16]


def _policy_runner(config: str, ckpt: str, training_seed: int, device: str,
                   tag: str = "final"):
    """학습 ckpt -> (policy callable, meta). 세계는 **학습 계약**으로 조립한다.

    ckpt 의 contract hash 는 TRAIN layer 세계의 것이므로 러너도 train layer 로
    만들어야 `restore` 가 통과한다 (docs/65 A5). 평가 world 는 이 러너가 아니라
    아래 `run_band` 가 IID layer 로 따로 만든다 -- 그게 두 축 분리의 실체다.
    """
    import torch
    import yaml

    from shepherd.scripts.train_m4 import (M4Runner, build_parser_defaults,
                                           build_specs)
    run_cfg = yaml.safe_load(open(config))
    specs = build_specs(build_parser_defaults())
    specs.update(attacker=None, spawn=None)          # layer draw 가 구성한다
    runner = M4Runner(run_cfg, int(training_seed), device, threat_layer="train",
                      finisher_policy="scripted", **specs)
    # tag 기본 "final" = 판정용. "latest" 는 **학습 중간** 체크포인트로 평가
    # 경로를 미리 깨보는 스모크 전용이다 (산출물에 ckpt_tag 로 남는다).
    steps = runner.restore(pathlib.Path(ckpt), tag=tag)
    if steps <= 0:
        raise SystemExit(f"체크포인트 복원 실패 (tag={tag}): {ckpt}")
    ck = pathlib.Path(ckpt) / f"ckpt_mappo_{tag}.pt"
    meta = dict(
        action_profile=("accel3+commit" if runner.limiter_commit else "accel3"),
        limiter_commit=bool(runner.limiter_commit),
        train_contract_hash=runner.contract["hash"],
        checkpoint_hash=hashlib.sha256(ck.read_bytes()).hexdigest()[:16],
        checkpoint_steps=int(steps), ckpt_tag=tag,
        arm_role=runner.arm)
    return runner, meta, torch


def eval_episodes(eps, *, policy=None, scripted_roles=(), ep_kw=None,
                  torch=None, arm: str = "", log=print):
    """에피소드 목록을 굴려 (rows, world_contract) 를 낸다.

    `run_band` 가 대역 가드를 통과한 뒤 부르는 알맹이 -- 테스트는 2~3 판만
    굴려 pairing/regime 계약을 검사할 수 있다 (300 판 대역을 강제하지 않는다).
    """
    ep_kw = dict(limiter_mode="hold", fire_mode="clean") if ep_kw is None else ep_kw
    rows, contract = [], None
    for ep in eps:
        st = build_m4_env(EVAL_WORLD_SEED, ep, **world_kw())
        # ★ regime 은 여기서, **rollout 전에** 결정된다 (pre-treatment).
        reg = regime_of(st.threat["a_att"], st.threat["tau"], st.threat["net_radius"])
        if contract is None:
            contract = st.contract
        if torch is not None:
            torch.manual_seed(POLICY_RNG_BASE + ep)      # 에피소드별 재시드
        r = run_episode(st.env, st.scn, st.lay, seed=ep, policy=policy,
                        scripted_roles=scripted_roles, **ep_kw)
        rows.append(dict(episode=ep, regime=reg, label=r.label,
                         world_hash=world_hash(ep, st),
                         steps=r.steps, fire_step=r.fire_step,
                         wasted=r.wasted_fire, n_contact=r.n_contact,
                         **{k: round(float(v), 6) for k, v in st.threat.items()}))
        if log:
            log(f"{arm} ep{ep}: {r.label:>19} {reg:>14} steps={r.steps:>4}",
                flush=True)
    return rows, contract


def run_band(arm: str, ep0: int, n: int, *, config: str = "configs/l2_mappo.yaml",
             ckpt: Optional[str] = None, training_seed: Optional[int] = None,
             device: str = "cpu", shard_offset: int = 0,
             shard_n: Optional[int] = None, ckpt_tag: str = "final",
             log=print) -> dict:
    """한 팔 x 한 대역(또는 그 샤드) 평가. 반환 dict 그대로 JSON 으로 쓴다.

    샤딩은 long-run 정책(서버 병렬)용이다 -- 대역 자체는 여전히 선언된 것만
    허용하고, 샤드는 그 안의 부분구간이어야 한다. 병합·완전성 검사는
    `analyze_ls_commit` 이 한다.
    """
    band = _band_of(ep0, n)
    shard_n = n if shard_n is None else int(shard_n)
    if shard_offset < 0 or shard_n <= 0 or shard_offset + shard_n > n:
        raise SystemExit(f"샤드가 대역을 벗어난다: offset={shard_offset} "
                         f"n={shard_n} (대역 {ep0}..{ep0 + n - 1})")
    eps0 = ep0 + shard_offset
    meta: dict = {}
    policy = None
    torch = None
    scripted_roles = ()
    ep_kw = dict(limiter_mode="hold", fire_mode="clean")

    if arm in POLICY_ARMS:
        if ckpt is None or training_seed is None:
            raise SystemExit(f"{arm} 은 --policy-checkpoint 와 --training-seed 필수")
        runner, meta, torch = _policy_runner(config, ckpt, training_seed,
                                             device, ckpt_tag)
        if meta["limiter_commit"] is not POLICY_ARMS[arm]:
            raise SystemExit(
                f"arm={arm} 인데 ckpt/config 의 limiter_commit="
                f"{meta['limiter_commit']} 다 -- --config 를 잘못 짚었다 "
                f"(ls-off = configs/l2_mappo_nocommit.yaml)")
        policy = runner.policy_fn()                      # 표본추출 (docs/47)
        scripted_roles = runner.frozen_roles             # ("finisher",)
        ep_kw = dict(limiter_mode=runner.limiter_mode, fire_mode=runner.fire_mode)
    elif arm in SCRIPTED_ARMS:
        ep_kw = dict(SCRIPTED_ARMS[arm])
        meta = dict(action_profile="scripted", limiter_commit=None)
    else:
        raise SystemExit(f"모르는 arm: {arm} "
                         f"(허용 {sorted(SCRIPTED_ARMS) + sorted(POLICY_ARMS)})")

    rows, contract = eval_episodes(range(eps0, eps0 + shard_n), policy=policy,
                                   scripted_roles=scripted_roles, ep_kw=ep_kw,
                                   torch=torch, arm=arm, log=log)
    counts = {lab: 0 for lab in LABELS}
    by_regime: dict = {}
    for row in rows:
        counts[row["label"]] += 1
        by_regime.setdefault(row["regime"],
                             {lab: 0 for lab in LABELS})[row["label"]] += 1

    return dict(
        contract_doc="docs/71 §1.1 paired IID band eval (headline + ablation 공용)",
        arm=arm, band=band, training_seed=training_seed,
        eval_layer=EVAL_LAYER, eval_world_seed=EVAL_WORLD_SEED,
        episode_start=ep0, episode_end=ep0 + n - 1, band_n=n,
        shard_offset=shard_offset, shard_n=shard_n,       # n 은 label_rates 가 낸다
        shard_complete=(shard_n == n),
        distribution_hash=v3_distribution_hash(),
        world_contract_hash=contract["hash"],
        policy_rng_base=(POLICY_RNG_BASE if torch is not None else None),
        git_head=_git_head(), **meta,
        counts=counts, **label_rates(counts),
        by_regime={k: label_rates(v) for k, v in by_regime.items()},
        rows=rows)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="IID 대역 paired 평가 (docs/71 §1.1)")
    ap.add_argument("--arm", required=True,
                    choices=sorted(SCRIPTED_ARMS) + sorted(POLICY_ARMS))
    ap.add_argument("--threat-layer", default=EVAL_LAYER, choices=[EVAL_LAYER],
                    help="IID 전용 러너 (train 대역은 학습기 final eval 몫)")
    ap.add_argument("--episode-start", type=int, required=True)
    ap.add_argument("--episodes", type=int, required=True)
    ap.add_argument("--policy-checkpoint", default=None)
    ap.add_argument("--training-seed", type=int, default=None)
    ap.add_argument("--config", default="configs/l2_mappo.yaml",
                    help="ls-off 는 configs/l2_mappo_nocommit.yaml")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--shard-offset", type=int, default=0,
                    help="대역 안 부분구간 시작 오프셋 (서버 병렬 샤딩)")
    ap.add_argument("--shard-n", type=int, default=None,
                    help="샤드 판수 (기본 = 대역 전체)")
    ap.add_argument("--ckpt-tag", default="final",
                    help="판정은 final. latest = 학습 중간 ckpt 로 평가 경로만 "
                         "깨보는 스모크 (산출물 ckpt_tag 에 기록된다)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    out = run_band(a.arm, a.episode_start, a.episodes, config=a.config,
                   ckpt=a.policy_checkpoint, training_seed=a.training_seed,
                   device=a.device, shard_offset=a.shard_offset,
                   shard_n=a.shard_n, ckpt_tag=a.ckpt_tag,
                   log=None if a.quiet else print)
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    shape = out["by_regime"].get("SHAPING_NEEDED", {})
    print(f"[{out['arm']} seed={out['training_seed']}] band={out['band']} "
          f"n={out['n']} p_net={out['p_net']:.3f} "
          f"| SHAPING p_net={shape.get('p_net', float('nan')):.3f} "
          f"(n={shape.get('n', 0)}) -> {p}")
    ntfy(f"eval_iid {out['arm']} seed={out['training_seed']} band={out['band']} "
         f"p_net={out['p_net']:.3f} shape={shape.get('p_net', float('nan')):.3f}")


if __name__ == "__main__":
    main()
