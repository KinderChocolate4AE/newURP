"""Commit-4 GATE: COMA credit split + the M2 DoD smoke.

DoD (the ONE thing M2 must show):
  u_L != u_L^0  =>  delta_v_shot_headline > 0  AND a CLEAN net-shot threshold
  crossing with STRICTLY FEWER wasted_fire than the hold_position baseline.

The smoke compares a hold_position rollout vs a scripted-shaping rollout in a
corridor fixture (se3_cone judge; limiters ring the predicted-endpoint escape
shell). Capture is the worst-case (robust) judge frozen at fire; boxed_in is
NEVER counted as a clean net-shot.

Run: python -m pytest tests/test_coma.py
"""
import numpy as np

from shepherd.game.roles import ScenarioSpec
from shepherd.sim.analytic import AnalyticBackend, AgentKin, KinematicLimits
from shepherd.env import ShapingParallelEnv, Layout
from shepherd.agents.baselines import (hold_position_limiter, scripted_shaping_limiter,
                                       scripted_finisher)

# --- LOCKED DoD corridor fixture (tuned in commit 4; geometry-only, not S1-S8) ---
N_LIM = 8
THETA = 0.43            # se3_cone half-angle: baseline soft>=0.8 (fires) with worst=0 (miss)
R_RING = 2.1           # shaping escape-ring radius on the predicted-endpoint shell
X_FIRE = 11.0          # finisher commits when the attacker crosses this x-plane
N_SAMP = 800
EP = 45


def _ring(n, c, r):
    return [[c[0], c[1] + r * np.cos(2 * np.pi * i / n), c[2] + r * np.sin(2 * np.pi * i / n)]
            for i in range(n)]


def _scenario(nsamp=N_SAMP, n_lim=N_LIM):
    return ScenarioSpec.from_dict({
        "scenario": {"n_limiters": n_lim, "n_adversaries": 1, "finisher": {"K": 1}},
        "physics": {"dt": 0.05, "tau_deploy": 0.4, "tau_lock": 0.1, "a_att_max": 30.0,
                    "att_speed": 8.0, "kill_radius": 2.0, "net_radius": 2.25, "a_lim_max": 200.0},
        "attitude": {"omega_max": 3.14159, "e_net_init": [1, 0, 0]},
        "fire_gate": {"theta_fire": 0.8, "B_capture": 1.0, "c_fire": 0.8},
        "viability": {"judge": "se3_cone", "turn_limited": False, "n_samples": nsamp, "seed": 0},
        "reward": {"lambda1": 1.0, "lambda2": 1.0, "lambda3": 0.5},
        "baselines": {"headline_u0": "hold_position", "coma_u0": "hold_position"}})


def _layout(n_lim=N_LIM):
    lay = Layout(target=[0.0, 0, 0], limiter_p0=_ring(n_lim, [8.0, 0, 0], 5.0),
                 finisher_p0=[2.0, 0, 0], adversary_p0=[18.0, 0, 0], adversary_v0=[-8, 0, 0],
                 target_radius=1.0, r_ring=R_RING, episode_len=EP)
    lay.x_fire = X_FIRE
    return lay


def _backend(scn, lay):
    ag = [AgentKin(f"limiter_{i}", "limiter", KinematicLimits(200.0, 150.0, 16.0),
                   list(p), [0, 0, 0], [1, 0, 0]) for i, p in enumerate(lay.limiter_p0)]
    ag.append(AgentKin("finisher_0", "finisher", KinematicLimits(1.0, 1.0, 3.14159),
                       list(lay.finisher_p0), [0, 0, 0], [1, 0, 0]))
    ag.append(AgentKin("adversary_0", "adversary", KinematicLimits(30.0, 20.0, 10.0),
                       list(lay.adversary_p0), list(lay.adversary_v0), [-1, 0, 0]))
    return AnalyticBackend(ag, dt=scn.dt)


def _env(mode):
    scn, lay = _scenario(), _layout()
    return ShapingParallelEnv(_backend(scn, lay), scn, lay,
                              baseline_mode=mode, cone_half_angle=THETA)


def _limiter_action(env, mode, i, lims, p_att, v_att):
    if mode == "hold":
        return hold_position_limiter()
    return scripted_shaping_limiter(i, env.N, env._p(lims[i]), env._v(lims[i]), p_att, v_att,
                                    tau=env.tau_deploy, a_max=env.sc.limiter.a_max,
                                    r_ring=env.layout.r_ring, dt=env.dt)


