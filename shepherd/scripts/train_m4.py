"""M4 재학습 러너 — 모드 전환 방어 시스템 (docs/32 [D] 배선).

환경 조립은 **torch-free** `shepherd/m4_env.py` 에 있다. 이 파일은 학습기와 CLI 뿐이다.
`MAPPORunner` 를 상속해 재사용한다 (복사 금지 -- 드리프트 방지).

행동 공간은 **변경 없다** -- limiter Box(4) idx 3 이 곧 커밋 비트다(docs/29 §3.1).
동결 env 는 그 차원을 무시하고 `ModeSystemEnv` 가 읽는다.

왜 위협 랜덤화가 필수인가 (docs/40 §8.2)
----------------------------------------
고정 운용점(a_att=30)은 명제 N 경계 a*=44.4 **아래**라 조향이 불필요하고,
적형성 게이트에서 hold 가 이미 전부 저지한다(조향 이득 +0.00).
브래킷 [11, 78] 이 경계를 가로질러야 두 regime 이 한 축에 들어오고 게이트가
통과한다(+0.17). **고정 운용점으로 학습을 걸면 50런을 태우고 "차이 없음"만 얻는다.**

    python -m shepherd.scripts.train_m4 --config configs/l2_mappo.yaml \\
        --seed 0 --device cpu --output results/m4_run1 --w-kill 0.5

DoD 는 return 비교가 아니라 **2층 임무 지표**다(docs/29 §4):
1차 = 무력화율(침투 저지를 SPENT_FAIL/TRUNCATED 와 분리), 2차 = 비손실 비율.
그리고 **regime 별로 쪼개서** 본다 -- 그게 "위협의 함수로 중재한다"의 증거다.
"""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Dict, List, Optional

import numpy as np
import torch

from shepherd.agents.attacker_ladder import AttackerSpec, LAMBDA_PRESETS
from shepherd.env_sys import RewardSpec, SystemSpec
from shepherd.m4_config import (M4_OVERRIDES, TAU_DECOMPOSITION, THREAT_BRACKET,
                                m4_config)
from shepherd.m4_env import build_m4_env, mission_eval, regime_of
from shepherd.train.make_env import pad_env_action
from shepherd.scripts.curve_sweep import BANDS, summarize_bands
from shepherd.spawn_rand import SpawnSpec
from shepherd.train.adapter import ShepherdAdapter
from shepherd.train.ippo import limiter_inputs
from shepherd.train.mappo import MAPPOConfig, MAPPORollout, MAPPOTrainer
from shepherd.train.obs_norm import RunningNorm
from shepherd.scripts.train_mappo import MAPPORunner
from shepherd.scripts.train_ippo import seed_everything

__all__ = ["M4Runner", "build_specs", "main"]


