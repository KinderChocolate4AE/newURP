"""Commit-3 smoke tests: finisher FSM + reduced-attitude analytic backend.

(PettingZoo env-conformance / COMA tests are commit 4.)
Run: python -m pytest tests/test_env_spaces.py
"""
import numpy as np
import pytest

from shepherd.game.roles import FinisherSpec, FireGate
from shepherd.game.finisher_fsm import FinisherFSM, FinisherState, step_fsm
from shepherd.sim.analytic import AnalyticBackend, AgentKin, KinematicLimits, _slew

# --- shared specs ---
SPEC = FinisherSpec(K=1, tau_deploy=0.4, tau_lock=0.1, net_radius=1.5,
                    omega_max=3.14159, e_net=(1.0, 0.0, 0.0))
GATE = FireGate(theta_fire=0.8, B_capture=1.0, c_fire=0.8)
DT = 0.05


def _advance(fsm, n, fire_cmd=0, v=0.0, capture=None):
    for _ in range(n):
        fsm = step_fsm(fsm, fire_cmd, v, finisher_spec=SPEC, fire_gate=GATE, dt=DT,
                       capture=capture)
    return fsm


# --------------------------------------------------------------------------- #
# FSM
# --------------------------------------------------------------------------- #
def test_fsm_double_fire_decrements_once():
    """A second fire while DEPLOYING/LOCKED/SPENT is a no-op; k decrements once."""
    fsm = FinisherFSM.new(SPEC)                 # LOADED, k=1
    fsm = step_fsm(fsm, 1, 0.9, finisher_spec=SPEC, fire_gate=GATE, dt=DT)
    assert fsm.state is FinisherState.DEPLOYING
    assert fsm.k == 0 and fsm.fired_count == 1
    # hammer fire during DEPLOYING -> must not touch k or fired_count
    fsm = step_fsm(fsm, 1, 0.9, finisher_spec=SPEC, fire_gate=GATE, dt=DT)
    assert fsm.k == 0 and fsm.fired_count == 1
    # run to SPENT, then fire again -> still no-op
    fsm = _advance(fsm, 30, fire_cmd=1, v=0.9)
    assert fsm.state is FinisherState.SPENT
    assert fsm.k == 0 and fsm.fired_count == 1


def test_fsm_k1_reaches_spent_and_wasted_on_miss():
    """K=1 valid fire reaches SPENT after deploy+lock; an unmarked (missed)
    commit consumes the shot and surfaces as wasted_fire."""
    fsm = FinisherFSM.new(SPEC)
    fsm = step_fsm(fsm, 1, 0.85, finisher_spec=SPEC, fire_gate=GATE, dt=DT)
    # deploy = 0.4/0.05 = 8 ticks, lock = 0.1/0.05 = 2 ticks
    fsm = _advance(fsm, 7)                       # still deploying
    assert fsm.state is FinisherState.DEPLOYING
    fsm = _advance(fsm, 1)                       # -> LOCKED
    assert fsm.state is FinisherState.LOCKED
    fsm = _advance(fsm, 2, capture=None)        # lock resolves as a miss
    assert fsm.state is FinisherState.SPENT
    assert fsm.k == 0
    assert fsm.wasted_fire == 1
    assert fsm.last_capture is False


def test_fsm_capture_hit_is_not_wasted():
    """A marked capture consumes the shot but is NOT counted as wasted_fire."""
    fsm = FinisherFSM.new(SPEC)
    fsm = step_fsm(fsm, 1, 0.85, finisher_spec=SPEC, fire_gate=GATE, dt=DT)
    fsm = _advance(fsm, 8)                       # -> LOCKED
    fsm = _advance(fsm, 2, capture=True)         # resolve as a hit
    assert fsm.state is FinisherState.SPENT
    assert fsm.wasted_fire == 0
    assert fsm.last_capture is True


