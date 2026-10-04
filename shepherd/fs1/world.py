"""FS1 세계 (docs/123) — full-stack 동시학습용 교전 세계. torch-free.

B0 v3 물리 (χ, η 무차원 resolver, kill chain, net FSM, 포획 판정) 를 그대로 쓰고
다음만 바꾼다:
  - 배치: 공격자 = 자산 중심 2D 고리 R∈[100, 300] m · 방위 균등 · 자산 향해 순항 속도.
          limiter 4 = 자산 중심 반경 2 m 대칭 (위상 무작위), finisher = 자산 위치.
          전진 ring 같은 사전 배치 없음 (편향 금지, 사용자 2026-10-04).
  - env 플래그: lean (viability 는 FIRE tick 에만) · fire gate 제거 · finisher 학습 병진.
  - 공격자: RL 정책 (매 step `set_attacker_action`) 또는 scripted callable (초기 pool).
  - 보상: env_sys RewardSpec (net +1, HARD_KILL +0.5, 침투/timeout −1, limiter 소모 −0.1)
          + net 소진 전 kinetic 무력화 (H_illegal) → −1 로 대체, net 발사 −0.05.
          공격자: 침투 +1, 무력화·timeout −1.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Optional

import numpy as np
from gymnasium import spaces

ADV = "adversary_0"
FIN = "finisher_0"

DEFENDED = ("NET_CAPTURE", "CAPTURE_WITH_CONTACT", "HARD_KILL")


@dataclass(frozen=True)
class FS1Spec:
    chi: float = 0.52            # B2 boundary cell r06c1 (lam slice 0) — 기존 경계 세계 물리
    eta: float = 3.9
    lam_slice: int = 0
    r_spawn: tuple = (100.0, 300.0)
    episode_len: int = 800       # 40 s @ dt 0.05
    lim_start_r: float = 2.0
    w_kill: float = 0.5
    r_illegal: float = -1.0
    c_fire: float = 0.05


def _physics_kwargs(spec: FS1Spec) -> dict:
    from shepherd.scripts.r2a_stage1 import MU, NU, resolve
    from shepherd.scripts.r2b_phase1 import _slices
    kw = resolve(_slices()[spec.lam_slice], spec.chi, spec.eta)
    extra = dict(kw["extra_cfg"])
    a, v = extra["physics.a_att_max"], extra["physics.att_speed"]
    extra["train.episode_len"] = int(spec.episode_len)
    extra["train.limits.finisher_a_max"] = MU * a        # = limiter 와 같은 기체급
    extra["train.limits.finisher_v_max"] = NU * v
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

    def action_space(self, agent):
        if agent == ADV:
            a = self.att_a_max
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

    def reset(self, seed: Optional[int] = None):
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        self._place()
        self._att_a = np.zeros(3)
        obs, infos = self.env.reset(seed=int(self._rng.integers(2**31)))
        return obs, infos

    def step(self, actions: dict):
        if ADV in actions and self._scripted is None:
            self._att_a = np.asarray(actions[ADV], float)
        acts = {k: v for k, v in actions.items() if k != ADV}
        acts[ADV] = np.zeros(3)                         # 백엔드 프록시가 교체
        obs, rew, terms, truncs, infos = self.env.step(acts)
        fi = infos.get(FIN, next(iter(infos.values()), {}))
        label = fi.get("m4_outcome")
        r_def = float(rew.get(FIN, 0.0))
        if label == "HARD_KILL" and not self._kill_after_net(fi):
            r_def += self.spec.r_illegal - self.sys.reward_spec.terminal("HARD_KILL")
            label = "H_ILLEGAL"
        if fi.get("fire_event"):
            r_def -= self.spec.c_fire
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
        return obs, rewards, done, infos

    def _kill_after_net(self, fi) -> bool:
        # net 이 실제로 소모된 뒤(miss 확인 후 fallback)의 kinetic 만 합법
        return bool(fi.get("net_spent", False) or self.sys.net_spent)
