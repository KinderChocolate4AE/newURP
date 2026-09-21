"""B0 v3용 RL credit wrapper.

물리 환경은 NET_SPENT 뒤의 kinetic fallback을 계속 적분한다. 학습은 clean net
capture만을 목표로 하므로 그 경로를 보상에 섞지 않고, NET_SPENT 또는 PRE/PENDING
kinetic engagement에서 에피소드 credit을 끝낸다. 내부 환경의 상태 전이나 결과 정의는
바꾸지 않는다.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Dict

import numpy as np


@dataclass(frozen=True)
class B0V3CreditSpec:
    gamma: float = 0.99
    beta: float = 0.2
    r_clean: float = 1.0
    r_illegal: float = -1.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.gamma <= 1.0:
            raise ValueError("gamma must be in [0, 1]")
        if self.beta < 0.0:
            raise ValueError("beta must be non-negative")
        if self.r_clean <= 0.0:
            raise ValueError("r_clean must be positive")
        if self.r_illegal >= 0.0:
            raise ValueError("r_illegal must be negative")

    def manifest(self) -> dict:
        body = {
            "schema": "b0-v3-rl-credit-v1",
            "task": "clean NET_CAPTURE",
            "cuts": ["H_illegal", "NET_SPENT"],
            "failure_reward": 0.0,
            "potential": "p_feasible>0 ? clip(v_shot_soft,0,1) : 0",
            **asdict(self),
        }
        raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
        return {**body, "credit_hash": hashlib.sha256(raw.encode()).hexdigest()[:16]}


def viability_potential(obs: np.ndarray, *, trailing_features: int = 0) -> float:
    """viability triple로 만든 bounded potential.

    B0 v3는 triple 뒤에 threat features 2개를 붙이므로 wrapper가 그 폭을 넘긴다.
    """
    x = np.asarray(obs, dtype=float).reshape(-1)
    k = int(trailing_features)
    if k < 0 or x.size < 3 + k:
        raise ValueError("observation is too short for the viability triple")
    v_soft, p_feasible = x[-3 - k], x[-1 - k]
    return float(np.clip(v_soft, 0.0, 1.0)) if float(p_feasible) > 0.0 else 0.0


class B0V3CreditEnv:
    """ParallelEnv-compatible reward/termination view over ``ModeSystemEnv``."""

    def __init__(self, inner, spec: B0V3CreditSpec = B0V3CreditSpec()):
        self.inner = inner
        self.spec = spec
        self.possible_agents = list(inner.possible_agents)
        self.agents = list(inner.agents)
        self._n_trailing = int(getattr(inner, "n_extra", 0))
        self._phi = 0.0

    def reset(self, seed=None, options=None):
        obs, infos = self.inner.reset(seed=seed, options=options)
        self.agents = list(self.inner.agents)
        self._phi = viability_potential(
            obs[self.inner.finisher_id], trailing_features=self._n_trailing)
        return obs, infos

    def _point_engagement(self) -> bool:
        lims, _, att = self.inner._states()
        p_att = np.asarray(self.inner._p(att), dtype=float)
        radius = (float(self.inner.spec.r_contact)
                  if self.inner.spec.r_contact is not None
                  else float(self.inner.kill_radius))
        return any(float(np.linalg.norm(
            p_att - np.asarray(self.inner._p(lim), dtype=float))) <= radius
                   for lim in lims)

    def step(self, actions):
        # 같은 tick의 NET_SPENT보다 engagement가 먼저라는 B0 v3 precedence를
        # 보존하려고 step 전 phase를 기록한다.
        pre_spent = bool(getattr(self.inner, "net_spent", False))
        point_before = (not pre_spent) and self._point_engagement()

        obs, _, terms, truncs, infos = self.inner.step(actions)
        fi = infos[self.inner.finisher_id]
        swept = bool(fi.get("contacts"))
        hard_kill = bool(fi.get("hard_kill", False))
        illegal = bool((not pre_spent) and (point_before or swept or hard_kill))
        captured = bool(fi.get("captured", False))
        clean = bool(captured and not illegal)
        spent = bool(fi.get("net_spent", False))
        natural_term = bool(any(terms.values()))
        natural_trunc = bool(any(truncs.values()))
        credit_cut = bool(illegal or clean or spent or natural_term or natural_trunc)

        if illegal:
            outcome, task_reward = "H_illegal", self.spec.r_illegal
        elif clean:
            outcome, task_reward = "N", self.spec.r_clean
        elif spent:
            outcome, task_reward = "NET_SPENT", 0.0
        elif bool(fi.get("penetrated", False)):
            outcome, task_reward = "PENETRATED", 0.0
        elif natural_trunc:
            outcome, task_reward = "TRUNCATED", 0.0
        else:
            outcome, task_reward = "RUNNING", 0.0

        phi_next = 0.0 if credit_cut else viability_potential(
            obs[self.inner.finisher_id], trailing_features=self._n_trailing)
        shaped = self.spec.beta * (self.spec.gamma * phi_next - self._phi)
        team_reward = float(task_reward + shaped)
        self._phi = phi_next

        rewards: Dict[str, float] = {
            aid: (-team_reward if aid == self.inner.adversary_id else team_reward)
            for aid in self.possible_agents
        }
        if illegal or clean or spent:
            terms = {aid: True for aid in self.possible_agents}
            truncs = {aid: False for aid in self.possible_agents}

        extra = {
            "b0_credit_cut": credit_cut,
            "b0_rl_outcome": outcome,
            "b0_reward_task": float(task_reward),
            "b0_reward_shape": float(shaped),
            "b0_phi_next": float(phi_next),
            "b0_illegal_engagement": illegal,
        }
        infos = {aid: {**infos.get(aid, {}), **extra}
                 for aid in self.possible_agents}
        self.agents = [] if credit_cut else list(self.inner.agents)
        return obs, rewards, terms, truncs, infos

    def __getattr__(self, name):
        return getattr(self.__dict__["inner"], name)
