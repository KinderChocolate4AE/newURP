from types import SimpleNamespace
from dataclasses import replace

import numpy as np

from shepherd.train.b0_v3_credit import (B0V3CreditEnv, B0V3CreditSpec,
                                          viability_potential)


AGENTS = ["limiter_0", "finisher", "adversary"]


class FakeEnv:
    possible_agents = AGENTS
    finisher_id = "finisher"
    adversary_id = "adversary"
    kill_radius = 0.75
    spec = SimpleNamespace(r_contact=None)

    def __init__(self, events):
        self.events = list(events)
        self.agents = list(AGENTS)
        self.net_spent = False
        self._lim = np.array([10.0, 0.0, 0.0])
        self._att = np.zeros(3)

    def _states(self):
        return ["lim"], "fin", "att"

    def _p(self, state):
        return self._lim if state == "lim" else self._att

    def reset(self, seed=None, options=None):
        self.agents = list(AGENTS)
        self.net_spent = False
        return self._obs(0.2, 1.0), {a: {} for a in AGENTS}

    def _obs(self, v_soft, p_feasible):
        x = np.array([0.0, v_soft, 0.0, p_feasible], np.float32)
        return {a: x.copy() for a in AGENTS}

    def step(self, actions):
        ev = self.events.pop(0)
        self.net_spent = bool(ev.get("net_spent", False))
        obs = self._obs(ev.get("v_soft", 0.3), ev.get("p_feasible", 1.0))
        info = {
            "contacts": ev.get("contacts", []),
            "hard_kill": ev.get("hard_kill", False),
            "captured": ev.get("captured", False),
            "penetrated": ev.get("penetrated", False),
            "net_spent": self.net_spent,
        }
        infos = {a: dict(info) for a in AGENTS}
        terms = {a: bool(ev.get("terminated", False)) for a in AGENTS}
        truncs = {a: bool(ev.get("truncated", False)) for a in AGENTS}
        return obs, {a: 99.0 for a in AGENTS}, terms, truncs, infos


def _step(event, *, beta=0.0):
    env = B0V3CreditEnv(FakeEnv([event]), B0V3CreditSpec(beta=beta))
    env.reset()
    return env, env.step({})


def test_potential_zeroes_boxed_surrogate():
    assert viability_potential(np.array([7.0, 1.0, 1.0, 0.0])) == 0.0
    assert viability_potential(np.array([7.0, 0.4, 1.0, 0.5])) == 0.4
    augmented = np.array([7.0, 0.4, 1.0, 0.5, -0.2, 0.7])
    assert viability_potential(augmented, trailing_features=2) == 0.4


def test_clean_capture_is_the_only_positive_terminal():
    env, (_, rewards, terms, _, infos) = _step({"captured": True})
    assert rewards["finisher"] == 1.0
    assert all(terms.values())
    assert infos["finisher"]["b0_rl_outcome"] == "N"
    assert env.agents == []


def test_illegal_engagement_precedes_same_tick_capture():
    _, (_, rewards, terms, _, infos) = _step(
        {"captured": True, "contacts": [(0, "KILL", 0.2)]})
    assert rewards["finisher"] == -1.0
    assert all(terms.values())
    assert infos["finisher"]["b0_rl_outcome"] == "H_illegal"


def test_net_spent_cuts_credit_with_neutral_task_reward():
    _, (_, rewards, terms, _, infos) = _step({"net_spent": True})
    assert rewards["finisher"] == 0.0
    assert all(terms.values())
    assert infos["finisher"]["b0_rl_outcome"] == "NET_SPENT"


def test_point_engagement_is_detected_even_without_swept_record():
    raw = FakeEnv([{}])
    raw._lim = np.array([0.5, 0.0, 0.0])
    env = B0V3CreditEnv(raw, B0V3CreditSpec(beta=0.0))
    env.reset()
    _, rewards, _, _, infos = env.step({})
    assert rewards["finisher"] == -1.0
    assert infos["finisher"]["b0_illegal_engagement"] is True


def test_pbrs_uses_zero_terminal_potential():
    _, (_, rewards, _, _, infos) = _step({"net_spent": True}, beta=0.2)
    assert np.isclose(rewards["finisher"], -0.04)
    assert np.isclose(infos["finisher"]["b0_phi_next"], 0.0)


def test_credit_manifest_is_stable():
    a = B0V3CreditSpec().manifest()
    b = B0V3CreditSpec().manifest()
    assert a == b
    assert len(a["credit_hash"]) == 16


def test_real_b0_world_cuts_on_net_spent_without_running_fallback():
    from shepherd.m4_env import build_m4_env
    from shepherd.scripts.b2_manifest import load
    from shepherd.scripts.b2_run import scenario_kwargs
    from shepherd.scripts.mission_rollout import scripted_role_actions

    manifest = load()
    cell = next(c for c in manifest["cells"] if c["cell_id"] == "r03c1")
    source_s = next(u["s_lo"] for u in manifest["units"]
                    if u["cell_id"] == cell["cell_id"])
    _, _, kw = scenario_kwargs(manifest, cell, source_s)
    kw["system"] = replace(kw["system"], force_commit_step=1)
    stack = build_m4_env(manifest["crn"]["seed0"], source_s, **kw)
    env = B0V3CreditEnv(stack.env, B0V3CreditSpec(beta=0.0))
    env.reset(seed=manifest["crn"]["seed0"] + source_s)

    outcome = None
    for _ in range(30):
        actions = scripted_role_actions(env, stack.scn, stack.lay,
                                        limiter_mode="hold", fire_mode="never")
        actions[env.adversary_id] = np.zeros(3, np.float32)
        _, rewards, terms, _, infos = env.step(actions)
        outcome = infos[env.finisher_id]["b0_rl_outcome"]
        if any(terms.values()):
            break

    assert outcome == "NET_SPENT"
    assert rewards[env.finisher_id] == 0.0
    assert env.inner.net_spent is True
    assert env.agents == []
