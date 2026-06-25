"""Reactive, goal-constrained, evasive adversary (THE keystone adversary).

Default (M2): constant forward progress toward the protected point + lateral dodge,
avoids kamikaze kill-radii, dodges on observing a net commit.
S13 (richer, deferred): loiter/BAIT to induce a commit -> hard back-diagonal escape ->
exploit the reload window to slip the kinetic limiters and penetrate.
NOTE: this is the closed-loop, state-consuming model (WarSim threats.py only has
open-loop scripted attackers today).
"""
from __future__ import annotations
