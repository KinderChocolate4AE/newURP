"""Scripted M2 rollout -> animated GIF (L1 DONE deliverable, composition root).

This is the ONE place that wires the concrete backend to the env: it imports
shepherd.sim.analytic.AnalyticBackend and INJECTS it into ShapingParallelEnv
(the env itself still never imports a concrete backend). Scripted policies only,
no torch. matplotlib Agg + PillowWriter.

Capture labelling (review note B -- do NOT conflate the two):
  * viability_capture  : the env's terminated/DoD decision = the WORST-CASE
                         viability judge FROZEN at fire (S5 robust). This is the
                         load-bearing capture.
  * trajectory_capture : did the scripted attacker's ACTUAL endpoint land inside
                         the net sphere N? Informational only -- it can disagree
                         with viability_capture (the attacker is more agile than
                         the surrogate, S14), and is NOT used for termination.
  * capture_model = "frozen_commit_worst_case".

Usage:
  python -m shepherd.scripts.rollout_gif --config configs/m2_default.yaml
"""
from __future__ import annotations
import argparse
import pathlib

import numpy as np
import yaml
# matplotlib is imported lazily inside render() so build_env()/rollout() (the
# scenario logic the tests pin) import without the viz dependency.

from shepherd.game.roles import ScenarioSpec
from shepherd.env import ShapingParallelEnv, Layout
from shepherd.sim.analytic import AnalyticBackend, AgentKin, KinematicLimits   # composition root
from shepherd.game.finisher_fsm import FinisherState
from shepherd.agents.baselines import (hold_position_limiter, scripted_shaping_limiter,
                                       scripted_finisher)

CAPTURE_MODEL = "frozen_commit_worst_case"


def _ring(n, c, r):
    return [[c[0], c[1] + r * np.cos(2 * np.pi * i / n), c[2] + r * np.sin(2 * np.pi * i / n)]
            for i in range(n)]


def build_env(cfg, mode="shaping"):
    """Compose ScenarioSpec + corridor Layout + AnalyticBackend + env (cone kwargs).

    An optional cfg["demo"] block overrides the corridor geometry + backend
    kinematic limits. Its DEFAULTS reproduce the conservative m2_default
    rendering exactly, so a config with no demo block is unaffected.
    """
    scn = ScenarioSpec.from_dict(cfg)
    cone = cfg.get("viability", {}).get("cone", {})
    d = cfg.get("demo", {})
    n = scn.n_limiters
    lim_vmax = float(d.get("limiter_v_max", 80.0))
    lim_omega = float(d.get("limiter_omega", 12.0))
    adv_vmax = float(d.get("adversary_v_max", 30.0))
    adv_x = float(d.get("adversary_start_x", 24.0))
    ep = int(d.get("episode_len", 70))
    r_ring = float(d.get("r_ring", 2.1))
    x_fire = float(d.get("x_fire", 11.0))
    lay = Layout(target=[0.0, 0, 0], limiter_p0=_ring(n, [8.0, 0, 0], 5.0),
                 finisher_p0=[2.0, 0, 0], adversary_p0=[adv_x, 0, 0],
                 adversary_v0=[-scn.adversary.speed, 0, 0], target_radius=1.0,
                 r_ring=r_ring, episode_len=ep)
    lay.x_fire = x_fire
    agents = [AgentKin(f"limiter_{i}", "limiter", KinematicLimits(scn.limiter.a_max, lim_vmax, lim_omega),
                       list(p), [0, 0, 0], [1, 0, 0]) for i, p in enumerate(lay.limiter_p0)]
    agents.append(AgentKin("finisher_0", "finisher", KinematicLimits(1.0, 1.0, scn.finisher.omega_max),
                           list(lay.finisher_p0), [0, 0, 0], [1, 0, 0]))
    agents.append(AgentKin("adversary_0", "adversary", KinematicLimits(scn.adversary.a_att_max, adv_vmax, 10.0),
                           list(lay.adversary_p0), list(lay.adversary_v0), [-1, 0, 0]))
    backend = AnalyticBackend(agents, dt=scn.dt)
    env = ShapingParallelEnv(backend, scn, lay, baseline_mode=mode,
                             cone_half_angle=float(cone.get("half_angle", 0.43)),
                             cone_range_min=float(cone.get("range_min", 0.0)),
                             cone_range_max=float(cone.get("range_max", 40.0)))
    return env, scn, lay


