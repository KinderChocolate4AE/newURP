"""S14 wiring (L2 prep): the env can train on the conservative EXTREME-POINT
v_shot (n_segments>1) instead of the legacy single-segment surrogate.

Proves the knob is plumbed end-to-end
(ViabilitySpec -> ScenarioSpec.from_dict -> ShapingParallelEnv._vshot) and that
turning it on:
  - routes the per-step viability through viability.v_shot(..., n_segments=K)
    (an EXACT-equivalence check against a direct call at the env's first-step
    state -- so the env is NOT silently using the legacy single-segment path),
  - preserves common-random-number determinism for the COMA/headline differences
    (same seed -> identical coma_D), now via the SHARED seed rather than a shared
    pre-drawn accel sample.
The default (n_segments=1) path stays bit-exact and is covered by the 31 L1 tests.
"""
import numpy as np

from shepherd.game.roles import ScenarioSpec, ViabilitySpec
from shepherd.sim.analytic import AnalyticBackend, AgentKin, KinematicLimits
from shepherd.env import ShapingParallelEnv, Layout
from shepherd.game import viability as V
from shepherd.agents.baselines import scripted_shaping_limiter


def _cfg(n_segments, judge="point_mass", nsamp=800):
    cfg = {
        "scenario": {"n_limiters": 4, "n_adversaries": 1, "finisher": {"K": 1}},
        "physics": {"dt": 0.05, "tau_deploy": 0.4, "tau_lock": 0.1, "a_att_max": 30.0,
                    "att_speed": 8.0, "kill_radius": 2.0, "net_radius": 2.0, "a_lim_max": 30.0},
        "attitude": {"omega_max": 3.14159, "e_net_init": [1, 0, 0]},
        "fire_gate": {"theta_fire": 0.8, "B_capture": 1.0, "c_fire": 0.8},
        "viability": {"judge": judge, "turn_limited": False, "n_samples": nsamp,
                      "seed": 0, "n_segments": n_segments},
        "reward": {"lambda1": 1.0, "lambda2": 1.0, "lambda3": 0.5},
        "baselines": {"headline_u0": "hold_position", "coma_u0": "hold_position"}}
    return cfg


def _ring(n, c, r):
    return [[c[0], c[1] + r * np.cos(2 * np.pi * i / n), c[2] + r * np.sin(2 * np.pi * i / n)]
            for i in range(n)]


def _layout(n_lim=4):
    lay = Layout(target=[0.0, 0, 0], limiter_p0=_ring(n_lim, [8.0, 0, 0], 5.0),
                 finisher_p0=[2.0, 0, 0], adversary_p0=[18.0, 0, 0], adversary_v0=[-8, 0, 0],
                 target_radius=1.0, r_ring=2.1, episode_len=20)
    lay.x_fire = 11.0
    return lay


def _backend(scn, lay):
    ag = [AgentKin(f"limiter_{i}", "limiter", KinematicLimits(30.0, 150.0, 16.0),
                   list(p), [0, 0, 0], [1, 0, 0]) for i, p in enumerate(lay.limiter_p0)]
    ag.append(AgentKin("finisher_0", "finisher", KinematicLimits(1.0, 1.0, 3.14159),
                       list(lay.finisher_p0), [0, 0, 0], [1, 0, 0]))
    ag.append(AgentKin("adversary_0", "adversary", KinematicLimits(30.0, 20.0, 10.0),
                       list(lay.adversary_p0), list(lay.adversary_v0), [-1, 0, 0]))
    return AnalyticBackend(ag, dt=scn.dt)


def _env(n_segments, judge="point_mass"):
    scn = ScenarioSpec.from_dict(_cfg(n_segments, judge=judge))
    lay = _layout()
    return ShapingParallelEnv(_backend(scn, lay), scn, lay, baseline_mode="shaping")


def test_viabilityspec_nsegments_default_and_parse():
    """Default = legacy single-segment; from_dict key is OPTIONAL (back-compat)."""
    assert ViabilitySpec().n_segments == 1
    cfg = _cfg(4)
    assert ScenarioSpec.from_dict(cfg).viability.n_segments == 4
    del cfg["viability"]["n_segments"]                  # absent -> default 1 (all L1 configs)
    assert ScenarioSpec.from_dict(cfg).viability.n_segments == 1


def test_env_nsegments_propagates():
    assert _env(1).n_segments == 1
    assert _env(5).n_segments == 5


def test_env_nsegments_routes_through_conservative_union():
    """With n_segments>1 the env's per-step v_shot EXACTLY equals
    viability.v_shot(..., n_segments=K, seed=step_seed) at the pre-move state --
    i.e. it routes through the conservative union, NOT the legacy single-segment
    _v_shot_with_accels path (whose soft/worst would differ)."""
    K = 5
    env = _env(K, judge="point_mass")
    env.reset(seed=0)
    lims, fin, att = env._states()
    p_att, v_att = env._p(att), env._v(att)
    lim_pos = [env._p(s) for s in lims]
    step_seed = env._seed * 100003 + 1                  # _step_i -> 1 on the first env.step
    nc = env._net_center(p_att, v_att)                  # point_mass net_center = p_att + v_att*tau
    expected = V.v_shot(p_att, v_att, tau=env.tau_deploy, a_att_max=env.a_att_max,
                        judge="point_mass", net_center=nc, net_radius=env.net_radius,
                        limiters=lim_pos, kill_radius=env.kill_radius,
                        n=env.n_samples, seed=step_seed, n_segments=K)
    acts = {lid: np.zeros(4, np.float32) for lid in env.limiter_ids}   # no pre-eval limiter move
    acts["finisher_0"] = np.array([0, 0, 0, 1, 0], np.float32)         # do NOT fire
    acts["adversary_0"] = np.zeros(3, np.float32)
    _, _, _, _, info = env.step(acts)
    fi = info["finisher_0"]
    assert abs(fi["v_shot_soft"] - expected.v_shot_soft) < 1e-12
    assert fi["v_shot_worst"] == expected.v_shot_worst


def test_env_nsegments_coma_crn_deterministic():
    """n_segments>1: CRN flows through the SHARED seed (not a shared accel array).
    Same seed -> identical coma_D for every limiter."""
    def first_step_coma(seed):
        env = _env(5, judge="point_mass")
        env.reset(seed=seed)
        lims, fin, att = env._states()
        p_att, v_att = env._p(att), env._v(att)
        acts = {lid: scripted_shaping_limiter(i, env.N, env._p(lims[i]), env._v(lims[i]),
                                              p_att, v_att, tau=env.tau_deploy,
                                              a_max=env.sc.limiter.a_max,
                                              r_ring=env.layout.r_ring, dt=env.dt)
                for i, lid in enumerate(env.limiter_ids)}
        acts["finisher_0"] = np.array([0, 0, 0, 1, 0], np.float32)
        acts["adversary_0"] = np.zeros(3, np.float32)
        _, _, _, _, info = env.step(acts)
        return [info[lid]["coma_D"] for lid in env.limiter_ids]
    assert first_step_coma(0) == first_step_coma(0)