class M4Runner(MAPPORunner):
    """MAPPORunner + M4 스택.

    부모 `__init__` 은 `make_train_env(env_cfg)` 로 obs_dim 을 재는데, M4 는
    관측이 위협 2차원만큼 넓다. 부모를 호출하면 액터/크리틱이 **잘못된 폭**으로
    생성되므로 초기화를 여기서 다시 쓴다(부모 로직과 1:1 대응, 환경만 M4 스택).
    나머지 메서드(collect_rollout / update / rolling / learned_bundle)는 상속.
    """

    def __init__(self, run_cfg: dict, seed: int, device: str, *,
                 system: SystemSpec, reward: RewardSpec, attacker: AttackerSpec,
                 spawn: SpawnSpec, randomize_threat: bool = True,
                 threat_obs: bool = True):
        self._m4 = dict(system=system, reward=reward, attacker=attacker,
                        spawn=spawn, randomize_threat=randomize_threat,
                        threat_obs=threat_obs)
        self.env_cfg = m4_config()
        loop = run_cfg["loop"]
        self.rollout_env_steps = int(loop["rollout_env_steps"])
        self.seed = int(seed)

        st = build_m4_env(seed, 0, **self._m4)              # <-- M4 스택으로 dim 산출
        ad = ShepherdAdapter(st.env)
        self.n = len(ad.limiter_ids)
        self.obs_dim = ad.obs_dim
        lim_low, lim_high = ad.action_bounds(ad.limiter_ids[0])
        fin_low, fin_high = ad.action_bounds(ad.finisher_id)
        if not (np.allclose(lim_low, -lim_high) and np.allclose(fin_low[:3], -fin_high[:3])):
            raise ValueError("action Boxes are expected symmetric for [-1,1] scaling")
        self.lim_scale = lim_high.astype(np.float32)
        self.fin_axis_scale = fin_high[:3].astype(np.float32)

        self.norm = RunningNorm(self.obs_dim)
        cfg = MAPPOConfig.from_dict({**run_cfg["mappo"], "seed": seed,
                                     "device": device,
                                     "rollout_steps": self.rollout_env_steps,
                                     "total_timesteps": int(loop["total_env_steps"])})
        self.tr = MAPPOTrainer(self.obs_dim, self.n, cfg)
        self.buf = MAPPORollout(self.rollout_env_steps, self.obs_dim, self.n)

        self.rand_cfg = None                    # 위협 랜덤화는 m4_config 가 담당
        self.rand_rng = np.random.default_rng(seed * 9973 + 17)
        self.base_seed = seed * 1_000_003 + 1
        self.eval_seed0 = seed * 1_000_003 + 500_000

        self.env_steps = 0
        self.ep_records: List[dict] = []
        self._ep_idx = 0
        self._adapter: Optional[ShepherdAdapter] = None
        self._obs: Optional[np.ndarray] = None
        self._ep: Dict[str, float] = {}
        self._threat_log: List[dict] = []
        self._ep_env = None

    # --------------------------------------------------------------- 에피소드 ---
    def _begin_episode(self) -> None:
        st = build_m4_env(self.seed, self._ep_idx, **self._m4)
        self._adapter = ShepherdAdapter(st.env)
        obs_d, _ = self._adapter.reset(seed=self.base_seed + self._ep_idx)
        self._obs = obs_d[self._adapter.limiter_ids[0]]
        self._ep = {"ret": 0.0, "headline": 0.0, "limiter_loss": 0.0,
                    "coma_sum": 0.0, "fire_events": 0.0, "steps": 0.0,
                    "clean": 0.0}
        self._ep_params = st.threat
        self._ep_env = st.env

    def _finish_episode(self, r) -> None:
        super()._finish_episode(r)
        t, env = self._ep_params, self._ep_env
        self._threat_log.append({
            "episode": self._ep_idx - 1,
            **{k: float(v) for k, v in t.items()},
            "regime": regime_of(t["a_att"], t["tau"], t["net_radius"]),
            "hard_kill": bool(getattr(env, "hard_kill", False)),
            "n_committed": len(getattr(env, "commits", [])),
            "veto_events": int(getattr(env, "veto_events", 0)),
        })
        if len(self._threat_log) > 2000:
            del self._threat_log[:-2000]

    # ------------------------------------------------------------------ 지표 ---
    def regime_split(self, k: int = 200) -> Dict[str, float]:
        """★ regime 별 분해 — §6 의 핵심 표.

        위협이 명제 N 경계를 가로지르므로, **두 regime 에서 다르게 행동하는가**가
        "위협의 함수로 모드를 중재한다"는 주장의 직접 증거다.
        """
        recs, eps = self._threat_log[-k:], self.ep_records[-k:]
        m = min(len(recs), len(eps))
        if m == 0:
            return {}
        recs, eps = recs[-m:], eps[-m:]
        out: Dict[str, float] = {}
        for reg, tag in (("FREE_CAPTURE", "free"), ("SHAPING_NEEDED", "shape")):
            idx = [i for i, t in enumerate(recs) if t["regime"] == reg]
            if not idx:
                continue
            out[f"regime/{tag}/n"] = float(len(idx))
            out[f"regime/{tag}/captured"] = float(np.mean([eps[i]["captured"] for i in idx]))
            out[f"regime/{tag}/penetrated"] = float(np.mean([eps[i]["penetrated"] for i in idx]))
            out[f"regime/{tag}/hard_kill"] = float(np.mean([recs[i]["hard_kill"] for i in idx]))
            out[f"regime/{tag}/limiter_loss"] = float(
                np.mean([eps[i]["limiter_loss_sum"] for i in idx]))
            out[f"regime/{tag}/fire_events"] = float(
                np.mean([eps[i]["fire_events"] for i in idx]))
        return out

    # ------------------------------------------------------------------ 평가 ---
    def _bundle(self, deterministic: bool):
        """`learned_bundle` 의 M4 판 -- 표본추출/결정론을 고를 수 있다.

        부모(`train_mappo.learned_bundle`)는 `deterministic=True` 로 고정돼 있다.
        M4 는 **표본추출**로 평가한다 -- 아래 `evaluate` 의 설명 참조.
        """
        dev = self.tr.device

        def lim_fn(obs, flags):
            nobs = self.norm.normalize(obs)
            t = torch.as_tensor(limiter_inputs(nobs, self.n), device=dev)
            raw, _ = self.tr.lim_actor.act(t, deterministic=deterministic)
            return (np.clip(raw.cpu().numpy(), -1.0, 1.0)
                    * self.lim_scale).astype(np.float32)

        def fin_fn(obs, flags):
            nobs = self.norm.normalize(obs)
            t = torch.as_tensor(nobs[None, :], device=dev)
            raw, _ = self.tr.fin_actor.act(t, deterministic=deterministic)
            raw = raw[0].cpu().numpy()
            axis = np.clip(raw[:3], -1.0, 1.0) * self.fin_axis_scale
            return np.concatenate([axis, raw[3:]]).astype(np.float32)

        return lim_fn, fin_fn

    def policy_fn(self, deterministic: bool = False):
        """`mission_rollout.run_episode(policy=...)` 규약의 콜러블.

        ★ 2026-08-03 결함 1 수정 -- **`pad_env_action` 을 여기서 건다.**
        정책 출력은 LIVE 차원(limiter 3, finisher 4)이고 env Box 는 각각 4·5 다.
        학습 롤아웃은 `adapter.step` 이 패딩을 걸지만(adapter.py:90) 평가 경로인
        `run_episode(policy=...)` 는 안 걸었다. 그 결과 finisher 의 발사 비트가
        env idx4(진짜 자리) 대신 idx3(예약 slew)으로 들어가 **발사가 env 에 한 번도
        닿지 않았다.** 파일럿 3런의 최종 평가가 전부 `무력화 0.000 / 침투 1.000 /
        SPENT_FAIL 0` 이었던 이유이고, 패딩을 걸자 같은 체크포인트가 0.110 이 됐다.
        P46 이 이 줄을 지킨다.
        """
        lim_fn, fin_fn = self._bundle(deterministic)
        ids = None

        def policy(obs, flags):
            nonlocal ids
            if ids is None:
                # 갓 복원한 러너는 `_adapter` 가 None 이다 (`restore` 가 비운다).
                # 롤아웃 없이 평가만 하는 경우가 있으므로 여기서 게으르게 만든다.
                if self._adapter is None:
                    self._adapter = ShepherdAdapter(
                        build_m4_env(self.eval_seed0, 0, **self._m4).env)
                ids = (self._adapter.limiter_ids, self._adapter.finisher_id)
            lim = lim_fn(obs, flags)
            acts = {lid: np.asarray(lim[i], np.float32)
                    for i, lid in enumerate(ids[0])}
            acts[ids[1]] = np.asarray(fin_fn(obs, flags), np.float32)
            return {aid: pad_env_action(aid, a) for aid, a in acts.items()}
        return policy

    def evaluate(self, episodes: int,
                 records: Optional[list] = None) -> dict:     # 부모 시그니처 유지
        """★ 2026-08-03 평가 프로토콜 선언 -- **고정 시드 표본추출**. 결과 보기 전.

        종전에는 `deterministic=True` 였고, 그건 이진 행동을 `probs > 0.5` 로 잘랐다
        (mappo.py:177). 발사·커밋은 **에피소드당 한 번** 하는 행동이라 올바른 정책일수록
        스텝당 확률이 낮다 -- 0.5 문턱은 그런 정책을 구조적으로 버린다. 실제로 파일럿
        s1 은 p = 0.0002 를 배웠고 결정론 평가는 한 발도 안 쐈다.

        그래서 **학습과 같은 분포(표본추출)** 로 평가하되, `torch.manual_seed` 를
        평가마다 고정해 재현성을 지킨다. 판정식(docs/47 §4.3)은 바꾸지 않는다 --
        무엇을 성공으로 세는지가 아니라 정책을 어떻게 행동으로 바꾸는지의 문제다.
        P47 이 재현성을 지킨다.
        """
        torch.manual_seed(self.eval_seed0)
        return mission_eval(self.eval_seed0, episodes, policy=self.policy_fn(),
                            records=records, **self._m4)

    def save(self, out_dir: pathlib.Path, tag: str = "latest") -> None:
        super().save(out_dir, tag)
        (out_dir / f"threat_log_{tag}.json").write_text(
            json.dumps(self._threat_log[-2000:]))

    # ------------------------------------------------------------ 재개 ---
    def restore(self, out_dir: pathlib.Path, tag: str = "latest") -> int:
        """체크포인트에서 이어서 학습한다. 완료 스텝 수를 돌려준다.

        WHY: 1 런이 ~24 시간이고 스윕이 40~50 런이다. 무재개로 돌리면 죽은 런은
        통째로 날아간다 (3일짜리 서버 작업의 단일 실패점). `MAPPOTrainer.load` 는
        이미 있었고 학습기만 그것을 안 쓰고 있었다.

        **재개는 비트 동일 재현이 아니다** -- 롤아웃 RNG 스트림이 이어지지 않는다.
        그래서 재개된 런은 `summary.json` 에 `resumed_from` 을 남겨 결과 해석 시
        구분할 수 있게 한다. 판정 지표(최종 평가)는 정책만 보므로 영향이 없다.
        """
        ck = out_dir / f"ckpt_mappo_{tag}.pt"
        st = out_dir / f"run_state_{tag}.json"
        if not (ck.exists() and st.exists()):
            return 0
        self.tr = MAPPOTrainer.load(str(ck), map_location=self.tr.cfg.device)
        nz = out_dir / f"obs_norm_{tag}.json"
        if nz.exists():
            self.norm.load_state_dict(json.loads(nz.read_text()))
        rs = json.loads(st.read_text())
        self.env_steps = int(rs.get("env_steps", 0))
        self._ep_idx = int(rs.get("episodes", 0))
        tl = out_dir / f"threat_log_{tag}.json"
        if tl.exists():
            try:
                self._threat_log = json.loads(tl.read_text())
            except Exception:                                  # pragma: no cover
                pass
        self._adapter, self._obs = None, None                  # 다음 롤아웃에서 재조립
        return self.env_steps