def _rollout(mode, seed=0):
    """Drive the locked fixture; return the DoD metrics."""
    env = _env(mode)
    env.reset(seed=seed)
    out = dict(fired=False, fire_boxed=None, max_delta=0.0, clean=False,
               captured=False, wasted=0)
    for _ in range(env.layout.episode_len):
        lims, fin, att = env._states()
        p_att, v_att, p_fin = env._p(att), env._v(att), env._p(fin)
        trig = p_att[0] <= env.layout.x_fire
        acts = {lid: _limiter_action(env, mode, i, lims, p_att, v_att)
                for i, lid in enumerate(env.limiter_ids)}
        acts["finisher_0"] = scripted_finisher(p_fin, p_att, v_att, tau=env.tau_deploy,
                                               clean_threshold_crossed=trig)
        acts["adversary_0"] = np.zeros(3, np.float32)
        _, _, _, _, info = env.step(acts)
        fi = info["finisher_0"]
        out["max_delta"] = max(out["max_delta"], fi["delta_v_shot_headline"])
        out["clean"] = out["clean"] or fi["clean_net_threshold_crossed"]
        out["captured"] = out["captured"] or fi["captured"]
        if fi["fire_event"]:
            out["fired"] = True
            out["fire_boxed"] = fi["boxed_in"]
        if not env.agents:
            break
    out["wasted"] = env.fsm.wasted_fire
    return out


# --------------------------------------------------------------------------- #
# COMA credit split
# --------------------------------------------------------------------------- #
def test_coma_held_baseline_all_zero():
    """Hold-position rollout: every limiter's current pos == its baseline, so the
    counterfactual swap changes nothing -> coma_D == 0 exactly."""
    env = _env("hold")
    env.reset(seed=0)
    acts = {lid: hold_position_limiter() for lid in env.limiter_ids}
    acts["finisher_0"] = np.array([0, 0, 0, 1, 0], np.float32)
    acts["adversary_0"] = np.zeros(3, np.float32)
    _, _, _, _, info = env.step(acts)
    for lid in env.limiter_ids:
        assert info[lid]["coma_D"] == 0.0


def test_coma_active_on_route_positive_inactive_zero():
    """Controlled point_mass corridor (the proven viability fixture): a limiter
    placed ON the active lateral escape route earns coma_D > 0; a limiter sitting
    at its hold baseline (current == u_i^0) earns coma_D == 0 exactly."""
    scn = ScenarioSpec.from_dict({
        "scenario": {"n_limiters": 2, "n_adversaries": 1, "finisher": {"K": 1}},
        "physics": {"dt": 0.05, "tau_deploy": 0.4, "tau_lock": 0.1, "a_att_max": 30.0,
                    "att_speed": 20.0, "kill_radius": 2.0, "net_radius": 1.5, "a_lim_max": 100.0},
        "attitude": {"omega_max": 3.14159, "e_net_init": [1, 0, 0]},
        "fire_gate": {"theta_fire": 0.8, "B_capture": 1.0, "c_fire": 0.8},
        "viability": {"judge": "point_mass", "turn_limited": False, "n_samples": 1500, "seed": 0},
        "reward": {"lambda1": 1.0, "lambda2": 1.0, "lambda3": 0.5},
        "baselines": {"headline_u0": "hold_position", "coma_u0": "hold_position"}})
    # baselines (u_L^0) are OFF the escape route; attacker funnels +x from origin
    lay = Layout(target=[20.0, 0, 0], limiter_p0=[[-6.0, 6, 0], [-6.0, -6, 0]],
                 finisher_p0=[16.0, 0, 0], adversary_p0=[0.0, 0, 0], adversary_v0=[20, 0, 0],
                 target_radius=1.0, r_ring=2.2, episode_len=10)
    env = ShapingParallelEnv(_backend(scn, lay), scn, lay, baseline_mode="shaping")
    env.reset(seed=0)
    # place limiter_0 ON the active escape route (mid-path ring slot), limiter_1
    # stays at its hold baseline (current == u_1^0).
    mid = np.array([4.0, 0.0, 0.0])                  # p_att + v*tau*0.5 = origin + [4,0,0]
    env.backend.by_name("limiter_0").p = mid + np.array([0.0, 2.2, 0.0])
    env.backend.by_name("limiter_1").p = np.asarray(lay.limiter_p0[1], float)

    acts = {"limiter_0": np.zeros(4, np.float32), "limiter_1": np.zeros(4, np.float32),
            "finisher_0": np.array([0, 0, 0, 1, 0], np.float32),   # don't fire
            "adversary_0": np.zeros(3, np.float32)}
    _, _, _, _, info = env.step(acts)
    assert info["limiter_0"]["coma_D"] > 0.0          # on-route limiter shapes v_shot up
    assert info["limiter_1"]["coma_D"] == 0.0         # baseline-parked limiter contributes 0


def test_coma_shared_sample_deterministic():
    """Same seed -> identical coma_D (common random numbers / shared accel sample)."""
    def first_step_D(seed):
        env = _env("shaping")
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
    assert first_step_D(0) == first_step_D(0)


