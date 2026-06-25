"""Capture-viability v_shot (THE GOAL, sim-agnostic).

v_shot(x, u_limiters) = P[attacker still inside the net deployment volume at t+tau |
its best feasible escape], where cheap kamikaze limiters' kill-radii impose a no-go
that SHRINKS the attacker's tau-reachable set R_A. This is the S8 shaping-as-lever core.

Proof-of-concept (numpy, validated): ../prototypes/reachset.py.
TODO(6-DOF): replace the single-segment point-mass reachable set with a 6-DOF SE3
reachable set (attitude/rate limits, reduced-attitude pointing for the net axis);
keep the interface v_shot(state, limiters, net_spec) -> [0,1] sim-agnostic.
"""
from __future__ import annotations
# port/extend from prototypes/reachset.py