# ------------------------------------------------------------------- CLI ---
def build_specs(args) -> Dict[str, object]:
    lam = LAMBDA_PRESETS[args.lam]
    dflt = SystemSpec()
    _or = lambda v, d: d if v is None else v          # noqa: E731
    return dict(
        system=SystemSpec(tau_kill=_or(args.tau_kill, dflt.tau_kill),
                          p_kill=_or(args.p_kill, dflt.p_kill),
                          r_nk=_or(args.r_nk, dflt.r_nk), enabled=True),
        reward=RewardSpec(w_kill=args.w_kill,
                          terminal_scale=_or(args.terminal_scale,
                                             RewardSpec().terminal_scale),
                          enabled=True),
        attacker=AttackerSpec(level=args.attacker, lam_gain=lam[0], lam_range=lam[1],
                              jink_amp=args.jink_amp, seed=args.seed,
                              label=f"{args.attacker}/{args.lam}"),
        spawn=SpawnSpec(),
    )


def _add_args(ap):
    ap.add_argument("--config", default="configs/l2_mappo.yaml")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--seeds", type=int, nargs="+", default=None)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--output", default="results/m4")
    ap.add_argument("--total-env-steps", type=int, default=None)
    ap.add_argument("--eval-episodes", type=int, default=None,
                    help="학습 곡선용 (저비용). 판정용이 아니다")
    ap.add_argument("--final-eval-episodes", type=int, default=300,
                    help="★ 판정용 최종 평가. docs/47 §4.3: 1차 지표는 SHAPING_NEEDED "
                         "영역의 무력화율이고 hold 기저는 0/122 이다. 그 영역에서 "
                         "Δ=0.05 를 80%% 검정력으로 잡으려면 in-regime 150 판이 필요하고, "
                         "shape 가 draw 의 61%% 이므로 300 판이면 약 183 판이 든다. "
                         "곡선용 20 판은 반폭 ±0.175 라 판정에 쓸 수 없다.")
    ap.add_argument("--w-kill", type=float, default=0.5, help="선언된 sweep 축")
    # ★ 아래 셋의 기본값은 **하드코딩하지 않는다.** 선언은 SystemSpec 한 군데뿐이고
    #   CLI 가 그것을 그림자처럼 복제하면 조용히 갈라진다. 실제로 갈라져 있었다:
    #   `--tau-kill` 기본이 0.1 이라 docs/42 에서 0.15 로 재선언한 값을 덮어쓰고
    #   있었다(2026-08-01 발견). None -> 선언값 사용. P40 이 이 대응을 강제한다.
    ap.add_argument("--p-kill", type=float, default=None)
    ap.add_argument("--r-nk", type=float, default=None)
    ap.add_argument("--tau-kill", type=float, default=None,
                    help=f"선언값 {SystemSpec().tau_kill} (sweep 축 {{0.15, 0.20}})")
    ap.add_argument("--terminal-scale", type=float, default=None,
                    help=f"선언값 {RewardSpec().terminal_scale} (env_sys.RewardSpec). "
                         "[E] 스케일 스모크 실측(2026-07-29): sum|dense| 평균 1.00, "
                         "|TERMINAL| 최대 1.0 -> 같은 자릿수. scale_smoke.py 참조")
    ap.add_argument("--attacker", default="A2", choices=["A1", "A2", "A3"])
    ap.add_argument("--lam", default="LAM_REF", choices=list(LAMBDA_PRESETS))
    ap.add_argument("--jink-amp", type=float, default=0.6)
    ap.add_argument("--no-threat-randomization", action="store_true",
                    help="★ 적형성 게이트 미통과 조건. 진단용 (docs/40 §8.2)")
    ap.add_argument("--no-threat-obs", action="store_true",
                    help="regime-blind ablation (§6 대조군)")
    ap.add_argument("--resume", action="store_true",
                    help="출력 디렉터리에 체크포인트가 있으면 이어서 학습한다. "
                         "스윕(40~50런 x 24h)에서 죽은 런을 통째로 잃지 않기 위한 것. "
                         "재개된 런은 summary.json 의 resumed_from 으로 표시된다.")
    return ap


