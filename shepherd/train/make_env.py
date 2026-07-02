"""Training composition root (Phase 2A prerequisite) + reserved-dim action pads.

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

RESERVED ACTION DIMS (decision 2026-07-03, Hyunjun -- docs/09 SS2):
The frozen env (shepherd/env.py) ACCEPTS limiter Box(4)=accel3+pressure and
finisher Box(5)=axis3+slew+fire but IGNORES pressure (idx 3) and slew (idx 3).
Those dims stay in the env contract as RESERVED (env.py is frozen, diff 0).
Trainers must NOT explore them: policies output only the LIVE dims
(limiter 3 = accel, finisher 4 = axis3+fire, adversary 3 = accel) and
pad_env_action() re-inserts zeros at the reserved indices before env.step().
"""
from __future__ import annotations
from typing import Dict, Tuple

import numpy as np

from shepherd.game.roles import ScenarioSpec
from shepherd.env import ShapingParallelEnv, Layout
from shepherd.sim.analytic import AnalyticBackend, AgentKin, KinematicLimits  # composition root

# role -> (env action dim, LIVE indices). Complement = RESERVED (env ignores; pad 0).
LIVE_DIMS: Dict[str, Tuple[int, Tuple[int, ...]]] = {
    "limiter":   (4, (0, 1, 2)),        # accel xyz     | reserved: pressure (idx 3)
    "finisher":  (5, (0, 1, 2, 4)),     # axis xyz+fire | reserved: slew     (idx 3)
    "adversary": (3, (0, 1, 2)),        # accel xyz     | (scripted in-env; kept for API)
}


def _role(agent_id: str) -> str:
    role = agent_id.rsplit("_", 1)[0]
    if role not in LIVE_DIMS:
        raise KeyError(f"unknown agent id '{agent_id}' (role '{role}')")
    return role


def live_action_dim(agent_id: str) -> int:
    """Policy output dim for this agent (reserved dims excluded)."""
    return len(LIVE_DIMS[_role(agent_id)][1])


def pad_env_action(agent_id: str, live_action) -> np.ndarray:
    """Map a policy's LIVE-dim action to the env's full Box, zeros at RESERVED idx.

    finisher example: live (ax, ay, az, fire) -> env (ax, ay, az, 0.0, fire).
    """
    env_dim, live_idx = LIVE_DIMS[_role(agent_id)]
    la = np.asarray(live_action, np.float32).reshape(-1)
    if la.shape[0] != len(live_idx):
        raise ValueError(f"{agent_id}: expected live dim {len(live_idx)}, got {la.shape[0]}")
    out = np.zeros(env_dim, np.float32)
    out[list(live_idx)] = la
    return out


def pad_env_actions(live_actions: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    """Dict convenience wrapper over pad_env_action."""
    return {aid: pad_env_action(aid, a) for aid, a in live_actions.items()}


def _req(d: dict, key: str, where: str):
    if key not in d:
        raise KeyError(f"config missing required key '{where}.{key}' "
                       f"(composition-root pins are STRICT; see shepherd/train/make_env.py)")
    return d[key]


def _ring(n, c, r):
    return [[c[0], c[1] + r * np.cos(2 * np.pi * i / n), c[2] + r * np.sin(2 * np.pi * i / n)]
            for i in range(n)]


def make_train_env(cfg: dict, mode: str = "shaping"):
    """STRICT training composition root: ScenarioSpec + Layout + AnalyticBackend + env.

    Requires cfg['train'] (episode_len, layout, limits) and cfg['viability']['cone']
    (half_angle, range_min, range_max). Returns (env, scn, lay) like build_env.
    """
    scn = ScenarioSpec.from_dict(cfg)

    tr = _req(cfg, "train", "<root>")
    lo = _req(tr, "layout", "train")
    li = _req(tr, "limits", "train")
    cone = _req(_req(cfg, "viability", "<root>"), "cone", "viability")

    episode_len = int(_req(tr, "episode_len", "train"))   # env-contract horizon (80, docs/09 SS2)
    target = [float(x) for x in _req(lo, "target", "train.layout")]
    ring_c = [float(x) for x in _req(lo, "ring_center", "train.layout")]
    ring_r = float(_req(lo, "ring_radius", "train.layout"))
    adv_x = float(_req(lo, "adversary_start_x", "train.layout"))

    lay = Layout(target=target,
                 limiter_p0=_ring(scn.n_limiters, ring_c, ring_r),
                 finisher_p0=[float(x) for x in _req(lo, "finisher_p0", "train.layout")],
                 adversary_p0=[adv_x, 0.0, 0.0],
                 adversary_v0=[-scn.adversary.speed, 0.0, 0.0],
                 target_radius=float(_req(lo, "target_radius", "train.layout")),
                 r_ring=float(_req(lo, "r_ring", "train.layout")),
                 episode_len=episode_len)
    lay.x_fire = float(_req(lo, "x_fire", "train.layout"))   # scripted-baseline trigger only

    lim_vmax = float(_req(li, "limiter_v_max", "train.limits"))
    lim_omega = float(_req(li, "limiter_omega", "train.limits"))
    adv_vmax = float(_req(li, "adversary_v_max", "train.limits"))

    agents = [AgentKin(f"limiter_{i}", "limiter",
                       KinematicLimits(scn.limiter.a_max, lim_vmax, lim_omega),
                       list(p), [0, 0, 0], [1, 0, 0]) for i, p in enumerate(lay.limiter_p0)]
    agents.append(AgentKin("finisher_0", "finisher",
                           KinematicLimits(1.0, 1.0, scn.finisher.omega_max),
                           list(lay.finisher_p0), [0, 0, 0], [1, 0, 0]))
    agents.append(AgentKin("adversary_0", "adversary",
                           KinematicLimits(scn.adversary.a_att_max, adv_vmax, 10.0),
                           list(lay.adversary_p0), list(lay.adversary_v0), [-1, 0, 0]))
    backend = AnalyticBackend(agents, dt=scn.dt)

    env = ShapingParallelEnv(backend, scn, lay, baseline_mode=mode,
                             cone_half_angle=float(_req(cone, "half_angle", "viability.cone")),
                             cone_range_min=float(_req(cone, "range_min", "viability.cone")),
                             cone_range_max=float(_req(cone, "range_max", "viability.cone")))
    return env, scn, lay