def rollout(env, scn, lay, mode, seed=0):
    """Run one scripted episode; return a list of per-frame records."""
    env.reset(seed=seed)
    R_lat = 0.5 * scn.adversary.a_att_max * scn.finisher.tau_deploy ** 2
    frames = []
    frozen_nc = None
    traj_cap = None
    viability_cap = False
    prev_state = env.fsm.state
    for t in range(lay.episode_len):
        lims, fin, att = env._states()
        p_att, v_att, p_fin = env._p(att), env._v(att), env._p(fin)
        trig = p_att[0] <= lay.x_fire
        acts = {}
        for i, lid in enumerate(env.limiter_ids):
            acts[lid] = (hold_position_limiter() if mode == "hold"
                         else scripted_shaping_limiter(i, env.N, env._p(lims[i]), env._v(lims[i]),
                                                       p_att, v_att, tau=env.tau_deploy,
                                                       a_max=scn.limiter.a_max,
                                                       r_ring=lay.r_ring, dt=env.dt))
        acts["finisher_0"] = scripted_finisher(p_fin, p_att, v_att, tau=env.tau_deploy,
                                               clean_threshold_crossed=trig)
        acts["adversary_0"] = np.zeros(3, np.float32)
        _, _, term, trunc, info = env.step(acts)
        fi = info["finisher_0"]

        if fi["fire_event"] and env.fsm.commit is not None:
            frozen_nc = np.asarray(env.fsm.commit.net_center, float)
        # trajectory_capture (informational): actual attacker vs frozen net sphere
        # resolved when the shot leaves LOCKED.
        if (prev_state is FinisherState.LOCKED
                and env.fsm.state in (FinisherState.SPENT, FinisherState.LOADED)
                and frozen_nc is not None):
            traj_cap = bool(np.linalg.norm(env._p(env._states()[2]) - frozen_nc) <= env.net_radius)
        viability_cap = viability_cap or bool(fi["captured"])
        prev_state = env.fsm.state

        lims2, fin2, att2 = env._states()
        frames.append(dict(
            t=t,
            limiters=[env._p(s)[:2] for s in lims2],
            kill_radius=env.kill_radius,
            finisher=env._p(fin2)[:2],
            finisher_e=env._e(fin2)[:2],
            theta=env.cone_half_angle,
            adv=env._p(att2)[:2],
            adv_head=env._e(att2)[:2],
            endpoint=(env._p(att2) + env._v(att2) * env.tau_deploy)[:2],
            R_lat=R_lat, net_radius=env.net_radius, target=np.asarray(lay.target, float)[:2],
            fsm=fi["fsm_state"], k=fi["k_remaining"],
            vsoft=fi["v_shot_soft"], vworst=fi["v_shot_worst"], delta=fi["delta_v_shot_headline"],
            clean=fi["clean_net_threshold_crossed"], boxed=fi["boxed_in"],
            fire=fi["fire_event"], committed=fi["fsm_state"] in ("DEPLOYING", "LOCKED"),
            viability_capture=viability_cap, trajectory_capture=traj_cap,
        ))
        if not env.agents:
            break
    summary = dict(viability_capture=viability_cap, trajectory_capture=traj_cap,
                   capture_model=CAPTURE_MODEL,
                   max_vshot=max(f["vsoft"] for f in frames),
                   max_delta=max(f["delta"] for f in frames),
                   clean=any(f["clean"] for f in frames),
                   boxed_steps=sum(int(f["boxed"]) for f in frames),
                   wasted=env.fsm.wasted_fire)
    return frames, summary


def _cone_polygon(apex, axis2d, half, length):
    a = np.asarray(axis2d, float)
    n = np.linalg.norm(a)
    a = np.array([1.0, 0.0]) if n < 1e-9 else a / n
    def rot(v, ang):
        c, s = np.cos(ang), np.sin(ang)
        return np.array([c * v[0] - s * v[1], s * v[0] + c * v[1]])
    e1 = rot(a, half) * length
    e2 = rot(a, -half) * length
    return np.array([apex, apex + e1, apex + e2])


