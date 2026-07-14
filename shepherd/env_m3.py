"""M3a "capture-unlock" reward-geometry env variant (docs/11 v0.2, ratified 2026-07-07).

NON-frozen M3 lane. Subclasses the FROZEN ShapingParallelEnv (shepherd/env.py,
which stays byte-identical) and overrides reset()/step() ONLY to swap the
reward geometry; everything else -- kinematic backend, finisher FSM + R2 fire
gate, CRN viability plumbing (batched union eval), scripted adversary,
termination, obs layout -- is inherited/copied unchanged from the frozen step.

Reward (docs/11 SS1; grounded in the P4 verdict "feasibility acquitted,
findability guilty", docs/09 (s)/(t)/(u)):

    v_eff       = v_soft * 1[not boxed]              # HARD gate = MAIN
    headline_M3 = v_eff(full) - v_eff(hold)          # M2-consistent hold-vs LEVEL
                                                     # form, SIGNED
    g(o)        = exp(-(ln o - ln o*)^2 / (2 sigma_g^2)),  g(0) = 0
    r_geo_step  = v_soft * g(o)
    r_geo_fire  = v_soft * g(o) * 1[fire_event]
    J_M3a       = w_h*headline_M3 + w_g*r_geo_step + w_gf*r_geo_fire
                  + l1*1[clean] + lam_cap*1[captured]
                  - l2*wasted_inc - l3*limiter_loss

Ratified invariants enforced by this module:
  * headline_M3 stays SIGNED -- transitions into boxed keep their full negative
    level; NO positive-only / max(0, .) clipping anywhere (docs/11 SS1).
  * v_eff_mode="hard" is the MAIN path; "smooth" (sigmoid in o - o*) exists as
    an ablation/debug knob ONLY and must never back a main claim (docs/11 SS1).
  * obs layout UNCHANGED (o = p_feasible is already obs[-1]; boxed ==
    (p_feasible == 0) is derivable) -> mix-0.5 L2 checkpoints stay
    shape-compatible for the ratified warm-start arm (docs/11 SS3).
  * limiter coma_D stays the M2 v_soft CRN difference -- M3a changes the SHARED
    reward only. info["delta_v_shot_headline"] still reports the M2 v_soft
    headline (continuity + docs/11 SS4 non-inferiority aux); the REWARD uses
    headline_m3.
  * near-capture auxiliary terms are FORBIDDEN in this first implementation
    (docs/11 SS1 modification 4; reserved as a second-line prescription).

Fire-chain decomposition logging (docs/11 SS3, required at eval): shared info
gains the per-step M3 terms + release_event / boxed_dwell trackers, and
info["fire_chains"] carries one record per fire with the state frozen at
commit (v_soft/v_eff/o/n_feasible/boxed/clean, fire_step, |ln o - ln o*|,
release_event_before_fire, boxed_dwell_before_fire) and the shot outcome
(captured/wasted) filled in at resolution.

Curriculum scaffolding constants (half_angle / theta_fire / sigma_g / w_g) are
injected by the M3 composition root (shepherd/train/make_env_m3.py); eval envs
are ALWAYS built with frozen constants (docs/11 SS2). torch-free.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from shepherd.env import ShapingParallelEnv, _unit
from shepherd.game import viability as V
from shepherd.game.finisher_fsm import CommitMeta, FinisherState, step_fsm
from shepherd.agents.adversary import scripted_adversary_action

__all__ = ["M3Params", "M3ShapingEnv", "g_geo", "v_effective",
           "m3_step_terms", "release_transition"]


# ------------------------------------------------------------- pure pieces ---
def g_geo(o: float, o_star: float, sigma_g: float) -> float:
    """Inverted-U geometry bonus in ln o (docs/11 SS1 (B)): g(o*) = 1, g(0) = 0,
    symmetric in ln o around ln o*."""
    o = float(o)
    if o <= 0.0:
        return 0.0
    z = (math.log(o) - math.log(float(o_star))) / float(sigma_g)
    return float(math.exp(-0.5 * z * z))


def v_effective(v_soft: float, boxed: bool, o: float, *, mode: str = "hard",
                o_star: float = 1e-3, tau_m: float = 3e-4) -> float:
    """docs/11 SS1 (A). mode="hard" (MAIN): v * 1[not boxed] -- removes the
    boxed/clean headline equivalence (P4/M3 design requirement A). mode=
    "smooth": v * sigmoid((o - o*)/tau_m), an ABLATION/debug knob only --
    forbidden as the default and for main claims (docs/11 SS1)."""
    if mode == "hard":
        return float(v_soft) * (0.0 if boxed else 1.0)
    if mode == "smooth":
        return float(v_soft) / (1.0 + math.exp(-(float(o) - float(o_star)) / float(tau_m)))
    raise ValueError(f"unknown v_eff_mode '{mode}' (expected 'hard' or 'smooth')")


def release_transition(prev_o: Optional[float], o: float, o_hi: float) -> bool:
    """Release event (docs/11 SS3): the feasibility fraction o transitions
    0 -> (0, o_hi] between consecutive pre-move states (the non-radial
    release-channel signature measured in P4, docs/09 (u))."""
    if prev_o is None:
        return False
    return float(prev_o) <= 0.0 and 0.0 < float(o) <= float(o_hi)


@dataclass(frozen=True)
class M3Params:
    """J_M3a weights + geometry knobs (docs/11 SS1 run-1 start values, except
    w_g whose JUDGMENT/S3 value is 0.3 -- the S1/S2 scaffold raises it to 1.0
    via the curriculum, docs/11 SS2). l1/l2/l3 mirror scenario.reward and are
    cross-checked against the env's own values at construction."""
    o_star: float = 1e-3
    sigma_g: float = 1.0
    w_h: float = 1.0
    w_g: float = 1.0
    w_gf: float = 1.0
    lam_cap: float = 5.0
    l1: float = 1.0
    l2: float = 1.0
    l3: float = 0.5
    v_eff_mode: str = "hard"
    tau_m: float = 3e-4
    o_hi_release: float = 1e-2
    # --- A-2 scaffold knobs (docs/12 SS3/SS4, NF branch; STAGE-injected ONLY).
    # Judgment-neutral defaults reproduce the ratified J_M3a bit-for-bit
    # (docs/12 SS1 principle 3): the run-config m3: block cannot set these
    # (STRICT key check in make_env_m3); they enter via curriculum stage dicts
    # and vanish at S3 / stage=None.
    lam2_scale: float = 1.0        # L-fire: scales l2 (wasted) during scaffold
    clean_margin_tau: float = 0.0  # L-margin: >0 -> graded l1*sigmoid((v-theta)/tau)*1[not boxed]


