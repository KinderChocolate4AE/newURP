"""FS1 세계 (docs/123) — full-stack 동시학습용 교전 세계. torch-free.

B0 v3 물리 (χ, η 무차원 resolver, kill chain, net FSM, 포획 판정) 를 그대로 쓰고
다음만 바꾼다:
  - 배치: 공격자 = 자산 중심 2D 고리 R∈[100, 300] m · 방위 균등 · 자산 향해 순항 속도.
          limiter 4 = 자산 중심 반경 2 m 대칭 (위상 무작위), finisher = 자산 위치.
          전진 ring 같은 사전 배치 없음 (편향 금지, 사용자 2026-10-04).
  - env 플래그: lean (viability 는 FIRE tick 에만) · fire gate 제거 · finisher 학습 병진.
  - 공격자: RL 정책 (매 step `set_attacker_action`) 또는 scripted callable (초기 pool).
  - 사격통제 분리 (FCS, 사용자 2026-10-04): 정책 = 전술, FCS = 정밀 실행.
          finisher 행동 [가속3, r_fire(m), arm]: 포탑이 예측 net 중심 자동 추적,
          arm ∧ LOADED ∧ d ≤ r_fire 이면 발사.
          limiter 행동 [가속3, arm]: arm 이면 기존 PN 종말유도 (mission_rollout
          intercept) 가 조종하고 commit_margin 기하가 맞을 때 commit.
          이동 3채널 = **위치 목표 (station point)**: 자산 + c·STATION (c∈[-1,1]),
          하위 PD autopilot (kp 8, kd 4 — scripted limiter 선언값) 이 비행. 가속 행동은
          탐색 노이즈가 적분돼 방어자가 흩어졌다 (BC 검증 2026-10-04).
  - 공격자 (사용자 2026-10-04): 가속 = 자산 homing autopilot + 학습 residual (전권:
          |residual| ≤ 2·a_max, 합산은 백엔드가 a_max 로 clip) — homing 을 잠시 완전히
          덮어써 이탈·baiting 가능, 풀면 다시 유도. 기동 스킬 z = one-hot (Z_DIM 개
          이산 스킬) 을 episode 시작과 평균 Z_SWITCH_S 초 간격 무작위 시점에 재추출,
          공격자 관측에만 붙인다 (다양성 보상은 학습 루프의 판별기).
  - 보상: env_sys RewardSpec (net +1, HARD_KILL +0.5, 침투/timeout −1, limiter 소모 −0.1),
          net 발사 −0.05. 공격자: 침투 +1, 무력화·timeout −1.
          ROE (r3, 사용자 2026-10-04 A안): net 소진 전 kinetic 무력화 = **K_FIRST**, 보상은
          HARD_KILL 과 같은 +0.5 (r_kfirst=None). 6 m no-kinetic zone 은 env_sys 가 유지.
          r2 까지는 −1 (H_ILLEGAL) 이라 kinetic-first mode 가 침투와 같은 값이었다.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Optional

import numpy as np
from gymnasium import spaces

ADV = "adversary_0"
FIN = "finisher_0"

DEFENDED = ("NET_CAPTURE", "CAPTURE_WITH_CONTACT", "HARD_KILL", "K_FIRST")
Z_DIM = 8                 # 이산 기동 스킬 수 (one-hot)
Z_SWITCH_S = 4.0          # 스킬 재추출 평균 간격 (지수분포)
K_HOME = 4.0              # autopilot 속도추종 이득 (1/s)
STATION = np.array([80.0, 80.0, 10.0])   # 방어자 위치 목표 범위 (자산 기준, m)
KP_ST, KD_ST = 8.0, 4.0                  # station PD (shepherd.agents.baselines arc 선언값)


@dataclass(frozen=True)
class FS1Spec:
    chi: float = 0.52            # B2 boundary cell r06c1 (lam slice 0) — 기존 경계 세계 물리
    eta: float = 3.9
    lam_slice: int = 0
    r_spawn: tuple = (100.0, 300.0)
    episode_len: int = 800       # 40 s @ dt 0.05
    lim_start_r: float = 2.0
    w_kill: float = 0.5
    r_kfirst: Optional[float] = None   # net 소진 전 kinetic 보상. None = HARD_KILL 과 동일 (A안)
    c_fire: float = 0.05
    r_fire_range: tuple = (4.0, 16.0)   # FCS 발사 거리 행동의 범위 (m)
    obs_time: bool = False              # r4' (docs/124 D2): 관측에 t/episode_len 1채널 추가
                                        # (timeout 종단 하 Markov 복원). False = 기존 65-D bit-exact
    k_viab: float = 0.0                 # arm B (r5, docs/124 D4): net 발사 tick 에 팀 보상
                                        # += k_viab·v_shot_soft (비준 판정값, non-potential —
                                        # B−A 는 목적함수 변경 효과로만 보고). 0 = off (bit-exact)
    mu: float = 0.35                    # E3 (docs/124 §2): 방어 capability conditioning —
    nu: float = 1.0                     # a_def = mu·a_att, v_def = nu·v_att (limiter·finisher 공통).
                                        # 기본값 = r2a_stage1 의 MU/NU 상수 그대로 (bit-exact).
                                        # 공격자 쪽은 불변 (비준 위협 고정)
    tau_scale: float = 1.0              # E7-b (docs/129 §6): physics.tau_deploy 단일 config
                                        # 소스 배율 — env.tau_deploy 와 FSM dep 타이머 동시 전파
    theta_scale: float = 1.0            # E7-b: judge cone_half_angle 배율
    aim: str = "cv"                     # E7-b FCS 조준: cv = p+v·τ (현행) / "ma" = +½·â·τ²
                                        # (â = 속도 유한차분, a_att_max clip). 기본 전부 no-op
    limiter_roe: str = "a"              # E7-c (docs/130): "a" = 현행 (net 전 kinetic 허용) /
                                        # "post_shot" = 첫 발사 전 limiter 무장·접촉 kinetic 차단
    limiter_inert: bool = False         # E7-c: physics.kill_radius = 0 (판정 폐쇄·kinetic 동시 0)


def _physics_kwargs(spec: FS1Spec) -> dict:
    from shepherd.scripts.r2a_stage1 import resolve
    from shepherd.scripts.r2b_phase1 import _slices
    kw = resolve(_slices()[spec.lam_slice], spec.chi, spec.eta)
    extra = dict(kw["extra_cfg"])
    a, v = extra["physics.a_att_max"], extra["physics.att_speed"]
    extra["train.episode_len"] = int(spec.episode_len)
    # E3 capability conditioning (기본 mu/nu = resolve 의 MU/NU 와 동일 → bit-exact)
    extra["physics.a_lim_max"] = spec.mu * a
    extra["train.limits.limiter_v_max"] = spec.nu * v
    extra["train.limits.finisher_a_max"] = spec.mu * a   # = limiter 와 같은 기체급
    extra["train.limits.finisher_v_max"] = spec.nu * v
    if spec.tau_scale != 1.0:            # E7-b: config 단일 소스 (scenario 경유 FSM 까지 전파)
        from shepherd.m4_config import M4_OVERRIDES
        extra["physics.tau_deploy"] = float(M4_OVERRIDES["physics.tau_deploy"]) * spec.tau_scale
    if spec.limiter_inert:               # E7-c: config 단일 소스 (scenario.limiter.kill_radius)
        extra["physics.kill_radius"] = 0.0
    kw["extra_cfg"] = extra
    kw["reward"] = replace(kw["reward"], w_kill=spec.w_kill, dense_scale=0.0, enabled=True)
    return kw


class FS1Env:
    """PettingZoo-style parallel API. agents = 4 limiter + finisher + adversary."""

    def __init__(self, spec: FS1Spec = FS1Spec(), *, seed: int = 0):
        from shepherd.env_adv import attach_attacker
        from shepherd.m4_env import build_m4_env
        self.spec = spec
        kw = _physics_kwargs(spec)
        self.stack = build_m4_env(seed, 0, randomize_threat=False, **kw)
        self.env = self.stack.env                       # ThreatObsEnv
        self.sys = self.env.inner                       # ModeSystemEnv
        self.inner = self.sys.inner                     # ShapingParallelEnv
        inn = self.inner
        inn.lean, inn.fire_gate_on, inn.finisher_learned_accel = True, False, True
        if spec.theta_scale != 1.0:      # E7-b: judge 콘 반각 배율 (판정 의미론 불변)
            inn.cone_half_angle = float(inn.cone_half_angle) * spec.theta_scale
        self._fcs_v_prev = None          # E7-b ma 조준용 공격자 속도 이력 (cv 는 미사용)
        self._fired = False              # E7-c post_shot: 첫 발사 latch (K>1 재장전에도 유지)
        self._contact0 = bool(self.sys.spec.contact_resolver)
        fa = float(inn.backend.by_name(FIN).limits.a_max)
        inn._act_spaces[FIN] = spaces.Box(
            np.array([-1, -1, -1, 0, 0, -fa, -fa, -fa], np.float32),
            np.array([1, 1, 1, 1, 1, fa, fa, fa], np.float32), dtype=np.float32)
        self._att_a = np.zeros(3)
        self._scripted: Optional[Callable] = None
        attach_attacker(inn, self._attacker_cb)
        self.att_speed = float(inn.sc.adversary.speed)
        self.att_a_max = float(inn.backend.by_name(ADV).limits.a_max)
        self.limiter_ids = list(inn.limiter_ids)
        self.agents = self.limiter_ids + [FIN, ADV]
        self._rng = np.random.default_rng(seed)
        self.z = np.zeros(Z_DIM)

    # ---- attacker plumbing ------------------------------------------------
    def _attacker_cb(self, p_att, v_att, **kw):
        if self._scripted is not None:
            return self._scripted(p_att, v_att, **kw)
        a = self._att_a
        n = float(np.linalg.norm(a))
        e = a / n if n > 1e-9 else (v_att / max(np.linalg.norm(v_att), 1e-9))
        return {"a": a.copy(), "e_cmd": e}

    def set_scripted_attacker(self, cb: Optional[Callable]):
        """None → RL 공격자 (step 의 adversary 행동 사용)."""
        self._scripted = cb

    def autopilot(self):
        """자산 향한 순항속도 추종 (residual 0 이면 이것만으로 침투)."""
        inn = self.inner
        att = inn._states()[2]
        p, v = inn._p(att), inn._v(att)
        d = np.asarray(inn.layout.target, float) - p
        v_des = self.att_speed * d / max(np.linalg.norm(d), 1e-9)
        a = K_HOME * (v_des - v)
        n = np.linalg.norm(a)
        return a * (self.att_a_max / n) if n > self.att_a_max else a

    def att_obs(self, obs_vec):
        return np.r_[obs_vec, self.z].astype(np.float32)

    def action_space(self, agent):
        if agent == ADV:                                   # residual (전권)
            a = 2.0 * self.att_a_max
            return spaces.Box(-a, a, (3,), np.float32)
        return self.inner.action_space(agent)

    # ---- episode ------------------------------------------------------------
    def _place(self):
        inn, rng, sp = self.inner, self._rng, self.spec
        tgt = np.asarray(inn.layout.target, float)
        R = rng.uniform(*sp.r_spawn)
        th = rng.uniform(0.0, 2.0 * np.pi)
        p_att = tgt + R * np.array([np.cos(th), np.sin(th), 0.0])
        att = inn.backend.by_name(ADV)
        att.p0 = list(p_att)
        att.v0 = list(-self.att_speed * (p_att - tgt) / R)
        n = len(self.limiter_ids)
        ph = rng.uniform(0.0, 2.0 * np.pi / n)
        ring = [tgt + sp.lim_start_r * np.array([np.cos(ph + 2 * np.pi * i / n),
                                                  np.sin(ph + 2 * np.pi * i / n), 0.0])
                for i in range(n)]
        for lid, p in zip(self.limiter_ids, ring):
            b = inn.backend.by_name(lid)
            b.p0, b.v0 = list(p), [0.0, 0.0, 0.0]
        f = inn.backend.by_name(FIN)
        f.p0, f.v0 = list(tgt), [0.0, 0.0, 0.0]
        inn.layout = replace(inn.layout, limiter_p0=tuple(tuple(p) for p in ring),
                             finisher_p0=tuple(tgt))

    def _aug(self, obs):
        """r4' 시간 채널: 각 관측 벡터 끝에 t/episode_len 을 붙인다 (spec.obs_time 일 때만)."""
        if not self.spec.obs_time:
            return obs
        f = np.float32(self._t / self.spec.episode_len)
        return {k: np.r_[v, f].astype(np.float32) for k, v in obs.items()}

    def reset(self, seed: Optional[int] = None):
        if seed is not None:
            self._rng = np.random.default_rng(seed)
            # scripted 사다리 jink 위상 (P1a 와 같은 derive_phase 규약). 해시라 _rng 흐름 불변
            from shepherd.agents.attacker_ladder import derive_phase
            self.inner._attacker_phase = derive_phase(0, seed)
        self._place()
        self._att_a = np.zeros(3)
        self._fcs_v_prev = None
        self._fired = False
        self._t = 0
        self.z = self._draw_skill()
        obs, infos = self.env.reset(seed=int(self._rng.integers(2**31)))
        self.start_station = {a: self.station_of(a) for a in self.limiter_ids + [FIN]}
        return self._aug(obs), infos

    # ---- 사격통제 (FCS) -------------------------------------------------------
    def station_accel(self, agent, c):
        """위치 목표 c∈[-1,1]³ (자산 기준 ×STATION) → PD 가속 (a_max clip)."""
        b = self.inner.backend.by_name(agent)
        p_cmd = np.asarray(self.inner.layout.target, float) + np.clip(c, -1, 1) * STATION
        a = KP_ST * (p_cmd - np.asarray(b.p, float)) - KD_ST * np.asarray(b.v, float)
        n = np.linalg.norm(a)
        return a * (b.limits.a_max / n) if n > b.limits.a_max else a

    def station_of(self, agent):
        """현재 위치 → 위치 목표 c (위치 유지 라벨용)."""
        b = self.inner.backend.by_name(agent)
        return (np.asarray(b.p, float) - np.asarray(self.inner.layout.target, float)) / STATION

    def limiters_harmless(self) -> bool:
        """E7-c: 지금 limiter kinetic 이 금지되는가 (inert 상시 / post_shot 은 첫 발사 전)."""
        return self.spec.limiter_inert or (self.spec.limiter_roe == "post_shot" and not self._fired)

    def fcs(self, hl: dict) -> dict:
        """전술 행동 → env 행동. hl[limiter] = [c3, arm], hl[finisher] = [c3, r_fire, arm]
        (c = 위치 목표, station_accel 참조)."""
        from shepherd.scripts.mission_rollout import _limiter_actions
        inn = self.inner
        if self.limiters_harmless():     # 무장 채널 0 강제 → PN 커밋 경로 차단
            hl = {k: (np.r_[np.asarray(v, float)[:3], 0.0] if k in self.limiter_ids else v)
                  for k, v in hl.items()}
        lims, fin, att = inn._states()
        p_att, v_att, p_fin = inn._p(att), inn._v(att), inn._p(fin)
        acts = {}
        if any(hl.get(l, np.zeros(4))[3] > 0.5 for l in self.limiter_ids):
            pn = _limiter_actions(self.env, inn.sc, inn.layout, "intercept", lims, p_att, v_att)
        for lid in self.limiter_ids:
            a = np.asarray(hl.get(lid, np.zeros(4)), float)
            acts[lid] = (np.asarray(pn[lid], float) if a[3] > 0.5
                         else np.r_[self.station_accel(lid, a[:3]), 0.0])
        f = np.asarray(hl.get(FIN, np.zeros(5)), float)
        nc = np.asarray(inn._net_center(p_att, v_att))
        if self.spec.aim == "ma":        # E7-b (docs/129 §6): 조준점만 보정, witness/판정 불변
            ah = (np.zeros(3) if self._fcs_v_prev is None
                  else (v_att - self._fcs_v_prev) / inn.dt)
            n = np.linalg.norm(ah)
            if n > inn.a_att_max:
                ah = ah * (inn.a_att_max / n)
            nc = nc + 0.5 * ah * inn.tau_deploy ** 2
            self._fcs_v_prev = v_att.copy()
        axis = (nc - p_fin) / max(np.linalg.norm(nc - p_fin), 1e-9)
        fire = float(f[4] > 0.5 and inn.fsm.state.value == "LOADED"
                     and np.linalg.norm(p_att - p_fin) <= f[3])
        acts[FIN] = np.r_[axis, 1.0, fire, self.station_accel(FIN, f[:3])]
        return acts

    def step(self, actions: dict):
        """actions = 전술 행동 (FCS 가 env 행동으로 변환) + adversary 가속."""
        actions = {**self.fcs(actions), **({ADV: actions[ADV]} if ADV in actions else {})}
        if ADV in actions and self._scripted is None:   # autopilot + residual
            self._att_a = self.autopilot() + np.clip(actions[ADV], -2 * self.att_a_max,
                                                     2 * self.att_a_max)
        if self._rng.random() < self.inner.dt / Z_SWITCH_S:
            self.z = self._draw_skill()
        acts = {k: v for k, v in actions.items() if k != ADV}
        acts[ADV] = np.zeros(3)                         # 백엔드 프록시가 교체
        want = self._contact0 and not self.limiters_harmless()   # 접촉 kinetic 경로 (E7-c)
        if self.sys.spec.contact_resolver != want:
            self.sys.spec = replace(self.sys.spec, contact_resolver=want)
        obs, rew, terms, truncs, infos = self.env.step(acts)
        fi = infos.get(FIN, next(iter(infos.values()), {}))
        if fi.get("fire_event"):
            self._fired = True
        label = fi.get("m4_outcome")
        r_def = float(rew.get(FIN, 0.0))
        if label == "HARD_KILL" and not self._kill_after_net(fi):
            if self.spec.r_kfirst is not None:
                r_def += self.spec.r_kfirst - self.sys.reward_spec.terminal("HARD_KILL")
            label = "K_FIRST"                          # B0 v3 의 H_illegal 과 같은 사건
        if fi.get("fire_event"):
            r_def -= self.spec.c_fire
            if self.spec.k_viab:
                r_def += self.spec.k_viab * float(fi.get("v_shot_soft") or 0.0)
        r_att = 0.0
        if label == "PENETRATED":
            r_att = 1.0
        elif label is not None:
            r_att = -1.0
        rewards = {a: r_def for a in self.limiter_ids + [FIN]}
        rewards[ADV] = r_att
        done = any(terms.values()) or any(truncs.values())
        for a in infos:
            infos[a]["fs1_label"] = label
        self._t += 1
        return self._aug(obs), rewards, done, infos

    def _draw_skill(self):
        return np.eye(Z_DIM)[int(self._rng.integers(Z_DIM))]

    def _kill_after_net(self, fi) -> bool:
        # net 이 실제로 소모된 뒤(miss 확인 후)의 kinetic = fallback, 그 전 = K_FIRST
        return bool(fi.get("net_spent", False) or self.sys.net_spent)