def build_parser_defaults():
    """인자 없이 파싱한 기본 args. P40(선언값 그림자 금지) 검정용."""
    return _add_args(argparse.ArgumentParser()).parse_args([])


def main(argv=None) -> None:
    import yaml
    ap = _add_args(argparse.ArgumentParser(description="M4 모드 전환 방어 시스템 학습"))
    args = ap.parse_args(argv)

    if args.no_threat_randomization:
        print("[경고] 위협 랜덤화 OFF -- 고정 운용점은 적형성 게이트를 통과하지 "
              "못한다(hold 가 이미 전부 저지). 진단용으로만. docs/40 §8.2")

    run_cfg = yaml.safe_load(open(pathlib.Path(args.config)))
    if args.total_env_steps is not None:
        run_cfg["loop"]["total_env_steps"] = args.total_env_steps
    if args.eval_episodes is not None:
        run_cfg["loop"]["eval_episodes"] = args.eval_episodes

    tau = M4_OVERRIDES["physics.tau_deploy"]
    rho = m4_config()["physics"]["net_radius"]
    a_star = 2 * rho / tau ** 2
    lo, hi = THREAT_BRACKET["physics.a_att_max"]
    print(f"[M4] tau = {tau} = " +
          " + ".join(f"{k}({v[0]})" for k, v in TAU_DECOMPOSITION.items()))
    print(f"[M4] 명제 N 경계 a* = {a_star:.1f} m/s^2, 브래킷 [{lo:g}, {hi:g}] -> "
          f"{'가로지름 OK' if lo < a_star < hi else '★ 안 가로지름 -- 게이트 재확인'}")
    print(f"[M4] w_kill={args.w_kill} 공격자={args.attacker}/{args.lam} "
          f"위협랜덤화={'OFF' if args.no_threat_randomization else 'ON'} "
          f"위협관측={'OFF' if args.no_threat_obs else 'ON'}")

    specs = build_specs(args)
    seeds = args.seeds if args.seeds is not None else [args.seed]
    out_root = pathlib.Path(args.output)
    eval_every = int(run_cfg["loop"]["eval_interval_updates"])
    eval_eps = int(run_cfg["loop"]["eval_episodes"])

    for s in seeds:
        seed_everything(s)
        runner = M4Runner(run_cfg, s, args.device,
                          randomize_threat=not args.no_threat_randomization,
                          threat_obs=not args.no_threat_obs, **specs)
        out_dir = out_root / f"seed{s}"
        out_dir.mkdir(parents=True, exist_ok=True)
        n_upd = max(1, int(run_cfg["loop"]["total_env_steps"]) // runner.rollout_env_steps)
        curve = []
        resumed_from = 0
        upd0 = 0
        if args.resume:
            resumed_from = runner.restore(out_dir)
            if resumed_from:
                upd0 = min(resumed_from // runner.rollout_env_steps, n_upd)
                cf = out_dir / "mission_curve.json"
                if cf.exists():
                    try:
                        curve = json.loads(cf.read_text())
                    except Exception:                          # pragma: no cover
                        curve = []
                print(f"[seed {s}] 재개: step={resumed_from} (upd {upd0}/{n_upd})")
            else:
                print(f"[seed {s}] 재개할 체크포인트 없음 -- 처음부터")
        if upd0 >= n_upd:
            print(f"[seed {s}] 이미 완료됨 (upd {upd0}/{n_upd}) -- 최종 평가만 수행")
        for upd in range(upd0 + 1, n_upd + 1):
            runner.collect_rollout()
            stats = runner.update()
            if upd % eval_every == 0 or upd == n_upd:
                roll, reg = runner.rolling(), runner.regime_split()
                ev = runner.evaluate(eval_eps)
                curve.append({"step": runner.env_steps, **ev, **reg})
                print(f"[seed {s}] upd {upd}/{n_upd} step={runner.env_steps} "
                      f"ret={roll.get('train/ep_return', float('nan')):.3f} "
                      f"| 무력화 {ev['neutralized_rate']:.2f} "
                      f"침투 {ev['penetrated_rate']:.2f} "
                      f"비손실 {ev['nondestructive_frac']:.2f} "
                      f"| free_cap {reg.get('regime/free/captured', float('nan')):.2f} "
                      f"shape_cap {reg.get('regime/shape/captured', float('nan')):.2f} "
                      f"shape_hk {reg.get('regime/shape/hard_kill', float('nan')):.2f}")
                runner.save(out_dir)
                (out_dir / "mission_curve.json").write_text(json.dumps(curve, indent=2))
        runner.save(out_dir, tag="final")
        # ★ 판정용 최종 평가는 곡선용과 **분리**한다 (docs/47 §4.3).
        final_recs: list = []
        final_eval = runner.evaluate(int(args.final_eval_episodes),
                                     records=final_recs)
        # ★ 세 칸 집계 (docs/47 §4.4). **결과를 보기 전에 선언된 보고 축**이고
        #   1차 판정식에는 들어가지 않는다. 여기서 같이 안 뽑으면 스윕이 끝난 뒤
        #   다시 돌려야 하고, 그러면 결과를 본 뒤 축을 만드는 모양이 된다.
        final_bands = summarize_bands(final_recs)
        print(f"[seed {s}] 최종평가 n={args.final_eval_episodes} "
              f"무력화 {final_eval['neutralized_rate']:.3f} "
              f"| shape " + ", ".join(
                  f"{k}={v['neutralized_rate']:.3f}(n={v['n']})"
                  for k, v in sorted(final_eval.get("by_regime", {}).items())))
        print("[seed %d] 밴드 " % s + "  ".join(
            f"{b}: 네트 {final_bands[b]['net_capture']['p']:.3f} / "
            f"무력화 {final_bands[b]['neutralized']['p']:.3f} (n={final_bands[b]['n']})"
            for b in BANDS))
        (out_dir / "summary.json").write_text(json.dumps({
            "seed": s, "w_kill": args.w_kill, "attacker": args.attacker,
            "threat_randomized": not args.no_threat_randomization,
            "threat_obs": not args.no_threat_obs,
            "final": curve[-1] if curve else None,
            "final_eval_episodes": int(args.final_eval_episodes),
            "resumed_from": int(resumed_from),
            "final_eval": final_eval,
            "final_eval_bands": final_bands}, indent=2))


if __name__ == "__main__":
    main()
