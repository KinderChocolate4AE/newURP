"""Scripted-attacker FAMILY domain randomization (M2; docs/09 SS7 item (c) step 1).

Per-episode iid sampling over a FIXED-range attacker family -- a stationary
distribution, NOT co-training (self-play / exploiter probes stay S13 / post-L2,
docs/09 SS7). The env is rebuilt per episode through the STRICT composition
root (make_train_env) on a DEEP-COPIED config dict; the frozen YAML and the
frozen env.py are never touched.

Why these knobs and no others (ratified reasoning, docs/09 SS8 2026-07-03):
  att_speed          -> ScenarioSpec.adversary.speed: the scripted forward-drive
                        v_nominal AND the spawn velocity (make_train_env wires
                        both from the same value).
  adversary_start_x  -> Layout spawn depth (the only config-reachable spawn
                        geometry knob; y/z are fixed by the frozen corridor).
  adversary_omega    -> backend heading-slew limit (train.limits) -- evasion
                        turn agility.
  adv_a_max          -> the ACTUAL scripted accel/dodge authority. This is the
                        ShapingParallelEnv constructor knob (env.py line 1:
                        ``adv_a_max``) that make_train_env does not surface; a
                        post-construction attribute set is EXACTLY equivalent
                        to passing the kwarg. DOWNWARD-ONLY (<= physics
                        a_att_max = 30): (1) the backend adversary
                        KinematicLimits.a_max is built from the SAME
                        physics.a_att_max, so any value above 30 would be
                        silently clamped by the integrator; (2) actual <=
                        surrogate keeps the S14 conservative signal sound
                        (v_shot never reads optimistically vs the family).

NEVER randomized: physics.a_att_max (the v_shot surrogate authority). Moving it
would shift the reward/measurement semantics that theta_fire = 0.9 and the
zero-waste band [0.85, 1.0] were calibrated against (fire_gate_calibration).

torch-free.
"""
from __future__ import annotations

import copy
from typing import Dict, Optional

import numpy as np

from shepherd.train.make_env import make_train_env

__all__ = ["RAND_KEYS", "sample_attacker_params", "build_attacker_env"]

# knob -> (config path applied in build_attacker_env)
RAND_KEYS = ("att_speed", "adversary_start_x", "adversary_omega", "adv_a_max")


def sample_attacker_params(rand_cfg: Optional[dict],
                           rng: np.random.Generator) -> Dict[str, float]:
    """Sample one attacker-family draw: uniform in [lo, hi] per enabled knob.

    Returns {} when disabled/absent (nominal ratified env). Unknown keys raise
    (catches typos instead of silently training on the nominal attacker).
    """
    if not rand_cfg or not bool(rand_cfg.get("enabled", False)):
        return {}
    unknown = set(rand_cfg) - set(RAND_KEYS) - {"enabled"}
    if unknown:
        raise KeyError(f"unknown randomize keys: {sorted(unknown)} "
                       f"(allowed: {list(RAND_KEYS)})")
    out: Dict[str, float] = {}
    for key in RAND_KEYS:
        rng_spec = rand_cfg.get(key)
        if rng_spec is None:
            continue
        lo, hi = (float(v) for v in rng_spec)
        if hi < lo:
            raise ValueError(f"randomize.{key}: hi {hi} < lo {lo}")
        out[key] = float(rng.uniform(lo, hi))
    if "adv_a_max" in out and out["adv_a_max"] > 30.0 + 1e-9:
        # backend clamp + S14 soundness (module docstring); fail loudly rather
        # than silently training on a clamped, mislabeled attacker.
        raise ValueError(
            f"randomize.adv_a_max upper bound {out['adv_a_max']:.3f} > 30 "
            "(backend KinematicLimits clamps at physics.a_att_max; "
            "downward-only randomization)")
    return out


def build_attacker_env(env_cfg: dict, params: Dict[str, float]):
    """make_train_env on a deep-copied cfg with one family draw applied.

    ``env_cfg`` (the loaded frozen YAML dict) is NEVER mutated. Returns
    (env, scn, lay) like make_train_env. ``adv_a_max`` is applied as a
    post-construction attribute set == the ShapingParallelEnv constructor
    kwarg (the surrogate authority env.a_att_max is untouched).
    """
    cfg = copy.deepcopy(env_cfg)
    if "att_speed" in params:
        cfg["physics"]["att_speed"] = float(params["att_speed"])
    if "adversary_start_x" in params:
        cfg["train"]["layout"]["adversary_start_x"] = float(
            params["adversary_start_x"])
    if "adversary_omega" in params:
        cfg["train"]["limits"]["adversary_omega"] = float(
            params["adversary_omega"])
    env, scn, lay = make_train_env(cfg)
    if "adv_a_max" in params:
        env.adv_a_max = float(params["adv_a_max"])
    return env, scn, lay
