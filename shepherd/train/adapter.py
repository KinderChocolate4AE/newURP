"""Trainer-side adapter for ShapingParallelEnv (Phase 2A, docs/09 SS5).

torch-free. Bridges the PettingZoo ParallelEnv (frozen contract) to the
Phase-1 PPO core's flat-array world without modifying either side:

  - composition STRICTLY via shepherd.train.make_env.make_train_env (the
    strict root; the lenient demo root rollout_gif.build_env is banned for
    training, docs/09 SS2);
  - policies act in LIVE dims only (limiter 3 = accel, finisher 4 = axis+fire,
    adversary 3); reserved dims are re-inserted as zeros by pad_env_action;
  - the adversary is env-scripted (frozen env computes its action internally
    and ignores the submitted one) -- the adapter injects zeros for API shape;
  - credit split extracted per step and kept separate (docs/09 SS2):
    info[limiter_i]["coma_D"] and info[finisher]["delta_v_shot_headline"];
  - env.state() exposed each step for the 2C central critic.

2B plugs role policies into collect_episode(); nothing here depends on torch.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import numpy as np

from shepherd.env import ShapingParallelEnv
from shepherd.train.action_dims import role_of          # noqa: F401  (재수출: tests/test_adapter_smoke)
from shepherd.train.make_env import live_action_dim, pad_env_action, LIVE_DIMS

SHARED_FLAG_KEYS = ("fire_event", "wasted_fire", "fsm_state", "k_remaining",
                    "v_shot_soft", "v_shot_worst", "p_feasible", "boxed_in",
                    "threshold_crossed", "clean_net_threshold_crossed",
                    "captured", "penetrated", "limiter_loss")


@dataclass
class StepResult:
    obs: Dict[str, np.ndarray]
    rewards: Dict[str, float]
    terminated: bool
    truncated: bool
    done: bool                       # terminated or truncated (episode over)
    coma_D: Dict[str, float]         # limiter_id -> analytic D_i (S8 credit)
    headline: float                  # finisher delta_v_shot_headline
    flags: Dict[str, object]         # SHARED_FLAG_KEYS subset of the shared info
    state: np.ndarray                # env.state() AFTER the step (central critic)


class ShepherdAdapter:
    """Flat-array view of the frozen ParallelEnv for role-based trainers."""

    def __init__(self, env: ShapingParallelEnv):
        self.env = env
        self.agent_ids: List[str] = list(env.possible_agents)
        self.limiter_ids = [a for a in self.agent_ids if role_of(a) == "limiter"]
        self.finisher_id = next(a for a in self.agent_ids if role_of(a) == "finisher")
        self.adversary_id = next(a for a in self.agent_ids if role_of(a) == "adversary")
        self.obs_dim = int(env.observation_space(self.agent_ids[0]).shape[0])
        self.state_dim = 9 * (len(self.limiter_ids) + 2)   # kinematic concat
        # live-dim slices of the env action Box, per agent
        self._bounds = {}
        for a in self.agent_ids:
            space = env.action_space(a)
            _, live_idx = LIVE_DIMS[role_of(a)]
            self._bounds[a] = (space.low[list(live_idx)].astype(np.float64),
                               space.high[list(live_idx)].astype(np.float64))

    # ------------------------------------------------------------------ api
    def live_dim(self, agent_id: str) -> int:
        return live_action_dim(agent_id)

    def action_bounds(self, agent_id: str):
        """(low, high) arrays for the LIVE dims of this agent."""
        return self._bounds[agent_id]

    def reset(self, seed: int):
        obs, _ = self.env.reset(seed=seed)
        self._check_obs(obs)
        return obs, self.env.state()

    def step(self, live_actions: Dict[str, np.ndarray]) -> StepResult:
        acts = dict(live_actions)
        acts.setdefault(self.adversary_id, np.zeros(3, np.float32))  # env-scripted
        env_actions = {aid: pad_env_action(aid, a) for aid, a in acts.items()}
        obs, rewards, terms, truncs, infos = self.env.step(env_actions)
        self._check_obs(obs)
        terminated = any(terms.values())
        truncated = any(truncs.values())
        fin_info = infos[self.finisher_id]
        coma = {lid: float(infos[lid]["coma_D"]) for lid in self.limiter_ids}
        flags = {k: fin_info[k] for k in SHARED_FLAG_KEYS}
        return StepResult(
            obs=obs, rewards={a: float(r) for a, r in rewards.items()},
            terminated=terminated, truncated=truncated,
            done=bool(terminated or truncated),
            coma_D=coma, headline=float(fin_info["delta_v_shot_headline"]),
            flags=flags, state=self.env.state())

    # ------------------------------------------------------------------ util
    def _check_obs(self, obs: Dict[str, np.ndarray]):
        for a, o in obs.items():
            if o.shape != (self.obs_dim,):
                raise ValueError(f"{a}: obs shape {o.shape} != ({self.obs_dim},)")
            if not np.all(np.isfinite(o)):
                raise FloatingPointError(f"{a}: non-finite obs")


def random_policy(rng: np.random.Generator, fire_prob: float = 0.0) -> Callable:
    """Uniform live-dim policy within the env action bounds; finisher fire is a
    Bernoulli(fire_prob) mapped to {0, 1} (env decodes fire > 0.5)."""
    def policy(agent_id: str, obs: np.ndarray, adapter: ShepherdAdapter):
        low, high = adapter.action_bounds(agent_id)
        act = rng.uniform(low, high).astype(np.float32)
        if role_of(agent_id) == "finisher":
            act[-1] = 1.0 if rng.uniform() < fire_prob else 0.0
        return act
    return policy


@dataclass
class Episode:
    obs: Dict[str, np.ndarray]        # agent -> (T+1, obs_dim) incl. terminal obs
    actions: Dict[str, np.ndarray]    # agent -> (T, live_dim)
    rewards: Dict[str, np.ndarray]    # agent -> (T,)
    coma_D: np.ndarray                # (T, n_limiters), limiter_ids order
    headline: np.ndarray              # (T,)
    states: np.ndarray                # (T+1, state_dim)
    terminated: bool = False
    truncated: bool = False
    flags_last: Dict[str, object] = field(default_factory=dict)

    @property
    def length(self) -> int:
        return next(iter(self.rewards.values())).shape[0]


def collect_episode(adapter: ShepherdAdapter, policy: Callable, seed: int,
                    max_steps: Optional[int] = None) -> Episode:
    """Roll one episode with `policy(agent_id, obs, adapter) -> live action`.

    Runs to the env's natural end (terminated/truncated) or max_steps. Returns
    per-agent stacked arrays; obs/states include the post-terminal entry so GAE
    can bootstrap V(final_obs) on truncation (docs/09 SS5 Phase 1 gae.py).
    """
    obs, state = adapter.reset(seed)
    controlled = [a for a in adapter.agent_ids if a != adapter.adversary_id]
    obs_hist = {a: [obs[a]] for a in adapter.agent_ids}
    act_hist = {a: [] for a in controlled}
    rew_hist = {a: [] for a in adapter.agent_ids}
    coma_hist, head_hist, state_hist = [], [], [state]
    terminated = truncated = False
    flags_last: Dict[str, object] = {}

    t = 0
    while adapter.env.agents and (max_steps is None or t < max_steps):
        live = {a: policy(a, obs[a], adapter) for a in controlled}
        r = adapter.step(live)
        obs = r.obs
        for a in adapter.agent_ids:
            obs_hist[a].append(r.obs[a])
            rew_hist[a].append(r.rewards[a])
        for a in controlled:
            act_hist[a].append(np.asarray(live[a], np.float32))
        coma_hist.append([r.coma_D[l] for l in adapter.limiter_ids])
        head_hist.append(r.headline)
        state_hist.append(r.state)
        terminated, truncated, flags_last = r.terminated, r.truncated, r.flags
        t += 1
        if r.done:
            break

    return Episode(
        obs={a: np.stack(v) for a, v in obs_hist.items()},
        actions={a: (np.stack(v) if v else np.zeros((0, adapter.live_dim(a)),
                                                    np.float32))
                 for a, v in act_hist.items()},
        rewards={a: np.asarray(v, float) for a, v in rew_hist.items()},
        coma_D=np.asarray(coma_hist, float),
        headline=np.asarray(head_hist, float),
        states=np.stack(state_hist),
        terminated=terminated, truncated=truncated, flags_last=flags_last)
