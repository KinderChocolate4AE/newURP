"""Exchange economics (THE GOAL, sim-agnostic).

Miss-is-free payoff + two-currency resource accounting (cheap expendable kamikaze
limiters + scarce irreversible non-destructive nets) -> the EXCHANGE FRONTIER:
P_penetration vs E[resource spent], under an attacker best response (bait/exhaustion).
Headline comparison: cheap-limiter shaping vs buying more nets.

Proof-of-concept (numpy, validated): ../prototypes/exchange_game.py (shaping dominates).
TODO: drive frontier from measured 6-DOF MARL rollouts (not heuristic placement).
"""
from __future__ import annotations
# port/extend from prototypes/exchange_game.py
