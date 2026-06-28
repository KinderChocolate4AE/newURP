"""PettingZoo ParallelEnv for the M2 shaping game (THE GATE composition).

Lives at shepherd/env.py (NOT shepherd/game/) so that shepherd/game/* stays
PettingZoo-free. The env COMPOSES three sim-agnostic pieces:
  - shepherd.game.finisher_fsm : magazine / deploy / lock timers (irreversible).
  - shepherd.sim.interface.EnvBackend : reduced-attitude kinematics (INJECTED;
        this module never imports shepherd.sim.analytic -- the backend instance
        is passed to the constructor).
  - shepherd.game.viability : v_shot capture-value surrogate (judge per config).

M2 DoD (the only thing this proves):
  u_L != u_L^0  =>  delta_v_shot_headline > 0  AND a CLEAN net-shot threshold
  crossing with FEWER wasted_fire than the hold_position baseline.
NO exchange frontier / sequential raid / S9-M3 economics here.

Credit-assignment split (kept separate, never mixed):
  - info[finisher]["delta_v_shot_headline"] : current shaping vs the FIXED
        hold_position limiter layout (same attacker state, common random seed).
  - info[limiter_i]["coma_D"] : same timestep, SAME accel samples
        (viability._v_shot_with_accels), limiter i replaced by its hold_position
        baseline -> D_i = v_shot(u_i,u_-i) - v_shot(u_i^0,u_-i). CRN cancels noise.
  - boxed_in is reported as containment, NEVER as a clean net-shot crossing.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np
from gymnasium import spaces
from pettingzoo import ParallelEnv

from shepherd.game.roles import ScenarioSpec
from shepherd.game.finisher_fsm import FinisherFSM, FinisherState, CommitMeta, step_fsm
from shepherd.game import viability as V
from shepherd.sim.interface import EnvBackend
from shepherd.agents.adversary import scripted_adversary_action

_EPS = 1e-12
_PHASES = [FinisherState.LOADED, FinisherState.DEPLOYING,
           FinisherState.LOCKED, FinisherState.SPENT]


def _unit(v, fallback=(1.0, 0.0, 0.0)):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return np.asarray(fallback, float) if n < _EPS else v / n


@dataclass
class Layout:
    """Geometry the env needs that the kinematic backend does not carry."""
    target: Sequence[float]                 # protected point
    limiter_p0: List[Sequence[float]]       # hold_position (u_L^0) limiter layout
    finisher_p0: Sequence[float]
    adversary_p0: Sequence[float]
    adversary_v0: Sequence[float]
    target_radius: float = 1.0              # penetration radius
    r_ring: float = 2.2                     # shaping escape-ring radius (for policies)
    episode_len: int = 80


class ShapingParallelEnv(ParallelEnv):
    """N limiters + 1 finisher + 1 (scripted) adversary. CTDE full-state obs."""

    metadata = {"name": "shepherd_m2_shaping_v0", "is_parallelizable": True}

    def __init__(self, backend: EnvBackend, scenario: ScenarioSpec, layout: Layout,
                 *, n_limiters_max: Optional[int] = None, baseline_mode: str = "shaping",
                 capture_thresh: float = 0.95, cone_half_angle: float = 0.067,
                 cone_range_min: float = 0.0, cone_range_max: float = 29.847,
                 adv_a_max: Optional[float] = None):
        # cone defaults are N1-GROUNDED (Xu et al. Drones 9:190; see
        # docs/n1_net_grounding.md): half_angle=arctan(net_radius/range_max)=0.067 rad,
        # range_max=29.847 m. The legacy tuned 0.43 rad / 40 m cone was ~6.5x over-sized
        # (effective net radius ~13.7 m) -- it is now an explicit non-gating SHOWCASE only.
        self.backend = backend                      # EnvBackend ABC (injected; NOT analytic here)
        self.sc = scenario
        self.layout = layout
        self.N = scenario.n_limiters
        self.N_max = self.N if n_limiters_max is None else int(n_limiters_max)
        self.baseline_mode = baseline_mode
        # Robust capture criterion (surrogate, S7): an evasive attacker is captured
        # iff its feasible (non-boxed) best-escape set is almost entirely inside the
        # net -- v_shot_soft >= capture_thresh. This is DISTINCT from and ABOVE the
        # fire gate theta_fire: you may FIRE at theta_fire confidence but only
        # reliably CAPTURE the evader at capture_thresh. boxed_in is limiter
        # containment, never counted as a clean net capture.
        self.capture_thresh = float(capture_thresh)
        self.cone_half_angle = float(cone_half_angle)
        self.cone_range_min = float(cone_range_min)
        self.cone_range_max = float(cone_range_max)

        # physics shortcuts
        self.dt = scenario.dt
        self.tau_deploy = scenario.finisher.tau_deploy
        self.net_radius = scenario.finisher.net_radius
        self.kill_radius = scenario.limiter.kill_radius
        self.a_att_max = scenario.adversary.a_att_max          # v_shot SURROGATE model authority
        # actual scripted-attacker agility may exceed the surrogate (S14: the
        # surrogate can underestimate the evader). Defaults to the model authority.
        self.adv_a_max = float(self.a_att_max if adv_a_max is None else adv_a_max)
        self.v_nominal = scenario.adversary.speed
        self.theta_fire = scenario.fire_gate.theta_fire
        self.judge = scenario.viability.judge
        self.n_samples = scenario.viability.n_samples
        # S14: n_segments>1 makes v_shot the conservative extreme-point (over-approx)
        # signal L2 should train on. Default 1 keeps env/DoD bit-exact with the legacy
        # single-segment surrogate (all 31 L1 tests run this path).
        self.n_segments = int(scenario.viability.n_segments)
        self.l1 = scenario.reward.lambda1
        self.l2 = scenario.reward.lambda2
        self.l3 = scenario.reward.lambda3

        self.limiter_ids = [f"limiter_{i}" for i in range(self.N)]
        self.finisher_id = "finisher_0"
        self.adversary_id = "adversary_0"
        self.possible_agents = list(self.limiter_ids) + [self.finisher_id, self.adversary_id]
        self.agents = list(self.possible_agents)

        self._obs_dim = 9 * self.N_max + 9 + 9 + 6 + 3
        self._obs_spaces = {a: spaces.Box(-np.inf, np.inf, (self._obs_dim,), np.float32)
                            for a in self.possible_agents}
        self._act_spaces = self._build_action_spaces()

        self._seed = 0
        self.fsm: FinisherFSM = FinisherFSM.new(scenario.finisher)
        self._step_i = 0
        self._pending_capture = None

    # ------------------------------------------------------------------ spaces
    def _build_action_spaces(self):
        out = {}
        a_lim = self.sc.limiter.a_max
        for lid in self.limiter_ids:
            low = np.array([-a_lim, -a_lim, -a_lim, 0.0], np.float32)
            high = np.array([a_lim, a_lim, a_lim, 1.0], np.float32)
            out[lid] = spaces.Box(low, high, dtype=np.float32)       # accel(3)+pressure(1)
        out[self.finisher_id] = spaces.Box(
            np.array([-1, -1, -1, 0, 0], np.float32),
            np.array([1, 1, 1, 1, 1], np.float32), dtype=np.float32)  # axis(3)+slew(1)+fire(1)
        a_att = self.a_att_max
        out[self.adversary_id] = spaces.Box(-a_att, a_att, (3,), np.float32)  # bounded accel
        return out

    def observation_space(self, agent):
        return self._obs_spaces[agent]

    def action_space(self, agent):
        return self._act_spaces[agent]

    # ------------------------------------------------------------------ helpers
    def _states(self):
        """Pull role-structured kinematic states from the backend."""
        obs = self.backend.observe()
        lims = obs.get("limiter", [])
        fin = obs.get("finisher", [np.zeros(9)])[0]
        att = obs.get("adversary", [np.zeros(9)])[0]
        return lims, fin, att

    @staticmethod
    def _p(s9):  # position slice
        return np.asarray(s9, float)[0:3]

    @staticmethod
    def _v(s9):  # velocity slice
        return np.asarray(s9, float)[3:6]

    @staticmethod
    def _e(s9):  # heading slice
        return np.asarray(s9, float)[6:9]

    def _net_center(self, p_att, v_att):
        return np.asarray(p_att, float) + np.asarray(v_att, float) * self.tau_deploy

    def _vshot_kwargs(self, p_att, v_att, fin_s9, net_center=None):
        if self.judge == "se3_cone":
            return dict(judge="se3_cone", net_apex=self._p(fin_s9), n_F=self._e(fin_s9),
                        theta_net=self.cone_half_angle, range_min=self.cone_range_min,
                        range_max=self.cone_range_max)
        nc = self._net_center(p_att, v_att) if net_center is None else np.asarray(net_center, float)
        return dict(judge="point_mass", net_center=nc, net_radius=self.net_radius)

    def _vshot(self, p_att, v_att, limiter_pos, fin_s9, *, accels=None, seed=0,
               net_center=None):
        kw = self._vshot_kwargs(p_att, v_att, fin_s9, net_center=net_center)
        if self.n_segments > 1:
            # S14 trustworthy signal: the conservative EXTREME-POINT reachable set.
            # Headline/COMA differences keep common-random-number cancellation via the
            # SHARED `seed` (the union's single-segment block is reachable_accels(seed);
            # the boundary/dogleg blocks are deterministic), so the pre-drawn `accels`
            # sample is intentionally unused on this path.
            return V.v_shot(p_att, v_att, tau=self.tau_deploy, a_att_max=self.a_att_max,
                            limiters=limiter_pos, kill_radius=self.kill_radius,
                            n=self.n_samples, seed=seed, n_segments=self.n_segments, **kw)
        if accels is None:
            return V.v_shot(p_att, v_att, tau=self.tau_deploy, a_att_max=self.a_att_max,
                            limiters=limiter_pos, kill_radius=self.kill_radius,
                            n=self.n_samples, seed=seed, **kw)
        return V._v_shot_with_accels(accels, p_att, v_att, tau=self.tau_deploy,
                                     limiters=limiter_pos, kill_radius=self.kill_radius,
                                     seed=seed, **kw)

    def _obs_vector(self, lims, fin, att, vres: V.VShotResult):
        parts = []
        for i in range(self.N_max):
            parts.append(np.asarray(lims[i], float) if i < len(lims) else np.zeros(9))
        parts.append(np.asarray(fin, float))
        parts.append(np.asarray(att, float))
        phase = np.array([1.0 if self.fsm.state is p else 0.0 for p in _PHASES])
        k_norm = self.fsm.k / max(self.sc.finisher.K, 1)
        parts.append(np.array([k_norm, *phase, self.fsm.timer]))
        parts.append(np.array([vres.v_shot_soft, vres.v_shot_worst, vres.p_feasible]))
        return np.concatenate(parts).astype(np.float32)

    # ------------------------------------------------------------------ API
    def reset(self, seed=None, options=None):
        self._seed = 0 if seed is None else int(seed)
        self.backend.reset(self._seed)
        self.fsm = FinisherFSM.new(self.sc.finisher)
        self._step_i = 0
        self._pending_capture = None
        self.agents = list(self.possible_agents)
        lims, fin, att = self._states()
        vres = self._vshot(self._p(att), self._v(att),
                           [self._p(s) for s in lims], fin, seed=self._seed)
        obs_vec = self._obs_vector(lims, fin, att, vres)
        obs = {a: obs_vec.copy() for a in self.agents}
        infos = {a: {} for a in self.agents}
        return obs, infos

    def step(self, actions):
        self._step_i += 1
        step_seed = self._seed * 100003 + self._step_i
        lims, fin, att = self._states()
        p_att, v_att = self._p(att), self._v(att)
        p_fin = self._p(fin)
        lim_pos = [self._p(s) for s in lims]

        # --- viability metrics on the CURRENT (pre-move) state -----------------
        accels = V.reachable_accels(self.a_att_max, self.n_samples, step_seed)
        # S14/L2: on the conservative signal (n_segments>1) build the layout-
        # INDEPENDENT reachable union ONCE and evaluate the headline + every COMA
        # counterfactual against it (different limiter masks). Makes the shared-seed
        # CRN manifest (identical endpoints/caught; only feasibility differs) and is
        # ~(N+2)x cheaper. Numerically identical to per-layout v_shot(n_segments=K)
        # (tests/test_union_equiv). n_segments==1 keeps the exact legacy accels path.
        union = None
        if self.n_segments > 1:
            union = V.build_reachable_union(
                p_att, v_att, tau=self.tau_deploy, a_att_max=self.a_att_max,
                n=self.n_samples, n_segments=self.n_segments, seed=step_seed,
                **self._vshot_kwargs(p_att, v_att, fin))

        def _vs(limiter_pos):
            if union is not None:
                return V.eval_union_with_limiters(union, limiter_pos, self.kill_radius)
            return self._vshot(p_att, v_att, limiter_pos, fin, accels=accels, seed=step_seed)

        vfull = _vs(lim_pos)
        vbase = _vs(self.layout.limiter_p0)                      # hold_position baseline
        delta_headline = vfull.v_shot_soft - vbase.v_shot_soft

        threshold_crossed = bool(vfull.v_shot_soft >= self.theta_fire)
        clean_crossed = bool(threshold_crossed and not vfull.boxed_in)

        # COMA D_i: swap limiter i to its hold_position, same accel sample (CRN)
        coma_D = {}
        for i, lid in enumerate(self.limiter_ids):
            cf = list(lim_pos)
            cf[i] = np.asarray(self.layout.limiter_p0[i], float)
            vcf = _vs(cf)
            coma_D[lid] = float(vfull.v_shot_soft - vcf.v_shot_soft)

        # --- finisher FSM (fire gate R2 enforced INSIDE the FSM) ---------------
        fin_act = np.asarray(actions.get(self.finisher_id, np.zeros(5)), float)
        fire_cmd = 1 if (len(fin_act) >= 5 and fin_act[4] > 0.5) else 0
        commit_meta = None
        if self.fsm.state is FinisherState.LOADED and fire_cmd == 1:
            nc = self._net_center(p_att, v_att)
            commit_meta = CommitMeta(t_fire=self.fsm.t, p_F=tuple(p_fin),
                                     v_F=tuple(self._v(fin)), e_net=tuple(self._e(fin)),
                                     net_center=tuple(nc), v_shot_at_commit=vfull.v_shot_soft)
        prev_state = self.fsm.state
        prev_wasted = self.fsm.wasted_fire
        # PHYSICAL capture (judge-independent): the ACTUAL attacker is inside the
        # net sphere (frozen net_center, net_radius) at deploy resolution. We freeze
        # it at the DEPLOYING->LOCKED transition and resolve it at lock end. v_shot
        # is the SURROGATE the limiters move; capture is the real outcome.
        self.fsm = step_fsm(self.fsm, fire_cmd, vfull.v_shot_soft,
                            finisher_spec=self.sc.finisher, fire_gate=self.sc.fire_gate,
                            dt=self.dt, commit_meta=commit_meta,
                            capture=self._pending_capture)
        fire_event = (prev_state is FinisherState.LOADED
                      and self.fsm.state is FinisherState.DEPLOYING)
        if fire_event:
            # Capture frozen at fire by the ROBUST (worst-case) judge (S5): the
            # best-feasible-escape attacker is caught iff NO feasible escape avoids
            # the net volume (v_shot_worst==1) AND the attacker is not merely boxed
            # by limiter kill-radii (boxed_in is containment, not a clean net-shot).
            self._pending_capture = bool((not vfull.boxed_in) and vfull.v_shot_worst >= 1.0)
        wasted_inc = self.fsm.wasted_fire - prev_wasted
        resolved = (prev_state is FinisherState.LOCKED
                    and self.fsm.state in (FinisherState.SPENT, FinisherState.LOADED))
        captured = bool(resolved and self.fsm.last_capture is True)

        # --- build backend action dict (adversary is env-scripted) -------------
        bk_action: Dict[str, dict] = {}
        for i, lid in enumerate(self.limiter_ids):
            la = np.asarray(actions.get(lid, np.zeros(4)), float)
            a_cmd = la[:3]
            bk_action[lid] = {"a": a_cmd, "e_cmd": _unit(a_cmd, self._e(lims[i]) if i < len(lims) else (1, 0, 0))}
        axis = _unit(fin_act[:3], self._e(fin)) if len(fin_act) >= 3 else self._e(fin)
        bk_action[self.finisher_id] = {"a": np.zeros(3), "e_cmd": axis}
        committed = self.fsm.state in (FinisherState.DEPLOYING, FinisherState.LOCKED)
        adv = scripted_adversary_action(
            p_att, v_att, target=self.layout.target,
            net_center=self._net_center(p_att, v_att), finisher_p=p_fin,
            limiters=lim_pos, kill_radius=self.kill_radius, a_att_max=self.adv_a_max,
            omega_att_max=8.0, v_nominal=self.v_nominal, dt=self.dt, committed=committed,
            repel_margin=1.0)
        bk_action[self.adversary_id] = adv

        self.backend.step(bk_action)

        # --- post-move state, termination --------------------------------------
        lims2, fin2, att2 = self._states()
        p_att2 = self._p(att2)
        penetrated = bool(np.linalg.norm(p_att2 - np.asarray(self.layout.target, float))
                          <= self.layout.target_radius)
        spent_fail = bool(self.fsm.state is FinisherState.SPENT and not captured)
        terminated_flag = bool(captured or penetrated or spent_fail)
        truncated_flag = bool((not terminated_flag) and self._step_i >= self.layout.episode_len)

        limiter_loss = float(sum(1 for c in lim_pos
                                 if np.linalg.norm(p_att - c) <= self.kill_radius))

        # --- reward (M2 LOCAL only) --------------------------------------------
        J = (delta_headline + self.l1 * (1.0 if clean_crossed else 0.0)
             - self.l2 * max(wasted_inc, 0) - self.l3 * limiter_loss)

        vres2 = self._vshot(p_att2, self._v(att2), [self._p(s) for s in lims2], fin2,
                            seed=step_seed)
        obs_vec = self._obs_vector(lims2, fin2, att2, vres2)

        shared = dict(
            fire_event=fire_event, wasted_fire=self.fsm.wasted_fire, fsm_state=self.fsm.state.value,
            k_remaining=self.fsm.k, judge=self.judge, limiter_loss=limiter_loss,
            baseline_mode=self.baseline_mode, v_shot_soft=vfull.v_shot_soft,
            v_shot_worst=vfull.v_shot_worst, p_feasible=vfull.p_feasible,
            p_limiter_blocked=vfull.p_limiter_blocked, boxed_in=vfull.boxed_in,
            threshold_crossed=threshold_crossed, clean_net_threshold_crossed=clean_crossed,
            captured=captured, penetrated=penetrated,
        )

        obs, rewards, terms, truncs, infos = {}, {}, {}, {}, {}
        for a in self.agents:
            obs[a] = obs_vec.copy()
            terms[a] = terminated_flag
            truncs[a] = truncated_flag
            info = dict(shared)
            if a == self.finisher_id:
                info["delta_v_shot_headline"] = float(delta_headline)
                rewards[a] = float(J)
            elif a in coma_D:
                info["coma_D"] = coma_D[a]
                rewards[a] = float(J)
            else:                                       # adversary
                rewards[a] = float(-J)
            infos[a] = info

        if terminated_flag or truncated_flag:
            self.agents = []
        return obs, rewards, terms, truncs, infos

    def render(self):
        return None

    def state(self):
        lims, fin, att = self._states()
        flat = [np.asarray(s, float) for s in lims] + [np.asarray(fin, float), np.asarray(att, float)]
        return np.concatenate(flat).astype(np.float32)

    def close(self):
        return None
