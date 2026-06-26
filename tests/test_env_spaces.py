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