def render(frames, summary, out_path, mode, scenario="m2"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation, PillowWriter
    from matplotlib.patches import Circle, Polygon

    fig, (axA, axP) = plt.subplots(1, 2, figsize=(12, 5.4),
                                   gridspec_kw={"width_ratios": [1.45, 1.0]})
    ts = [f["t"] for f in frames]
    vs = [f["vsoft"] for f in frames]
    vw = [f["vworst"] for f in frames]
    dl = [f["delta"] for f in frames]

    def update(i):
        f = frames[i]
        axA.clear()
        axA.set_title(f"M2 / L1 rollout  [{scenario}]  ({mode}, se3_cone)   t={f['t']}")
        axA.set_xlim(-3, 26); axA.set_ylim(-9, 9); axA.set_aspect("equal")
        axA.grid(alpha=0.15)
        # target
        axA.plot(*f["target"], "kx", ms=10, mew=2)
        axA.add_patch(Circle(f["target"], 1.0, fill=False, ls=":", ec="k", alpha=0.4))
        # net cone (active = filled when committed)
        poly = _cone_polygon(f["finisher"], f["finisher_e"], f["theta"],
                             min(18.0, 14.0))
        active = f["committed"]
        axA.add_patch(Polygon(poly, closed=True, fc="tab:green",
                              alpha=0.22 if active else 0.07, ec="tab:green",
                              lw=1.3 if active else 0.7))
        # finisher
        axA.plot(*f["finisher"], "s", color="tab:green", ms=11)
        # reachable-set + predicted endpoint blob
        axA.add_patch(Circle(f["endpoint"], f["R_lat"], fill=True, fc="tab:orange",
                             alpha=0.08, ec="tab:orange", ls="--", lw=0.7))
        axA.add_patch(Circle(f["endpoint"], f["net_radius"], fill=False, ec="tab:orange",
                             ls=":", alpha=0.5))
        # limiters + kill radii
        for c in f["limiters"]:
            axA.add_patch(Circle(c, f["kill_radius"], fill=True, fc="tab:red", alpha=0.10,
                                 ec="tab:red", lw=0.6))
            axA.plot(*c, ".", color="tab:red", ms=9)
        # adversary + heading
        axA.plot(*f["adv"], "o", color="tab:blue", ms=10)
        h = np.asarray(f["adv_head"], float)
        axA.arrow(f["adv"][0], f["adv"][1], 1.6 * h[0], 1.6 * h[1],
                  head_width=0.4, color="tab:blue", alpha=0.8)
        if f["fire"]:
            axA.plot(*f["finisher"], "*", color="gold", ms=26, mec="k")
            axA.text(0.5, 0.95, "FIRE", color="darkgoldenrod", fontsize=14, fontweight="bold",
                     ha="center", transform=axA.transAxes)
        axA.legend(handles=[
            plt.Line2D([], [], marker="o", color="w", mfc="tab:blue", ms=9, label="adversary"),
            plt.Line2D([], [], marker=".", color="w", mfc="tab:red", ms=12, label="limiter (kill-radius)"),
            plt.Line2D([], [], marker="s", color="w", mfc="tab:green", ms=9, label="finisher (net cone)"),
            plt.Line2D([], [], marker="o", color="w", mfc="none", mec="tab:orange", ms=9, label="reachable endpoint"),
        ], loc="lower left", fontsize=7, framealpha=0.8)

        axP.clear()
        axP.set_xlim(0, max(ts) + 1); axP.set_ylim(-0.05, 1.18)
        axP.axhline(0.8, color="gray", ls="--", lw=1, alpha=0.7)
        axP.text(0.3, 0.81, r"$\theta_{fire}=0.8$", fontsize=7, color="gray")
        axP.plot(ts[:i + 1], vs[:i + 1], "-", color="tab:purple", label=r"$v_{shot}^{soft}$")
        axP.plot(ts[:i + 1], vw[:i + 1], "-", color="tab:cyan", lw=1, label=r"$v_{shot}^{worst}$")
        axP.plot(ts[:i + 1], dl[:i + 1], "-", color="tab:olive", lw=1, label=r"$\Delta v_{shot}^{headline}$")
        axP.set_xlabel("step"); axP.set_title("viability metrics")
        axP.legend(loc="upper left", fontsize=7, ncol=1)
        tc = f["trajectory_capture"]
        txt = (f"FSM: {f['fsm']}    k={f['k']}\n"
               f"v_shot_soft = {f['vsoft']:.3f}   v_shot_worst = {f['vworst']:.0f}\n"
               f"delta_headline = {f['delta']:.3f}\n"
               f"clean_net_threshold = {f['clean']}\n"
               f"boxed_in = {f['boxed']}\n"
               f"---- capture (model = {summary['capture_model']}) ----\n"
               f"viability_capture  = {f['viability_capture']}   <- DoD / terminated\n"
               f"trajectory_capture = {tc}   (informational)")
        axP.text(0.02, -0.02, txt, transform=axP.transAxes, va="top", fontsize=8,
                 family="monospace",
                 bbox=dict(boxstyle="round", fc="#f4f4f4", ec="0.7"))
        return []

    anim = FuncAnimation(fig, update, frames=len(frames), interval=120, blit=False)
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    anim.save(str(out_path), writer=PillowWriter(fps=8))
    plt.close(fig)
    return out_path


def main():
    ap = argparse.ArgumentParser(description="Scripted M2 rollout GIF (L1).")
    ap.add_argument("--config", default="configs/m2_default.yaml")
    ap.add_argument("--output", "--out", dest="output", default="results/m2_rollout.gif")
    ap.add_argument("--mode", default="shaping", choices=["shaping", "hold"])
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    scenario = pathlib.Path(args.config).stem
    cfg = yaml.safe_load(open(args.config))
    env, scn, lay = build_env(cfg, mode=args.mode)
    frames, summary = rollout(env, scn, lay, args.mode, seed=args.seed)
    out = render(frames, summary, args.output, args.mode, scenario=scenario)
    print(f"scenario={scenario}  judge={scn.viability.judge}  net_radius={scn.finisher.net_radius}  "
          f"mode={args.mode}  frames={len(frames)}")
    print(f"max_vshot={summary['max_vshot']:.3f}  max_delta={summary['max_delta']:.3f}  "
          f"clean={summary['clean']}  boxed_steps={summary['boxed_steps']}  "
          f"wasted_fire={summary['wasted']}")
    print(f"capture_model={summary['capture_model']}  "
          f"viability_capture={summary['viability_capture']}  "
          f"trajectory_capture={summary['trajectory_capture']}")
    print(f"wrote {out}  ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
