"""M4 재학습 러너 — 모드 전환 방어 시스템 (docs/32 [D] 배선).

환경 조립은 **torch-free** `shepherd/m4_env.py` 에 있다. 이 파일은 학습기와 CLI 뿐이다.
`MAPPORunner` 를 상속해 재사용한다 (복사 금지 -- 드리프트 방지).

env 행동 공간은 **변경 없다** -- limiter Box(4) idx 3 이 곧 커밋 비트다(docs/29 §3.1).
동결 env 는 그 차원을 무시하고 `ModeSystemEnv` 가 읽는다.

★ 2026-08-03 결함 2 -- 정책의 live 차원은 변경된다
--------------------------------------------------
env Box 는 그대로지만 **정책이 그 idx 3 에 값을 넣을 수 있어야** 커밋이 성립한다.
`action_dims.LIVE_DIMS` 는 M4 이전 상태로 limiter live = (0,1,2) 였고, 그래서
`pad_env_action` 이 커밋 자리에 0 을 넣고 있었다 -- 정책에게 하드킬이라는 행동이
아예 없었다(파일럿 3런 `shape_hk = 0` 의 진짜 이유. 탐색 실패가 아니다).
M4 만 `M4_LIVE_DIMS` 프로파일을 써서 limiter live = (0,1,2,3) 으로 돌리고,
학습기는 `cfg.limiter_commit=True` 로 limiter actor 를 MixedActor(연속 3 +
Bernoulli 1) 로 만든다. M2/M3 는 두 기본값을 안 건드리므로 bit-identical.
P48 이 지킨다.

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
from shepherd.m4_config import (CAPABILITY_RATIOS, M4_OVERRIDES, TAU_DECOMPOSITION,
                                THREAT_BRACKET, m4_config)
from shepherd.m4_env import build_m4_env, mission_eval, regime_of
from shepherd.scripts.mission_rollout import scripted_role_actions
from shepherd.train.make_env import (M4_LIVE_DIMS, pad_env_action,
                                     unpad_env_action)
from shepherd.scripts.curve_sweep import BANDS, summarize_bands
from shepherd.spawn_rand import SpawnSpec
from shepherd.train.adapter import ShepherdAdapter
from shepherd.train.ippo import limiter_inputs
from shepherd.train.mappo import MAPPOConfig, MAPPORollout, MAPPOTrainer
from shepherd.train.obs_norm import RunningNorm
from shepherd.scripts.train_mappo import MAPPORunner
from shepherd.scripts.train_ippo import seed_everything

__all__ = ["M4Runner", "build_specs", "main", "ARMS", "arm_of"]

# ── 역할 분리 팔 (docs/48 §2) ────────────────────────────────────────────────
#   limiter x finisher 의 2x2. SS 는 학습이 없으므로 여기 없다 -- 그 칸은
#   `sweep_m4.measure_baseline("hold")` 가 이미 n=500 으로 재 둔 기저선이다.
ARMS = {
    ("learned", "learned"):  "LL",   # 둘 다 학습 (= 파일럿 구성)
    ("learned", "scripted"): "LS",   # 학습 편대 + 해석적 발사 규칙
    ("hold",    "learned"):  "SL",   # 무개입 편대 + 학습 발사
}


def arm_of(limiter_policy: str, finisher_policy: str) -> str:
    key = (limiter_policy, finisher_policy)
    if key not in ARMS:
        raise ValueError(
            f"학습 팔이 아니다: limiter={limiter_policy} finisher={finisher_policy}. "
            f"둘 다 스크립트인 칸(SS)은 손튜닝 기준선이므로 "
            f"`python -m shepherd.scripts.sweep_m4 --baseline 500` 으로 잰다")
    return ARMS[key]


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
                 threat_obs: bool = True,
                 limiter_policy: str = "learned",
                 finisher_policy: str = "learned"):
        self._m4 = dict(system=system, reward=reward, attacker=attacker,
                        spawn=spawn, randomize_threat=randomize_threat,
                        threat_obs=threat_obs)
        # ── 역할 분리 (docs/48). 기본은 (learned, learned) = 기존 경로 ──────────
        self.arm = arm_of(limiter_policy, finisher_policy)
        self.limiter_policy = limiter_policy
        self.finisher_policy = finisher_policy
        self.frozen_roles = tuple(
            r for r, p in (("limiter", limiter_policy), ("finisher", finisher_policy))
            if p != "learned")
        # 동결된 역할이 따를 스크립트. `hold` / `clean` 은 기저선과 **같은** 규칙이고
        # 그래야 LS-SS · SL-SS 가 학습의 기여로 읽힌다 (docs/48 §3).
        self.limiter_mode = "hold" if limiter_policy == "hold" else "hold"
        self.fire_mode = "clean"
        self._prev_clean = False
        self._scn = self._lay = None
        self.env_cfg = m4_config()
        loop = run_cfg["loop"]
        self.rollout_env_steps = int(loop["rollout_env_steps"])
        self.seed = int(seed)

        st = build_m4_env(seed, 0, **self._m4)              # <-- M4 스택으로 dim 산출
        ad = ShepherdAdapter(st.env, M4_LIVE_DIMS)         # 커밋 비트 live (결함 2)
        self.n = len(ad.limiter_ids)
        self.obs_dim = ad.obs_dim
        lim_low, lim_high = ad.action_bounds(ad.limiter_ids[0])
        fin_low, fin_high = ad.action_bounds(ad.finisher_id)
        # ★ 대칭성은 **연속 차원에만** 요구한다. 이산 비트(limiter 커밋 idx 3,
        #   finisher 발사 idx 4)의 Box 는 [0, 1] 이라 -high 와 같을 수 없다.
        #   종전 코드는 limiter 전체에 대칭성을 요구했고, 커밋 차원이 live 로
        #   들어오는 순간 여기서 걸린다 (배선 없이 프로파일만 바꾸면 죽는 지점).
        if not (np.allclose(lim_low[:3], -lim_high[:3])
                and np.allclose(fin_low[:3], -fin_high[:3])):
            raise ValueError("action Boxes are expected symmetric for [-1,1] scaling")
        if not (np.isclose(lim_low[3], 0.0) and np.isclose(lim_high[3], 1.0)):
            raise ValueError(f"커밋 비트 Box 가 [0,1] 이 아니다: "
                             f"[{lim_low[3]}, {lim_high[3]}] -- env.py 와 어긋났다")
        # lim_scale = [a_max, a_max, a_max, 1.0]. 커밋 비트는 Bernoulli {0,1} 이
        # 그대로 통과해 env 의 commit_threshold=0.5 와 맞물린다.
        #
        # ★ 2026-08-03 P5 수정 — 이 값은 **에피소드 0 의 draw** 다. 그대로 두면 안 된다.
        #   `a_lim_max = 0.35 × a_att` 이고 `a_att ~ U[11, 78]` 이라 실제 권한이 매
        #   에피소드 3.86 ~ 27.28 로 바뀐다(m4_config.CAPABILITY_RATIOS). 동결하면
        #   실측 41.5% 에피소드에서 과다명령(백엔드 노름 클램프 -> radial gradient 소실),
        #   44.3% 에서 과소명령(권한의 중앙 72% 만 사용)이 된다. 더 나쁜 것은
        #   **시드마다 동결값이 달라 시드가 복제가 아니게 된다**(실효 권한 100/72/48%).
        #   `_begin_episode` 가 매 에피소드 갱신한다(아래). 여기 값은 첫 롤아웃 전
        #   부트스트랩일 뿐이다.
        self.lim_scale = lim_high.astype(np.float32)
        self.fin_axis_scale = fin_high[:3].astype(np.float32)

        self.norm = RunningNorm(self.obs_dim)
        cfg = MAPPOConfig.from_dict({**run_cfg["mappo"], "seed": seed,
                                     "device": device,
                                     "rollout_steps": self.rollout_env_steps,
                                     "total_timesteps": int(loop["total_env_steps"]),
                                     # 결함 2 (a): M4 기본은 커밋 live.
                                     # config 로 끄면 docs/29 §15.2 폴백 (b) 의
                                     # 대조군(= 커밋을 정책 손에서 뗀 팔)이 된다.
                                     "limiter_commit": bool(
                                         run_cfg["mappo"].get("limiter_commit", True)),
                                     # docs/48: 동결 역할의 액터는 학습에서 뺀다
                                     "freeze_limiter": "limiter" in self.frozen_roles,
                                     "freeze_finisher": "finisher" in self.frozen_roles})
        self.tr = MAPPOTrainer(self.obs_dim, self.n, cfg)
        self.buf = MAPPORollout(self.rollout_env_steps, self.obs_dim, self.n,
                                lim_dim=self.tr.lim_dim)

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
        self._adapter = ShepherdAdapter(st.env, M4_LIVE_DIMS)
        # ★ P5: 이 에피소드의 실제 권한으로 행동 스케일을 갱신한다 (a_lim = 0.35·a_att).
        self.lim_scale = self._adapter.action_bounds(
            self._adapter.limiter_ids[0])[1].astype(np.float32)
        obs_d, _ = self._adapter.reset(seed=self.base_seed + self._ep_idx)
        self._obs = obs_d[self._adapter.limiter_ids[0]]
        self._ep = {"ret": 0.0, "headline": 0.0, "limiter_loss": 0.0,
                    "coma_sum": 0.0, "fire_events": 0.0, "steps": 0.0,
                    "clean": 0.0}
        self._ep_params = st.threat
        self._ep_env = st.env
        self._scn, self._lay = st.scn, st.lay
        self._prev_clean = False            # 발사 트리거는 **직전 스텝**의 플래그다

    # ------------------------------------------------------- 역할 동결 훅 ---
    def _override_live(self, live, ad):
        """동결된 역할의 행동을 스크립트로 갈아끼운다 (docs/48 §3).

        스크립트는 **env Box** 를 내고 `adapter.step` 은 **LIVE** 차원을 받는다.
        그래서 `unpad_env_action` 으로 되돌린다 -- 이 변환을 여기 말고 다른 데서
        하면 프로파일(M4_LIVE_DIMS)이 갈라져 결함 2 가 재발한다. P51 이 지킨다.
        """
        if not self.frozen_roles:
            return live
        env_acts = scripted_role_actions(
            ad.env, self._scn, self._lay, roles=self.frozen_roles,
            limiter_mode=self.limiter_mode, fire_mode=self.fire_mode,
            prev_clean=self._prev_clean, baseline_commit=False)
        out = dict(live)
        for aid, a in env_acts.items():
            out[aid] = unpad_env_action(aid, a, ad.live_dims)
        return out

    def _observe_step(self, r) -> None:
        self._prev_clean = bool(r.flags.get("clean_net_threshold_crossed", False))

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
    def _lim_scale_for(self, obs) -> np.ndarray:
        """★ P5 (평가 경로) — 이 에피소드의 실제 `a_lim` 으로 행동 스케일을 만든다.

        `mission_eval` 은 에피소드마다 env 를 새로 만들지만(`m4_env.py`) 정책 콜러블은
        env 를 못 본다. 대신 **관측에 이미 실려 있는 위협 특징**을 선언된 브래킷으로
        역변환한다 (`obs_threat.threat_features` 의 역):

            x = 2·(a_att − lo)/(hi − lo) − 1   ->   a_att = lo + (x + 1)·(hi − lo)/2
            a_lim = CAPABILITY_RATIOS["physics.a_lim_max"] × a_att

        브래킷·비율은 `m4_config` 에서 **import** 한다 (P40: 선언 그림자 금지).
        위협 관측이 꺼져 있으면(`--no-threat-obs`) 역변환 근거가 없으므로 현재
        `lim_scale` 을 그대로 쓴다 -- 그 팔은 regime-blind ablation 이고 판정용이 아니다.
        P49 가 이 역변환이 env 의 실제 action Box 와 일치함을 강제한다.
        """
        if not self._m4.get("threat_obs", True):
            return self.lim_scale
        lo, hi = THREAT_BRACKET["physics.a_att_max"]
        a_att = lo + (float(np.asarray(obs).reshape(-1)[-2]) + 1.0) * (hi - lo) / 2.0
        a_lim = CAPABILITY_RATIOS["physics.a_lim_max"][1] * a_att
        s = np.array(self.lim_scale, np.float32, copy=True)
        s[:3] = np.float32(a_lim)
        return s

    def _bundle(self, deterministic: bool):
        """`learned_bundle` 의 M4 판 -- 표본추출/결정론을 고를 수 있다.

        부모(`train_mappo.learned_bundle`)는 `deterministic=True` 로 고정돼 있다.
        M4 는 **표본추출**로 평가한다 -- 아래 `evaluate` 의 설명 참조.
        """
        dev = self.tr.device

        def lim_fn(obs, flags):
            scale = self._lim_scale_for(obs)                # ★ P5 (아래 설명)
            nobs = self.norm.normalize(obs)
            t = torch.as_tensor(limiter_inputs(nobs, self.n), device=dev)
            raw, _ = self.tr.lim_actor.act(t, deterministic=deterministic)
            raw = raw.cpu().numpy()
            # 연속 3 차원만 클립. 커밋 비트(idx 3)는 {0,1} 표본이라 그대로 통과시킨다
            # -- 클립하면 값 자체는 안 변하지만 규약이 finisher 와 갈라진다.
            act = raw.copy()
            act[:, :3] = np.clip(raw[:, :3], -1.0, 1.0)
            return (act * scale).astype(np.float32)

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
                        build_m4_env(self.eval_seed0, 0, **self._m4).env,
                        M4_LIVE_DIMS)
                ids = (self._adapter.limiter_ids, self._adapter.finisher_id)
            lim = lim_fn(obs, flags)
            acts = {lid: np.asarray(lim[i], np.float32)
                    for i, lid in enumerate(ids[0])}
            acts[ids[1]] = np.asarray(fin_fn(obs, flags), np.float32)
            # ★ 패딩은 어댑터와 **같은 프로파일**로 걸어야 한다. 기본 프로파일로
            #   걸면 커밋 비트가 다시 0 으로 덮여 결함 2 가 그대로 재발한다.
            return {aid: pad_env_action(aid, a, self._adapter.live_dims)
                    for aid, a in acts.items()}
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
                            records=records, limiter_mode=self.limiter_mode,
                            fire_mode=self.fire_mode,
                            scripted_roles=self.frozen_roles, **self._m4)

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
        # ★ 결함 2 이전 체크포인트(limiter_commit 없음 -> lim_dim 3)를 커밋 배선된
        #   러너에 이어 붙이면 조용히 틀린 폭을 학습한다. 조용히 넘기지 않는다.
        if self.tr.lim_dim != self.buf.lim_dim:
            raise ValueError(
                f"체크포인트 lim_dim={self.tr.lim_dim} != 러너 {self.buf.lim_dim}. "
                f"결함 2 배선 이전 체크포인트로 보인다 -- 재개하지 말고 처음부터 돌릴 것 "
                f"(results/m4_pilot 의 파일럿 산출물은 전후 대조용으로 보존)")
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
    # ★ 역할 분리 (docs/48). 기본 (learned, learned) 은 기존 경로와 동일하다.
    ap.add_argument("--limiter-policy", default="learned", choices=["learned", "hold"],
                    help="hold = 편대를 무개입으로 동결. 기저선과 **같은** 규칙")
    ap.add_argument("--finisher-policy", default="learned",
                    choices=["learned", "scripted"],
                    help="scripted = 해석적 발사 규칙(clean 임계 교차)으로 동결. "
                         "기저선 hold 의 finisher 와 같은 규칙")
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
    print(f"[M4] 역할 팔 = {arm_of(args.limiter_policy, args.finisher_policy)} "
          f"(limiter={args.limiter_policy}, finisher={args.finisher_policy})")

    specs = build_specs(args)
    seeds = args.seeds if args.seeds is not None else [args.seed]
    out_root = pathlib.Path(args.output)
    eval_every = int(run_cfg["loop"]["eval_interval_updates"])
    eval_eps = int(run_cfg["loop"]["eval_episodes"])

    for s in seeds:
        seed_everything(s)
        runner = M4Runner(run_cfg, s, args.device,
                          randomize_threat=not args.no_threat_randomization,
                          threat_obs=not args.no_threat_obs,
                          limiter_policy=args.limiter_policy,
                          finisher_policy=args.finisher_policy, **specs)
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
                      f"shape_hk {reg.get('regime/shape/hard_kill', float('nan')):.2f} "
                      # ★ 결함 2 이후 추가. 커밋을 실제로 몇 번 제안하는가 --
                      #   0.00/1.00 으로 굳으면 확률 붕괴(퇴화)이지 "학습 안 됨" 이 아니다.
                      f"| commit {stats.get('limiter/commit_rate', float('nan')):.3f}")
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
            # ★ 역할 분리 팔 (docs/48). 집계기가 이 세 키로 2x2 를 복원한다.
            "arm": runner.arm,
            "limiter_policy": args.limiter_policy,
            "finisher_policy": args.finisher_policy,
            "threat_randomized": not args.no_threat_randomization,
            "threat_obs": not args.no_threat_obs,
            "final": curve[-1] if curve else None,
            "final_eval_episodes": int(args.final_eval_episodes),
            "resumed_from": int(resumed_from),
            "final_eval": final_eval,
            "final_eval_bands": final_bands}, indent=2))


if __name__ == "__main__":
    main()