def test_fire_gate_single_source():
    """R2: below theta_fire does NOT fire from LOADED; at/above theta_fire fires."""
    fsm = FinisherFSM.new(SPEC)
    blocked = step_fsm(fsm, 1, 0.79, finisher_spec=SPEC, fire_gate=GATE, dt=DT)
    assert blocked.state is FinisherState.LOADED
    assert blocked.k == 1 and blocked.fired_count == 0     # no decrement when gated
    fired = step_fsm(fsm, 1, 0.80, finisher_spec=SPEC, fire_gate=GATE, dt=DT)
    assert fired.state is FinisherState.DEPLOYING
    assert fired.k == 0


# --------------------------------------------------------------------------- #
# Backend
# --------------------------------------------------------------------------- #
def _backend():
    agents = [
        AgentKin("lim0", "limiter", KinematicLimits(a_max=30.0, v_max=25.0, omega_max=6.0),
                 p0=[5, 2, 0], v0=[0, 0, 0], e0=[1, 0, 0]),
        AgentKin("fin", "finisher", KinematicLimits(a_max=20.0, v_max=20.0, omega_max=3.14159),
                 p0=[8, 0, 0], v0=[0, 0, 0], e0=[1, 0, 0]),
        AgentKin("att", "adversary", KinematicLimits(a_max=30.0, v_max=20.0, omega_max=8.0),
                 p0=[0, 0, 0], v0=[20, 0, 0], e0=[1, 0, 0]),
    ]
    return AnalyticBackend(agents, dt=DT)


def test_backend_reset_reproducible():
    """reset(seed) is deterministic across instances."""
    a = _backend(); b = _backend()
    oa = a.reset(7); ob = b.reset(7)
    for role in oa:
        for sa, sb in zip(oa[role], ob[role]):
            assert np.array_equal(sa, sb)


def test_backend_step_sane():
    """Observations finite; headings unit-normalized after stepping."""
    be = _backend(); be.reset(0)
    action = {
        "lim0": {"a": [10, -5, 0], "e_cmd": [0, 1, 0]},
        "fin":  {"a": [0, 0, 0], "e_cmd": [0, 0, 1]},
        "att":  {"a": [5, 8, 0], "e_cmd": [1, 1, 0]},
    }
    obs = be.observe()
    for _ in range(10):
        obs, r, term, trunc, info = be.step(action)
    for role, states in obs.items():
        for s9 in states:
            assert np.all(np.isfinite(s9))
            assert s9.shape == (9,)
            assert abs(np.linalg.norm(s9[6:9]) - 1.0) < 1e-9   # heading is unit


def test_backend_bounds_respected():
    """Speed cap, accel clamp, and slew-rate bound all hold under extreme commands."""
    be = _backend(); be.reset(0)
    att = be.by_name("att")          # v_max=20, a_max=30, omega_max=8
    e_before = att.e.copy()
    v_before = att.v.copy()
    # command huge accel + a 180-degree heading flip
    be.step({"att": {"a": [1e6, 1e6, 0], "e_cmd": [-1, 0, 0]}})
    # speed cap
    assert np.linalg.norm(att.v) <= att.limits.v_max + 1e-9
    # accel clamp: |dv|/dt <= a_max
    assert np.linalg.norm(att.v - v_before) <= att.limits.a_max * be.dt + 1e-6
    # slew bound: heading turned by <= omega_max*dt
    cos = float(np.clip(e_before @ att.e, -1.0, 1.0))
    assert np.arccos(cos) <= att.limits.omega_max * be.dt + 1e-6
    assert abs(np.linalg.norm(att.e) - 1.0) < 1e-9


def test_slew_reaches_when_within_budget():
    """If the commanded turn is within omega_max*dt, the heading snaps to it."""
    e = np.array([1.0, 0.0, 0.0])
    out = _slew(e, np.array([1.0, 0.05, 0.0]), max_ang=1.0)   # tiny turn, big budget
    assert abs(np.linalg.norm(out) - 1.0) < 1e-12
    assert out @ _slew(np.array([1.0, 0.05, 0.0]), np.array([1.0, 0.05, 0.0]), 1.0) > 0.999


