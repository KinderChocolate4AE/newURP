"""Baselines for the exchange-frontier comparison.

- no_shaping:    finisher (net) alone, no limiters.
- selection_only: pick when/which to commit by predicted capturability (Choi-style), no shaping.
- buy_nets:      no shaping, more nets K (the defense-OR alternative our thesis must beat).
- heuristic_ring: hand-placed limiter ring (the prototypes' static placement).
The learned MARL shaping policy must beat these on (P_penetration vs resource).
"""
from __future__ import annotations
