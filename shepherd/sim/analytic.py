"""Reduced-attitude KINEMATICS backend (THE MEANS, M2/L1 build-tier).

Implements sim.interface.EnvBackend with pure point-mass-plus-heading kinematics:
per-agent 9D state s = (p, v, e), where e is a UNIT heading/pointing axis. This
is the build-tier realization of the SE(3)-aware contract (docs/03 S2): omega is
NOT a state variable -- omega_max is a slew-RATE parameter that bounds how fast e
turns (R3). No full 6-DOF aero, no torch.

Integration (per step, per agent):
    a_cmd   <- clamp to ||a|| <= a_max
    v_{t+1} <- clip_speed(v_t + a_cmd*dt, v_max)
    p_{t+1} <- p_t + v_{t+1}*dt
    e_{t+1} <- slew(e_t, e_cmd, omega_max*dt)        (great-circle, rate-limited)

Pin (import discipline): this backend does NOT import finisher_fsm or game/*.
It does ONLY kinematics -- magazine, timers, fire gate, and v_shot live in the
FSM / viability core. The env (commit 4) composes FSM + backend + viability.
Reward/terminated are placeholders here (0.0/False); the env produces them.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

from shepherd.sim.interface import EnvBackend

_EPS = 1e-12


def _unit(v, fallback):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    if n < _EPS:
        return np.asarray(fallback, float).copy()
    return v / n


def _orthogonal(e):
    """Any unit vector orthogonal to e (for the anti-parallel slew case)."""
    ref = np.array([1.0, 0.0, 0.0]) if abs(e[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    o = ref - (ref @ e) * e
    return _unit(o, np.array([0.0, 1.0, 0.0]))


def _slew(e, e_cmd, max_ang):
    """Rotate unit heading e toward e_cmd by at most max_ang (Rodrigues)."""
    e = _unit(e, np.array([1.0, 0.0, 0.0]))
    nc = np.linalg.norm(e_cmd)
    if nc < _EPS or max_ang <= 0.0:
        return e                                    # no command / no slew budget
    ec = np.asarray(e_cmd, float) / nc
    dot = float(np.clip(e @ ec, -1.0, 1.0))
    ang = np.arccos(dot)
    if ang <= max_ang or ang < _EPS:
        return ec                                   # can reach the command this step
    axis = np.cross(e, ec)
    na = np.linalg.norm(axis)
    axis = _orthogonal(e) if na < _EPS else axis / na   # anti-parallel -> arbitrary axis
    c, s = np.cos(max_ang), np.sin(max_ang)
    e_new = e * c + np.cross(axis, e) * s + axis * (axis @ e) * (1.0 - c)
    return _unit(e_new, e)


@dataclass(frozen=True)
class KinematicLimits:
    a_max: float
    v_max: float
    omega_max: float = 3.14159


@dataclass
class AgentKin:
    """One kinematic body. p0/v0/e0 are the deterministic reset state."""
    name: str
    role: str                       # "limiter" | "finisher" | "adversary"
    limits: KinematicLimits
    p0: Sequence[float]
    v0: Sequence[float]
    e0: Sequence[float] = (1.0, 0.0, 0.0)
    p: np.ndarray = field(default=None, repr=False)
    v: np.ndarray = field(default=None, repr=False)
    e: np.ndarray = field(default=None, repr=False)


class AnalyticBackend(EnvBackend):
    """Reduced-attitude kinematics for a list of role-tagged agents."""

    def __init__(self, agents: List[AgentKin], dt: float):
        self.agents = agents
        self.dt = float(dt)
        self._t = 0.0
        self._rng: Optional[np.random.Generator] = None
        self.reset(0)

    # --- EnvBackend ABC -----------------------------------------------------
    def reset(self, seed: int):
        """Deterministic reset to (p0, v0, e0). seed only seeds an (unused-by-
        default) RNG so a later env can add seeded jitter without breaking this
        backend's determinism contract."""
        self._rng = np.random.default_rng(seed)
        self._t = 0.0
        for a in self.agents:
            a.p = np.asarray(a.p0, float).copy()
            a.v = np.asarray(a.v0, float).copy()
            a.e = _unit(np.asarray(a.e0, float), np.array([1.0, 0.0, 0.0]))
        return self.observe()

    def step(self, action: Dict[str, dict]):
        """action: {agent_name: {"a": (3,), "e_cmd": (3,)}}. Missing keys -> hold.
        Returns (obs, reward, terminated, truncated, info); reward/term are
        placeholders -- the env (commit 4) computes the real reward."""
        self._t += self.dt
        for a in self.agents:
            cmd = action.get(a.name, {}) if action else {}
            a_cmd = np.asarray(cmd.get("a", np.zeros(3)), float)
            e_cmd = np.asarray(cmd.get("e_cmd", a.e), float)

            an = np.linalg.norm(a_cmd)                          # clamp accel
            if an > a.limits.a_max and an > _EPS:
                a_cmd = a_cmd * (a.limits.a_max / an)

            v_new = a.v + a_cmd * self.dt                       # clip speed
            sp = np.linalg.norm(v_new)
            if sp > a.limits.v_max and sp > _EPS:
                v_new = v_new * (a.limits.v_max / sp)

            a.p = a.p + v_new * self.dt
            a.v = v_new
            a.e = _slew(a.e, e_cmd, a.limits.omega_max * self.dt)
        return self.observe(), 0.0, False, False, {"t": self._t}

    def observe(self):
        """Role-structured obs: {role: [s9, ...]} with s9 = concat(p, v, e)."""
        out: Dict[str, list] = {}
        for a in self.agents:
            out.setdefault(a.role, []).append(self.state9(a))
        return out

    # --- helpers ------------------------------------------------------------
    def state9(self, a: AgentKin) -> np.ndarray:
        return np.concatenate([a.p, a.v, a.e])

    def by_name(self, name: str) -> AgentKin:
        for a in self.agents:
            if a.name == name:
                return a
        raise KeyError(name)