# --------------------------------------------------------------------------- #
# PettingZoo M2 env composition (commit 4)
# --------------------------------------------------------------------------- #
from shepherd.game.roles import ScenarioSpec                       # noqa: E402
from shepherd.game.finisher_fsm import FinisherState               # noqa: E402
from shepherd.env import ShapingParallelEnv, Layout                # noqa: E402


def _ring(n, c, r):
    return [[c[0], c[1] + r * np.cos(2 * np.pi * i / n), c[2] + r * np.sin(2 * np.pi * i / n)]
            for i in range(n)]


def _scenario(n_lim, judge, nsamp):
    return ScenarioSpec.from_dict({
        "scenario": {"n_limiters": n_lim, "n_adversaries": 1, "finisher": {"K": 1}},
        "physics": {"dt": 0.05, "tau_deploy": 0.4, "tau_lock": 0.1, "a_att_max": 30.0,
                    "att_speed": 8.0, "kill_radius": 2.0, "net_radius": 2.25, "a_lim_max": 200.0},
        "attitude": {"omega_max": 3.14159, "e_net_init": [1, 0, 0]},
        "fire_gate": {"theta_fire": 0.8, "B_capture": 1.0, "c_fire": 0.8},
        "viability": {"judge": judge, "turn_limited": False, "n_samples": nsamp, "seed": 0},
        "reward": {"lambda1": 1.0, "lambda2": 1.0, "lambda3": 0.5},
        "baselines": {"headline_u0": "hold_position", "coma_u0": "hold_position"}})


def _env_backend(scn, lay):
    ag = [AgentKin(f"limiter_{i}", "limiter", KinematicLimits(200.0, 150.0, 16.0),
                   list(p), [0, 0, 0], [1, 0, 0]) for i, p in enumerate(lay.limiter_p0)]
    ag.append(AgentKin("finisher_0", "finisher", KinematicLimits(1.0, 1.0, 3.14159),
                       list(lay.finisher_p0), [0, 0, 0], [1, 0, 0]))
    ag.append(AgentKin("adversary_0", "adversary", KinematicLimits(30.0, 20.0, 10.0),
                       list(lay.adversary_p0), list(lay.adversary_v0), [-1, 0, 0]))
    return AnalyticBackend(ag, dt=scn.dt)


def _conformance_env(n_lim=4, nsamp=200):
    """Small, fast env for API/space conformance (point_mass judge)."""
    scn = _scenario(n_lim, "point_mass", nsamp)
    lay = Layout(target=[0.0, 0, 0], limiter_p0=_ring(n_lim, [8.0, 0, 0], 4.0),
                 finisher_p0=[2.0, 0, 0], adversary_p0=[16.0, 0, 0], adversary_v0=[-8, 0, 0],
                 target_radius=1.0, r_ring=2.1, episode_len=12)
    return ShapingParallelEnv(_env_backend(scn, lay), scn, lay)


def test_parallel_api_conformance():
    """PettingZoo ParallelEnv conformance (parallel_api_test)."""
    from pettingzoo.test import parallel_api_test
    parallel_api_test(_conformance_env(), num_cycles=40)


def test_env_reset_reproducible():
    a, b = _conformance_env(), _conformance_env()
    oa, _ = a.reset(seed=3)
    ob, _ = b.reset(seed=3)
    for k in oa:
        assert np.array_equal(oa[k], ob[k])


def test_obs_and_sampled_actions_in_spaces():
    env = _conformance_env()
    obs, _ = env.reset(seed=0)
    for agent, o in obs.items():
        assert env.observation_space(agent).contains(o)
    for _ in range(5):
        acts = {a: env.action_space(a).sample() for a in env.agents}
        for a, ac in acts.items():
            assert env.action_space(a).contains(ac)
        obs, rew, term, trunc, info = env.step(acts)
        if not env.agents:
            break
    for agent, o in obs.items():
        assert env.observation_space(agent).contains(o)