def m3_step_terms(*, v_full: float, boxed_full: bool, o_full: float,
                  v_base: float, boxed_base: bool, o_base: float,
                  fire_event: bool, clean: bool, captured: bool,
                  wasted_inc: float, limiter_loss: float,
                  p: M3Params,
                  clean_margin: Optional[float] = None) -> Dict[str, float]:
    """Pure J_M3a assembly (docs/11 SS1) -- unit-testable, no env state.

    INVARIANT (ratified): headline_m3 = v_eff(full) - v_eff(hold) is returned
    and consumed SIGNED. This function performs no clipping of any kind.

    A-2 scaffolds (docs/12 SS3, stage-only): p.clean_margin_tau > 0 swaps the
    binary l1 clean bonus for the graded L-margin form l1 * sigmoid(
    clean_margin / tau) * 1[not boxed] (clean_margin = v_soft - theta_fire of
    the CURRENT stage env, passed by the caller); p.lam2_scale scales the l2
    wasted penalty (L-fire). With the default M3Params both paths are
    bit-identical to the ratified judgment J."""
    ve = v_effective(v_full, boxed_full, o_full, mode=p.v_eff_mode,
                     o_star=p.o_star, tau_m=p.tau_m)
    vb = v_effective(v_base, boxed_base, o_base, mode=p.v_eff_mode,
                     o_star=p.o_star, tau_m=p.tau_m)
    headline_m3 = ve - vb                              # SIGNED level form
    g_o = g_geo(o_full, p.o_star, p.sigma_g)
    r_geo_step = float(v_full) * g_o
    r_geo_fire = r_geo_step if fire_event else 0.0     # commit-state v * g(o)
    if p.clean_margin_tau > 0.0:
        if clean_margin is None:
            raise ValueError(
                "clean_margin_tau > 0 requires clean_margin (= v_soft - "
                "theta_fire of the CURRENT stage env); the composition root "
                "always passes it -- direct callers must too")
        l1_term = (0.0 if boxed_full else
                   p.l1 / (1.0 + math.exp(-float(clean_margin)
                                          / p.clean_margin_tau)))
    else:
        l1_term = p.l1 * (1.0 if clean else 0.0)
    J = (p.w_h * headline_m3
         + p.w_g * r_geo_step
         + p.w_gf * r_geo_fire
         + l1_term
         + p.lam_cap * (1.0 if captured else 0.0)
         - p.l2 * p.lam2_scale * max(float(wasted_inc), 0.0)
         - p.l3 * float(limiter_loss))
    return {"v_eff": ve, "v_eff_base": vb, "headline_m3": float(headline_m3),
            "g_o": g_o, "r_geo_step": r_geo_step, "r_geo_fire": r_geo_fire,
            "l1_term": float(l1_term), "J": float(J)}