# --------------------------------------------------------------------------- #
# M2 DoD smoke (the load-bearing gate)
# --------------------------------------------------------------------------- #
def test_dod_smoke_shaping_beats_hold():
    """u_L != u_L^0  =>  delta_v_shot_headline > 0  AND a clean (non-boxed) net-shot
    threshold crossing with STRICTLY FEWER wasted_fire than the hold baseline."""
    base = _rollout("hold")
    shape = _rollout("shaping")

    # both finishers actually commit their single shot
    assert base["fired"] and shape["fired"]
    # the shaping lever moved v_shot
    assert shape["max_delta"] > 0.0
    # CLEAN crossing: the fire step is a real net-shot, not limiter containment
    assert shape["clean"] is True
    assert shape["fire_boxed"] is False
    # the payoff: shaping captures with no wasted shot; hold wastes its shot
    assert shape["captured"] is True
    assert shape["wasted"] == 0
    assert base["captured"] is False
    assert base["wasted"] >= 1
    assert shape["wasted"] < base["wasted"]           # STRICTLY fewer wasted_fire


def test_capture_model_is_frozen_worst_case_not_trajectory():
    """Note B: capture (terminated/DoD) = the WORST-CASE viability judge FROZEN at
    fire, NOT the scripted attacker's actual endpoint. In the hold baseline the
    fire step has v_shot_worst == 0 (a feasible escape avoids the net), so the env
    reports NO capture -- regardless of where the attacker's actual trajectory
    lands. capture_model == 'frozen_commit_worst_case'."""
    env = _env("hold")
    env.reset(seed=0)
    fired = False
    fire_worst = None
    for _ in range(env.layout.episode_len):
        lims, fin, att = env._states()
        p_att, v_att, p_fin = env._p(att), env._v(att), env._p(fin)
        trig = p_att[0] <= env.layout.x_fire
        acts = {lid: hold_position_limiter() for lid in env.limiter_ids}
        acts["finisher_0"] = scripted_finisher(p_fin, p_att, v_att, tau=env.tau_deploy,
                                               clean_threshold_crossed=trig)
        acts["adversary_0"] = np.zeros(3, np.float32)
        _, _, _, _, info = env.step(acts)
        fi = info["finisher_0"]
        if fi["fire_event"]:
            fired = True
            fire_worst = fi["v_shot_worst"]
        if not env.agents:
            break
    assert fired is True
    assert fire_worst == 0.0                  # worst-case judge says the attacker can escape
    assert env.fsm.last_capture is False      # -> env's capture decision is the worst-case one


def test_clean_viability_demo_reporting_is_consistent_and_honest():
    """configs/m2_clean_viability_demo.yaml shows the M2 DoD UNDER THE CONE judge
    via the shaping lever, at the GROUNDED net size (net_radius == 1.5), with
    HONEST capture reporting (no cherry-picking, no net enlargement):
      - viability_capture (worst-case CONTINUOUS reachable set in the cone) == True
      - trajectory_capture (actual discrete endpoint in the SAME cone)      == False
        -> S14 surrogate-fidelity: the closed-loop attacker overshoots the
           single-segment reachable surrogate and EXITS the cone (v_shot optimistic).
      - tight_net_probe_1p5m (actual endpoint in a tight 1.5 m sphere)       == False
        -> N1 physical-net caveat.
      - clean (non-boxed-at-fire) crossing, delta>0, wasted(shaping) < wasted(hold).
    We do NOT assert trajectory_capture or the tight sphere is True -- forcing
    that would require shrinking the dodge (cherry-pick); the disagreement IS the
    S14 / N1 finding, reported via summary['surrogate_fidelity']."""
    import pathlib
    import yaml
    import shepherd.scripts.rollout_gif as RG          # build_env/rollout import w/o matplotlib
    cfg = yaml.safe_load(open(pathlib.Path(__file__).resolve().parents[1]
                              / "configs" / "m2_clean_viability_demo.yaml"))

    def run(mode):
        env, scn, lay = RG.build_env(cfg, mode=mode)
        frames, summ = RG.rollout(env, scn, lay, mode, seed=0)
        fire_boxed = next((f["boxed"] for f in frames if f["fire"]), None)
        return summ, fire_boxed, scn.finisher.net_radius

    base, _, _ = run("hold")
    shape, shape_fire_boxed, net_r = run("shaping")

    assert net_r == 1.5                              # grounded net size, NOT enlarged
    assert shape["max_delta"] > 0.0                  # shaping lever moved v_shot
    assert shape["clean"] is True
    assert shape_fire_boxed is False                 # clean crossing at fire (NOT boxed containment)
    assert shape["viability_capture"] is True        # worst-case CONTINUOUS reachable set in the cone
    # honest S14 finding: the actual discrete attacker exits the same cone
    assert shape["trajectory_capture"] is False
    assert "tight_net_probe_1p5m" in shape           # N1 probe reported...
    assert shape["tight_net_probe_1p5m"] is False    # ...tight physical net would MISS
    assert "SE(3) cone" in shape["net_model"]
    assert "UNGROUNDED" in shape["net_model"]         # net model labelled ungrounded
    assert "S14" in shape["surrogate_fidelity"]       # surrogate-fidelity verdict surfaced
    assert "exits cone" in shape["surrogate_fidelity"]
    assert base["wasted"] >= 1
    assert shape["wasted"] < base["wasted"]          # strictly fewer wasted_fire than hold