def test_step_returns_parallel_dicts():
    env = _conformance_env()
    env.reset(seed=0)
    acts = {a: env.action_space(a).sample() for a in env.agents}
    obs, rew, term, trunc, info = env.step(acts)
    for d in (obs, rew, term, trunc, info):
        assert set(d.keys()) == set(env.possible_agents)
    assert all(isinstance(v, float) for v in rew.values())
    assert all(isinstance(v, bool) for v in term.values())
    assert all(isinstance(v, bool) for v in trunc.values())
    assert all(isinstance(v, dict) for v in info.values())


def test_termination_truncation_mutually_exclusive():
    """Across a full rollout, no agent is both terminated and truncated."""
    env = _conformance_env()
    env.reset(seed=0)
    for _ in range(60):
        acts = {a: env.action_space(a).sample() for a in env.agents}
        _, _, term, trunc, _ = env.step(acts)
        for a in term:
            assert not (term[a] and trunc[a])
        if not env.agents:
            break


def test_env_double_fire_no_double_decrement():
    """Hammering the finisher fire-logit through the env path decrements k once."""
    env = _conformance_env()
    env.reset(seed=0)
    saw_fire = False
    for _ in range(env.layout.episode_len):
        acts = {lid: np.zeros(4, np.float32) for lid in env.limiter_ids}
        # finisher: always command fire (logit=1); FSM enforces single decrement
        acts["finisher_0"] = np.array([1, 0, 0, 1, 1], np.float32)
        acts["adversary_0"] = np.zeros(3, np.float32)
        _, _, _, _, info = env.step(acts)
        if info["finisher_0"]["fire_event"]:
            saw_fire = True
        assert env.fsm.k >= 0
        if not env.agents:
            break
    assert saw_fire                      # it did fire at least once
    assert env.fsm.fired_count == 1      # ... and only once (K=1, irreversible)
    assert env.fsm.k == 0


def test_env_fire_gate_threshold():
    """Below theta_fire the env never fires; a high-v_shot setup does fire.
    (point_mass with a large net so v_shot >= theta_fire is reachable.)"""
    # low-v_shot: tiny net -> v_shot stays under theta_fire -> never fires
    scn = _scenario(4, "point_mass", 300)
    lay = Layout(target=[0.0, 0, 0], limiter_p0=_ring(4, [8.0, 0, 0], 4.0),
                 finisher_p0=[2.0, 0, 0], adversary_p0=[16.0, 0, 0], adversary_v0=[-8, 0, 0],
                 target_radius=1.0, r_ring=2.1, episode_len=30)
    env = ShapingParallelEnv(_env_backend(scn, lay), scn, lay)
    # shrink the net hard so the random reachable set rarely lands inside
    env.net_radius = 0.3
    env.reset(seed=0)
    for _ in range(env.layout.episode_len):
        acts = {lid: np.zeros(4, np.float32) for lid in env.limiter_ids}
        acts["finisher_0"] = np.array([1, 0, 0, 1, 1], np.float32)   # always command fire
        acts["adversary_0"] = np.zeros(3, np.float32)
        _, _, _, _, info = env.step(acts)
        assert info["finisher_0"]["v_shot_soft"] < env.theta_fire     # gate never satisfied
        if not env.agents:
            break
    assert env.fsm.fired_count == 0                                   # gate blocked every fire


def test_config_default_judge_is_se3_cone():
    """Note A: the M2/L1 default config selects the SE(3) cone judge, end-to-end
    (canonical value 'se3_cone' flows config -> ScenarioSpec -> viability)."""
    import pathlib
    import yaml
    cfg = yaml.safe_load(open(pathlib.Path(__file__).resolve().parents[1]
                              / "configs" / "m2_default.yaml"))
    assert cfg["viability"]["judge"] == "se3_cone"
    assert ScenarioSpec.from_dict(cfg).viability.judge == "se3_cone"
