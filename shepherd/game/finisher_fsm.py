"""Finite-magazine, irreversible net-shot FSM (S1/S3, sim-agnostic, torch-free).

The finisher carries a finite magazine K and fires an IRREVERSIBLE net-shot. A
fire commits the shot: the net deploys after tau_deploy and the launcher locks
for tau_lock. A MISSED commit still consumes the shot and is surfaced as
`wasted_fire` to later env logic -- i.e. the shot is finite-magazine and
miss-costly to the defender (R1). This is NOT a strategic-signaling channel
(S4): the fire is a physical commitment.

Pin (import discipline): this module does NOT import viability. The capture
value `v_shot_soft` is PASSED IN to the transition; the FSM only applies the
single fire gate (R2): fire_allowed = v_shot_soft >= fire_gate.theta_fire.
Deploy resolves against the commit metadata FROZEN at fire time, never against
live-recomputed limiter geometry.

State machine (M2 default K=1):
    LOADED --fire(valid)--> DEPLOYING --tau_deploy--> LOCKED --tau_lock-->
        (k==0) SPENT  |  (k>0) LOADED
fire is a no-op in DEPLOYING / LOCKED / SPENT -> a double-fire NEVER decrements k twice.
"""
from __future__ import annotations
import enum
from dataclasses import dataclass, replace
from typing import Optional, Tuple

from shepherd.game.roles import FinisherSpec, FireGate

_EPS_T = 1e-9
Vec3 = Tuple[float, float, float]


class FinisherState(enum.Enum):
    LOADED = "LOADED"
    DEPLOYING = "DEPLOYING"
    LOCKED = "LOCKED"
    SPENT = "SPENT"


@dataclass(frozen=True)
class CommitMeta:
    """Finisher pose + net target FROZEN at the fire instant (S2/S5). Deploy
    resolves against THIS, not live geometry."""
    t_fire: float
    p_F: Vec3
    v_F: Vec3
    e_net: Vec3                 # net-pointing axis at commit (n_F = R_F.e_net)
    net_center: Vec3            # net volume target frozen at commit
    v_shot_at_commit: float


@dataclass(frozen=True)
class FinisherFSM:
    """Immutable FSM snapshot; step_fsm returns the next snapshot."""
    k: int                                  # remaining net-shots
    state: FinisherState = FinisherState.LOADED
    timer: float = 0.0                      # remaining countdown in current phase [s]
    commit: Optional[CommitMeta] = None     # active frozen commit (DEPLOYING/LOCKED)
    wasted_fire: int = 0                    # shots consumed on a miss
    fired_count: int = 0                    # total valid fires (shots committed)
    last_capture: Optional[bool] = None     # outcome of the most recent resolved shot
    t: float = 0.0                          # FSM clock [s]

    @classmethod
    def new(cls, finisher_spec: FinisherSpec) -> "FinisherFSM":
        return cls(k=int(finisher_spec.K))


def step_fsm(fsm: FinisherFSM, fire_cmd, v_shot_soft, *,
             finisher_spec: FinisherSpec, fire_gate: FireGate, dt: float,
             commit_meta: Optional[CommitMeta] = None,
             capture: Optional[bool] = None) -> FinisherFSM:
    """Advance the FSM one dt tick, processing a fire command this tick.

    - fire_cmd is effective ONLY from LOADED and ONLY if v_shot_soft >= theta_fire
      (R2 single gate). A valid fire decrements k EXACTLY once and freezes
      commit_meta.
    - In DEPLOYING/LOCKED/SPENT fire_cmd is ignored (no second decrement).
    - At lock resolution the caller-supplied `capture` marks hit/miss; a miss
      (capture is not True) increments wasted_fire. k==0 -> SPENT else LOADED.
    """
    t = fsm.t + dt
    s = fsm.state

    if s is FinisherState.LOADED:
        fire_allowed = (int(fire_cmd) == 1) and (float(v_shot_soft) >= fire_gate.theta_fire)
        if fire_allowed:
            return replace(fsm,
                           state=FinisherState.DEPLOYING,
                           k=fsm.k - 1,                 # decrement EXACTLY once
                           timer=float(finisher_spec.tau_deploy),
                           commit=commit_meta,
                           fired_count=fsm.fired_count + 1,
                           t=t)
        return replace(fsm, t=t)                        # gate-blocked / no fire: no decrement, no waste

    if s is FinisherState.DEPLOYING:
        timer = fsm.timer - dt
        if timer <= _EPS_T:
            return replace(fsm, state=FinisherState.LOCKED,
                           timer=float(finisher_spec.tau_lock), t=t)
        return replace(fsm, timer=timer, t=t)

    if s is FinisherState.LOCKED:
        timer = fsm.timer - dt
        if timer <= _EPS_T:
            hit = (capture is True)
            wasted = fsm.wasted_fire + (0 if hit else 1)   # miss (incl. unmarked) consumes the shot
            nxt = FinisherState.SPENT if fsm.k == 0 else FinisherState.LOADED
            return replace(fsm, state=nxt, timer=0.0, commit=None,
                           wasted_fire=wasted, last_capture=hit, t=t)
        return replace(fsm, timer=timer, t=t)

    # SPENT: terminal, all fire is a no-op.
    return replace(fsm, t=t)
