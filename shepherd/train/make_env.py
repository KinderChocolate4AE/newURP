"""Training composition root (Phase 2A prerequisite).

WHY THIS FILE EXISTS (2026-07-03 code-doc consistency sweep, docs/09 SS8):
Until now the ONLY env assembly code was shepherd.scripts.rollout_gif.build_env,
whose demo default (episode_len=70) silently diverges from the env contract
(truncation at episode_len=80, docs/09 SS2 -- the 80 lived only in Layout's
dataclass default, in NO config). Cone kwargs were likewise hand-extracted at
the assembly site. A trainer reusing build_env would train on a 70-step horizon
while every doc claims 80.

make_train_env(cfg) is therefore STRICT: episode_len, corridor layout, backend
kinematic limits and the se3_cone geometry must ALL be present in the config
(configs/m2_l2_train.yaml `train:` + `viability.cone:` blocks). A missing key
raises KeyError -- no silent defaults at the composition root. build_env stays
as the lenient DEMO/rendering root; training must come through here.

2026-07-03 GPT-review hardening: (a) the finisher a_max/v_max and adversary
omega backend limits were hardcoded here despite the strict philosophy -- they
are now REQUIRED train.limits keys (added to m2_l2_train.yaml with the SAME
values, behavior unchanged); (b) config sections are type-checked (Mapping) and
layout vectors length-checked; (c) the reserved-dim action padding utilities
moved to shepherd.train.action_dims (re-exported here for back-compat).
"""
from __future__ import annotations
from collections.abc import Mapping

import numpy as np

from shepherd.train.action_dims import (LIVE_DIMS, live_action_dim,   # noqa: F401
                                        pad_env_action, pad_env_actions)
from shepherd.game.roles import ScenarioSpec
from shepherd.env import ShapingParallelEnv, Layout
from shepherd.sim.analytic import AnalyticBackend, AgentKin, KinematicLimits  # composition root

__all__ = ["LIVE_DIMS", "live_action_dim", "pad_env_action", "pad_env_actions",
           "make_train_env"]


def _req(d, key: str, where: str):
    if not isinstance(d, Mapping):
        raise TypeError(f"config section '{where}' must be a mapping, "
                        f"got {type(d).__name__} (composition-root pins are STRICT)")
    if key not in d:
        raise KeyError(f"config missing required key '{where}.{key}' "
                       f"(composition-root pins are STRICT; see shepherd/train/make_env.py)")
    return d[key]


def _vec3(d, key: str, where: str):
    v = [float(x) for x in _req(d, key, where)]
    if len(v) != 3:
        raise ValueError(f"config key '{where}.{key}' must be length 3, got {v}")
    return v


def _ring(n, c, r):
    return [[c[0], c[1] + r * np.cos(2 * np.pi * i / n), c[2] + r * np.sin(2 * np.pi * i / n)]
            for i in range(n)]


def make_train_env(cfg: dict, mode: str = "shaping"):
    """STRICT training composition root: ScenarioSpec + Layout + AnalyticBackend + env.

    Requires cfg['train'] (episode_len, layout, limits -- incl. finisher/adversary
    backend limits) and cfg['viability']['cone'] (half_angle, range_min, range_max).
    Returns (env, scn, lay) like build_env.
    """
    scn = ScenarioSpec.from_dict(cfg)

    tr = _req(cfg, "train", "<root>")
    lo = _req(tr, "layout", "train")
    li = _req(tr, "limits", "train")
    cone = _req(_req(cfg, "viability", "<root>"), "cone", "viability")

    episode_len = int(_req(tr, "episode_len", "train"))   # env-contract horizon (80, docs/09 SS2)
    target = _vec3(lo, "target", "train.layout")
    ring_c = _vec3(lo, "ring_center", "train.layout")
    ring_r = float(_req(lo, "ring_radius", "train.layout"))
    adv_x = float(_req(lo, "adversary_start_x", "train.layout"))

    lay = Layout(target=target,
                 limiter_p0=_ring(scn.n_limiters, ring_c, ring_r),
                 finisher_p0=_vec3(lo, "finisher_p0", "train.layout"),
                 adversary_p0=[adv_x, 0.0, 0.0],
                 adversary_v0=[-scn.adversary.speed, 0.0, 0.0],
                 target_radius=float(_req(lo, "target_radius", "train.layout")),
                 r_ring=float(_req(lo, "r_ring", "train.layout")),
                 episode_len=episode_len)
    # MONKEY PATCH (known wart): Layout lives in FROZEN shepherd/env.py and has no
    # x_fire field, so the scripted-baseline trigger is attached dynamically here
    # and in rollout_gif.build_env. Breaks if Layout ever gains slots=True; fold
    # into the dataclass at the next ratified env.py unfreeze.
    lay.x_fire = float(_req(lo, "x_fire", "train.layout"))   # scripted-baseline trigger only

    lim_vmax = float(_req(li, "limiter_v_max", "train.limits"))
    lim_omega = float(_req(li, "limiter_omega", "train.limits"))
    fin_a_max = float(_req(li, "finisher_a_max", "train.limits"))
    fin_vmax = float(_req(li, "finisher_v_max", "train.limits"))
    adv_vmax = float(_req(li, "adversary_v_max", "train.limits"))
    adv_omega = float(_req(li, "adversary_omega", "train.limits"))

    agents = [AgentKin(f"limiter_{i}", "limiter",
                       KinematicLimits(scn.limiter.a_max, lim_vmax, lim_omega),
                       list(p), [0, 0, 0], [1, 0, 0]) for i, p in enumerate(lay.limiter_p0)]
    agents.append(AgentKin("finisher_0", "finisher",
                           KinematicLimits(fin_a_max, fin_vmax, scn.finisher.omega_max),
                           list(lay.finisher_p0), [0, 0, 0], [1, 0, 0]))
    agents.append(AgentKin("adversary_0", "adversary",
                           KinematicLimits(scn.adversary.a_att_max, adv_vmax, adv_omega),
                           list(lay.adversary_p0), list(lay.adversary_v0), [-1, 0, 0]))
    backend = AnalyticBackend(agents, dt=scn.dt)

    env = ShapingParallelEnv(backend, scn, lay, baseline_mode=mode,
                             cone_half_angle=float(_req(cone, "half_angle", "viability.cone")),
                             cone_range_min=float(_req(cone, "range_min", "viability.cone")),
                             cone_range_max=float(_req(cone, "range_max", "viability.cone")))
    return env, scn, lay
