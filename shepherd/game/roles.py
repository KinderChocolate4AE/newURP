"""Role + resource specs (sim-agnostic).

- limiter:   cheap, expendable kamikaze; explosive kill-radius = credible no-go threat.
- finisher:  ONE non-destructive net-capturer; finite magazine K, deploy delay tau,
             IRREVERSIBLE fire, miss-is-free; reduced-attitude pointing for the net axis.
- adversary: goal-constrained (must penetrate) + evasive; see agents/adversary.py.
Physical spec VALUES are injected/read-only (assumptions register), never hardcoded.
"""
from __future__ import annotations