# ------------------------------------------------------------------ the env ---
class M3ShapingEnv(ShapingParallelEnv):
    """M3a capture-unlock env: frozen M2 mechanics, new reward geometry.

    step() is a faithful copy of the frozen ShapingParallelEnv.step() with the
    reward assembly swapped for m3_step_terms + fire-chain logging appended.
    Any future edit to the frozen step() must be mirrored here (drift guard:
    tests/test_env_m3.py::test_m2_equivalence_when_unboxed)."""

    metadata = {"name": "shepherd_m3a_capture_unlock_v0", "is_parallelizable": True}

    def __init__(self, backend, scenario, layout, *, m3: Optional[M3Params] = None,
                 **base_kwargs):
        super().__init__(backend, scenario, layout, **base_kwargs)
        if m3 is None:
            m3 = M3Params(l1=self.l1, l2=self.l2, l3=self.l3)
        for name, mine in (("l1", self.l1), ("l2", self.l2), ("l3", self.l3)):
            if abs(getattr(m3, name) - mine) > 1e-12:
                raise ValueError(
                    f"M3Params.{name}={getattr(m3, name)} != scenario reward "
                    f"{name}={mine} (single source of truth = the frozen "
                    "scenario YAML reward block)")
        if m3.v_eff_mode not in ("hard", "smooth"):
            raise ValueError(f"v_eff_mode '{m3.v_eff_mode}' invalid")
        self.m3 = m3
        self._reset_m3_trackers(p_feasible0=None)

    # --------------------------------------------------------------- helpers
    def _reset_m3_trackers(self, p_feasible0: Optional[float]) -> None:
        self._prev_o: Optional[float] = p_feasible0
        self._boxed_dwell: int = 0            # pre-move boxed states seen so far
        self._release_seen: bool = False      # any release event so far
        self._fire_chains: List[dict] = []    # one record per fire (K=1 -> <=1)

    @staticmethod
    def _o_dist_log(o: float, o_star: float) -> float:
        return abs(math.log(o) - math.log(o_star)) if o > 0.0 else float("nan")

    # ------------------------------------------------------------------- API
    def reset_to(self, spawn: dict, seed=None, options=None):
        """TRAIN-ONLY spawn injection (A-3 L-reverse, docs/13 SS6-1; R-5).

        Normal reset() first (seed/FSM/trackers), then overwrite the backend
        kinematic states with the spawn dict ({"limiters": (N,3), "att_p": 3,
        "att_v": 3}) and recompute viability + obs at the injected state.
        The finisher is NEVER moved (frame contract, docs/13 SS1). No eval
        path may call this -- eval bundles/harnesses reset() only (STRICT
        lock: tests/test_a3_reverse.py)."""
        self.reset(seed=seed, options=options)
        if not hasattr(self.backend, "by_name"):
            raise TypeError("reset_to needs a backend with mutable named "
                            "agent states (AnalyticBackend); RotorPy-style "
                            "backends need their own injection adapter")
        L = np.asarray(spawn["limiters"], float)
        if L.shape != (len(self.limiter_ids), 3):
            raise ValueError(f"spawn['limiters'] shape {L.shape} != "
                             f"({len(self.limiter_ids)}, 3)")
        for i, lid in enumerate(self.limiter_ids):
            a = self.backend.by_name(lid)
            a.p = L[i].copy()
            a.v = np.zeros(3)
        att = self.backend.by_name(self.adversary_id)
        att.p = np.asarray(spawn["att_p"], float).copy()
        att.v = np.asarray(spawn["att_v"], float).copy()
        lims, fin, att_s = self._states()
        vres = self._vshot(self._p(att_s), self._v(att_s),
                           [self._p(s) for s in lims], fin, seed=self._seed)
        obs_vec = self._obs_vector(lims, fin, att_s, vres)
        self._reset_m3_trackers(p_feasible0=float(obs_vec[-1]))
        obs = {a: obs_vec.copy() for a in self.agents}
        infos = {a: {} for a in self.agents}
        return obs, infos

    def reset(self, seed=None, options=None):
        obs, infos = super().reset(seed=seed, options=options)
        # seed the release tracker with the reset-state feasibility (same
        # geometry as step 1's pre-move state; only the sample seed differs)
        o0 = float(obs[self.possible_agents[0]][-1])   # obs[-1] == p_feasible
        self._reset_m3_trackers(p_feasible0=o0)
        return obs, infos

    def step(self, actions):
        # ==== copy of the frozen ShapingParallelEnv.step() (pre-reward part) ====
        self._step_i += 1
        step_seed = self._seed * 100003 + self._step_i
        lims, fin, att = self._states()
        p_att, v_att = self._p(att), self._v(att)
        p_fin = self._p(fin)
        lim_pos = [self._p(s) for s in lims]

        accels = V.reachable_accels(self.a_att_max, self.n_samples, step_seed)
        union = None
        if self.n_segments > 1:
            union = V.build_reachable_union(
                p_att, v_att, tau=self.tau_deploy, a_att_max=self.a_att_max,
                n=self.n_samples, n_segments=self.n_segments, seed=step_seed,
                **self._vshot_kwargs(p_att, v_att, fin))

        def _vs(limiter_pos):
            if union is not None:
                return V.eval_union_with_limiters(union, limiter_pos, self.kill_radius)
            return self._vshot(p_att, v_att, limiter_pos, fin, accels=accels,
                               seed=step_seed)

        if union is not None:
            cfs = []
            for i in range(len(self.limiter_ids)):
                cf = list(lim_pos)
                cf[i] = np.asarray(self.layout.limiter_p0[i], float)
                cfs.append(cf)
            res = V.eval_union_with_limiter_sets(
                union, [lim_pos, self.layout.limiter_p0] + cfs, self.kill_radius)
            vfull, vbase = res[0], res[1]
            coma_D = {lid: float(vfull.v_shot_soft - res[2 + i].v_shot_soft)
                      for i, lid in enumerate(self.limiter_ids)}
        else:
            vfull = _vs(lim_pos)
            vbase = _vs(self.layout.limiter_p0)
            coma_D = {}
            for i, lid in enumerate(self.limiter_ids):
                cf = list(lim_pos)
                cf[i] = np.asarray(self.layout.limiter_p0[i], float)
                vcf = _vs(cf)
                coma_D[lid] = float(vfull.v_shot_soft - vcf.v_shot_soft)
        delta_headline = vfull.v_shot_soft - vbase.v_shot_soft

        threshold_crossed = bool(vfull.v_shot_soft >= self.theta_fire)
        clean_crossed = bool(threshold_crossed and not vfull.boxed_in)

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
        self.fsm = step_fsm(self.fsm, fire_cmd, vfull.v_shot_soft,
                            finisher_spec=self.sc.finisher, fire_gate=self.sc.fire_gate,
                            dt=self.dt, commit_meta=commit_meta,
                            capture=self._pending_capture)
        fire_event = (prev_state is FinisherState.LOADED
                      and self.fsm.state is FinisherState.DEPLOYING)
        if fire_event:
            self._pending_capture = bool((not vfull.boxed_in) and vfull.v_shot_worst >= 1.0)
        wasted_inc = self.fsm.wasted_fire - prev_wasted
        resolved = (prev_state is FinisherState.LOCKED
                    and self.fsm.state in (FinisherState.SPENT, FinisherState.LOADED))
        captured = bool(resolved and self.fsm.last_capture is True)

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

        lims2, fin2, att2 = self._states()
        p_att2 = self._p(att2)
        penetrated = bool(np.linalg.norm(p_att2 - np.asarray(self.layout.target, float))
                          <= self.layout.target_radius)
        spent_fail = bool(self.fsm.state is FinisherState.SPENT and not captured)
        terminated_flag = bool(captured or penetrated or spent_fail)
        truncated_flag = bool((not terminated_flag) and self._step_i >= self.layout.episode_len)

        limiter_loss = float(sum(1 for c in lim_pos
                                 if np.linalg.norm(p_att - c) <= self.kill_radius))
        # ==== end of the copied frozen pre-reward step ==========================

        # --- M3a reward geometry (docs/11 SS1) --------------------------------
        o_full = float(vfull.p_feasible)
        terms = m3_step_terms(
            v_full=float(vfull.v_shot_soft), boxed_full=bool(vfull.boxed_in),
            o_full=o_full,
            v_base=float(vbase.v_shot_soft), boxed_base=bool(vbase.boxed_in),
            o_base=float(vbase.p_feasible),
            fire_event=fire_event, clean=clean_crossed, captured=captured,
            wasted_inc=wasted_inc, limiter_loss=limiter_loss, p=self.m3,
            clean_margin=float(vfull.v_shot_soft) - float(self.theta_fire))
        J = terms["J"]

        # --- fire-chain trackers (docs/11 SS3) ---------------------------------
        release_event = release_transition(self._prev_o, o_full,
                                           self.m3.o_hi_release)
        self._release_seen = self._release_seen or release_event
        if vfull.boxed_in:
            self._boxed_dwell += 1
        if fire_event:
            self._fire_chains.append({
                "fire_step": int(self._step_i),
                "v_soft": float(vfull.v_shot_soft),
                "v_eff": terms["v_eff"],
                "o": o_full,
                "n_feasible": int(vfull.n_feasible),
                "boxed": bool(vfull.boxed_in),
                "clean": bool(clean_crossed),
                "o_dist_log": self._o_dist_log(o_full, self.m3.o_star),
                "release_event_before_fire": bool(self._release_seen),
                "boxed_dwell_before_fire": int(self._boxed_dwell),
                "captured": None,               # filled at resolution
                "wasted": None,                 # filled at resolution
            })
        if resolved and self._fire_chains:
            fc = self._fire_chains[-1]
            if fc["captured"] is None:
                fc["captured"] = bool(captured)
                fc["wasted"] = bool(wasted_inc > 0)
        self._prev_o = o_full

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
            # ---- M3 additions (docs/11 SS1/SS3) ----
            headline_m3=terms["headline_m3"], v_eff=terms["v_eff"],
            v_eff_base=terms["v_eff_base"], g_o=terms["g_o"],
            r_geo_step=terms["r_geo_step"], r_geo_fire=terms["r_geo_fire"],
            n_feasible=int(vfull.n_feasible),
            o_dist_log=self._o_dist_log(o_full, self.m3.o_star),
            release_event=bool(release_event),
            boxed_dwell=int(self._boxed_dwell),
            fire_chains=[dict(fc) for fc in self._fire_chains],
        )

        obs, rewards, terms_d, truncs, infos = {}, {}, {}, {}, {}
        for a in self.agents:
            obs[a] = obs_vec.copy()
            terms_d[a] = terminated_flag
            truncs[a] = truncated_flag
            info = dict(shared)
            if a == self.finisher_id:
                info["delta_v_shot_headline"] = float(delta_headline)   # M2 aux
                rewards[a] = float(J)
            elif a in coma_D:
                info["coma_D"] = coma_D[a]                              # UNCHANGED
                rewards[a] = float(J)
            else:                                                       # adversary
                rewards[a] = float(-J)
            infos[a] = info

        if terminated_flag or truncated_flag:
            self.agents = []
        return obs, rewards, terms_d, truncs, infos
