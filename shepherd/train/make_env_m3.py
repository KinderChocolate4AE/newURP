"""M3a composition root + trainer adapter + curriculum constants (docs/11 SS2/SS3).

torch-free. STRICT config discipline, mirroring shepherd/train/make_env.py:

  * the frozen scenario YAML (configs/m2_l2_train.yaml) is NEVER edited; stage
    scaffolding constants are applied to a DEEP COPY of the parsed dict
    (viability.cone.half_angle, fire_gate.theta_fire + c_fire -- the FireGate
    R2 consistency assert requires both) exactly like attacker_rand's family
    draws;
  * M3 reward params come from the RUN config's `m3:` block via
    m3_params_from_cfg (required keys, no silent defaults); l1/l2/l3 are read
    from the frozen scenario reward block (single source of truth) and
    cross-checked inside M3ShapingEnv;
  * eval envs are built with stage=None -> FROZEN constants ALWAYS, and the m3
    base block carries the S3/JUDGMENT values (sigma_g 1.0, w_g 0.3): the
    judgment reward is identical across all training stages (docs/11 SS2
    "curriculum success = main-claim forbidden").

Curriculum stage dicts have exactly the keys STAGE_KEYS:
    half_angle  -> env cfg viability.cone.half_angle   (S1: x3 = 0.20)
    theta_fire  -> env cfg fire_gate.theta_fire+c_fire (S1: 0.8)
    sigma_g     -> M3Params.sigma_g                    (S1: x2 = 2.0)
    w_g         -> M3Params.w_g                        (S1/S2: 1.0; S3 uses base 0.3)
S2 = linear restore of (half_angle, theta_fire, sigma_g) toward frozen with w_g
held at the S1 value; S3 = stage None (frozen constants + base m3). docs/11 SS2.

A-2 scaffold keys (docs/12 SS3/SS4, NF branch; OPTIONAL per stage):
    w_gf             -> M3Params.w_gf             (L-fire commit-side boost)
    lam2_scale       -> M3Params.lam2_scale       (L-fire wasted-penalty relief)
    clean_margin_tau -> M3Params.clean_margin_tau (L-margin graded l1)
They ride through S2 at the S1 value like w_g (lam2_scale gets a post-full-width
linear restore in adaptive mode) and vanish at S3/stage=None -- the judgment m3
block cannot carry them (STRICT m3-key check), so the judged reward is
untouched (docs/12 SS1 principle 3). Curriculum mode "adaptive" (docs/12 SS3
L-adaptive) replaces the time-linear S2 ramp with a metric-gated width ladder:
advance on sustained train-eval clean, back off on stall, freeze at the step
budget cap (stall width = campaign evidence), restore lam2 after full width.
"""
from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Dict, List, Optional, Tuple

import numpy as np

from shepherd.env_m3 import M3Params, M3ShapingEnv
from shepherd.train.adapter import ShepherdAdapter, StepResult, SHARED_FLAG_KEYS
from shepherd.train.make_env import make_train_env, pad_env_action

__all__ = ["M3_REQUIRED", "M3_OPTIONAL", "STAGE_KEYS", "SCAFFOLD_KEYS",
           "M3_FLAG_KEYS", "Curriculum",
           "m3_params_from_cfg", "stage_from_cfg", "frozen_constants",
           "interp_stage", "apply_stage_env_overrides", "make_m3_train_env",
           "build_m3_attacker_env", "M3Adapter"]

M3_REQUIRED = ("o_star", "sigma_g", "w_h", "w_g", "w_gf", "lambda_cap")
M3_OPTIONAL = {"v_eff_mode": "hard", "tau_m": 3e-4, "o_hi_release": 1e-2}
STAGE_KEYS = ("half_angle", "theta_fire", "sigma_g", "w_g")
SCAFFOLD_KEYS = ("w_gf", "lam2_scale", "clean_margin_tau")  # A-2 (docs/12 SS3), optional

# extended flag set surfaced by M3Adapter (superset of the frozen adapter's)
M3_FLAG_KEYS = SHARED_FLAG_KEYS + (
    "headline_m3", "v_eff", "v_eff_base", "g_o", "r_geo_step", "r_geo_fire",
    "n_feasible", "o_dist_log", "release_event", "boxed_dwell", "fire_chains")


def _req(d, key: str, where: str):
    if not isinstance(d, Mapping):
        raise TypeError(f"config section '{where}' must be a mapping, "
                        f"got {type(d).__name__} (M3 config pins are STRICT)")
    if key not in d:
        raise KeyError(f"config missing required key '{where}.{key}' "
                       f"(M3 config pins are STRICT; see make_env_m3.py)")
    return d[key]


def m3_params_from_cfg(m3_cfg: Mapping, env_cfg: Mapping) -> M3Params:
    """Build M3Params from the run config `m3:` block (STRICT) + the frozen
    scenario reward block (l1/l2/l3 single source of truth)."""
    vals = {k: float(_req(m3_cfg, k, "m3")) for k in M3_REQUIRED}
    unknown = set(m3_cfg) - set(M3_REQUIRED) - set(M3_OPTIONAL)
    if unknown:
        raise KeyError(f"unknown m3 keys: {sorted(unknown)} "
                       f"(allowed: {list(M3_REQUIRED) + list(M3_OPTIONAL)})")
    rw = _req(env_cfg, "reward", "<env root>")
    return M3Params(
        o_star=vals["o_star"], sigma_g=vals["sigma_g"], w_h=vals["w_h"],
        w_g=vals["w_g"], w_gf=vals["w_gf"], lam_cap=vals["lambda_cap"],
        l1=float(_req(rw, "lambda1", "reward")),
        l2=float(_req(rw, "lambda2", "reward")),
        l3=float(_req(rw, "lambda3", "reward")),
        v_eff_mode=str(m3_cfg.get("v_eff_mode", M3_OPTIONAL["v_eff_mode"])),
        tau_m=float(m3_cfg.get("tau_m", M3_OPTIONAL["tau_m"])),
        o_hi_release=float(m3_cfg.get("o_hi_release",
                                      M3_OPTIONAL["o_hi_release"])))


def stage_from_cfg(stage_cfg: Mapping) -> Dict[str, float]:
    """Validate one curriculum stage dict (exactly STAGE_KEYS)."""
    stage = {k: float(_req(stage_cfg, k, "curriculum.stage")) for k in STAGE_KEYS}
    unknown = set(stage_cfg) - set(STAGE_KEYS) - set(SCAFFOLD_KEYS)
    if unknown:
        raise KeyError(f"unknown stage keys: {sorted(unknown)} "
                       f"(allowed: {list(STAGE_KEYS) + list(SCAFFOLD_KEYS)})")
    for k in SCAFFOLD_KEYS:
        if k in stage_cfg:
            stage[k] = float(stage_cfg[k])
    return stage


def frozen_constants(env_cfg: Mapping, m3: M3Params) -> Dict[str, float]:
    """The S3/judgment constants: frozen scenario cone/theta + base m3."""
    cone = _req(_req(env_cfg, "viability", "<env root>"), "cone", "viability")
    fg = _req(env_cfg, "fire_gate", "<env root>")
    return {"half_angle": float(_req(cone, "half_angle", "viability.cone")),
            "theta_fire": float(_req(fg, "theta_fire", "fire_gate")),
            "sigma_g": float(m3.sigma_g), "w_g": float(m3.w_g)}


def interp_stage(s1: Dict[str, float], frozen: Dict[str, float],
                 alpha: float) -> Dict[str, float]:
    """S2 linear restore (docs/11 SS2): alpha=0 -> S1, alpha=1 -> frozen triple
    (half_angle, theta_fire, sigma_g); w_g HOLDS at the S1 value through S2
    (it drops to the judgment value only at S3 = stage None)."""
    a = float(np.clip(alpha, 0.0, 1.0))
    out = {k: (1.0 - a) * s1[k] + a * frozen[k]
           for k in ("half_angle", "theta_fire", "sigma_g")}
    out["w_g"] = s1["w_g"]
    for k in SCAFFOLD_KEYS:               # A-2: ride at the S1 value through S2
        if k in s1:
            out[k] = s1[k]
    return out


def apply_stage_env_overrides(env_cfg: dict, stage: Optional[Dict[str, float]]) -> dict:
    """Deep-copied env cfg with the stage's ENV-level constants applied
    (half_angle; theta_fire + c_fire to satisfy the FireGate R2 assert).
    stage=None -> unmodified deep copy (frozen constants)."""
    cfg = copy.deepcopy(env_cfg)
    if stage is None:
        return cfg
    cfg["viability"]["cone"]["half_angle"] = float(stage["half_angle"])
    theta = float(stage["theta_fire"])
    b_cap = float(cfg["fire_gate"]["B_capture"])
    cfg["fire_gate"]["theta_fire"] = theta
    cfg["fire_gate"]["c_fire"] = theta * b_cap        # R2 consistency (roles.FireGate)
    return cfg


def _stage_m3(m3: M3Params, stage: Optional[Dict[str, float]]) -> M3Params:
    """M3Params with the stage's REWARD-level constants applied."""
    if stage is None:
        return m3
    upd = {"sigma_g": float(stage["sigma_g"]), "w_g": float(stage["w_g"])}
    for k in SCAFFOLD_KEYS:
        if k in stage:
            upd[k] = float(stage[k])
    return M3Params(**{**m3.__dict__, **upd})


def make_m3_train_env(env_cfg: dict, m3: M3Params,
                      stage: Optional[Dict[str, float]] = None):
    """STRICT M3 composition root. Builds through make_train_env (so every
    composition-root pin/check applies), then swaps in M3ShapingEnv on the SAME
    backend/scenario/layout. Returns (env, scn, lay).

    stage=None (EVAL path) -> frozen constants + base (judgment) m3 params."""
    cfg = apply_stage_env_overrides(env_cfg, stage)
    base_env, scn, lay = make_train_env(cfg)          # throwaway shell; reuse parts
    env = M3ShapingEnv(
        base_env.backend, scn, lay,
        baseline_mode=base_env.baseline_mode,
        capture_thresh=base_env.capture_thresh,
        cone_half_angle=base_env.cone_half_angle,
        cone_range_min=base_env.cone_range_min,
        cone_range_max=base_env.cone_range_max,
        m3=_stage_m3(m3, stage))
    return env, scn, lay


def build_m3_attacker_env(env_cfg: dict, m3: M3Params,
                          params: Dict[str, float],
                          stage: Optional[Dict[str, float]] = None):
    """make_m3_train_env on a deep-copied cfg with one attacker-family draw
    applied -- the SAME config paths as attacker_rand.build_attacker_env
    (att_speed / adversary_start_x / adversary_omega cfg patches; adv_a_max as
    the post-construction attribute set). ``env_cfg`` is never mutated."""
    cfg = copy.deepcopy(env_cfg)
    if "att_speed" in params:
        cfg["physics"]["att_speed"] = float(params["att_speed"])
    if "adversary_start_x" in params:
        cfg["train"]["layout"]["adversary_start_x"] = float(
            params["adversary_start_x"])
    if "adversary_omega" in params:
        cfg["train"]["limits"]["adversary_omega"] = float(
            params["adversary_omega"])
    env, scn, lay = make_m3_train_env(cfg, m3, stage=stage)
    if "adv_a_max" in params:
        env.adv_a_max = float(params["adv_a_max"])
    return env, scn, lay


class M3Adapter(ShepherdAdapter):
    """ShepherdAdapter with the M3 fire-chain flag superset (M3_FLAG_KEYS).

    step() mirrors the frozen adapter's step() byte-for-byte except the flag
    key set; headline stays the M2 delta_v_shot_headline (aux/non-inferiority
    logging) -- the M3 reward already lives in StepResult.rewards."""

    def reset_to(self, spawn: dict, seed: int):
        """A-3 TRAIN-ONLY spawn injection passthrough (docs/13 SS6-1)."""
        obs, _ = self.env.reset_to(spawn, seed=seed)
        self._check_obs(obs)
        return obs, self.env.state()

    def step(self, live_actions) -> StepResult:
        acts = dict(live_actions)
        acts.setdefault(self.adversary_id, np.zeros(3, np.float32))
        env_actions = {aid: pad_env_action(aid, a) for aid, a in acts.items()}
        obs, rewards, terms, truncs, infos = self.env.step(env_actions)
        self._check_obs(obs)
        terminated = any(terms.values())
        truncated = any(truncs.values())
        fin_info = infos[self.finisher_id]
        coma = {lid: float(infos[lid]["coma_D"]) for lid in self.limiter_ids}
        flags = {k: fin_info[k] for k in M3_FLAG_KEYS}
        return StepResult(
            obs=obs, rewards={a: float(r) for a, r in rewards.items()},
            terminated=terminated, truncated=truncated,
            done=bool(terminated or truncated),
            coma_D=coma, headline=float(fin_info["delta_v_shot_headline"]),
            flags=flags, state=self.env.state())

# ------------------------------------------------------------- curriculum ---
class Curriculum:
    """docs/11 SS2 stage machine. overrides() -> stage dict for the TRAIN env
    (None = frozen constants = S3); on_eval() advances stages on the ratified
    metric-gated exit conditions."""

    def __init__(self, cur_cfg: dict, frozen: Dict[str, float],
                 env_cfg: Optional[dict] = None):
        self.mode = str(cur_cfg["mode"])
        if self.mode not in ("s1_only", "staged", "adaptive", "reverse", "sbe"):
            raise ValueError(f"curriculum.mode '{self.mode}' "
                             "(s1_only|staged|adaptive|reverse|sbe)")
        self.frozen = dict(frozen)
        self.entry_step = 0
        self._streak = 0
        self._heldout_clean: List[float] = []
        if self.mode in ("reverse", "sbe"):        # A-3/A-3d ladders (docs/13/17)
            self.s1 = None                         # no width/reward stages
            self.stage = "s2"                      # ladder active from step 0
            self.history: List[dict] = [{"stage": "s2", "step": 0,
                                         "event": "enter", "r": 0}]
        else:
            self.s1 = stage_from_cfg(cur_cfg["s1"])
            self.stage = "s1"
            self.history = [{"stage": "s1", "step": 0}]
        if self.mode in ("staged", "adaptive"):
            self.s1_min_steps = int(cur_cfg["s1_min_steps"])
            e1 = cur_cfg["s1_exit"]
            self.s1_clean_min = float(e1["clean_cross_min"])
            self.s1_boxed_fire_max = float(e1["boxed_fire_max"])
            self.s1_sustain = int(e1["sustain_evals"])
            self.s2_heldout_last = int(cur_cfg["s2_exit"]["heldout_clean_nonzero_last"])
        if self.mode == "staged":
            self.s2_steps = int(cur_cfg["s2_steps"])
        if self.mode == "reverse":
            rv = cur_cfg["reverse"]
            self.rv_stages = [dict(st) for st in rv["stages"]]
            if not self.rv_stages or not self.rv_stages[-1].get("nominal"):
                raise ValueError("reverse.stages must end with a nominal stage "
                                 "(docs/13 SS2 R5)")
            for st in self.rv_stages[:-1]:
                for k in ("name", "sigma_pos", "sigma_vel", "rewind_dx",
                          "exit_clean"):
                    if k not in st:
                        raise KeyError(f"reverse stage missing '{k}': {st}")
            self.adv_sustain = int(rv["advance_sustain"])
            self.stall_evals = int(rv["stall_evals"])
            self.rv_max_steps = int(rv["max_steps"])
            self.exit_metric = str(rv.get("exit_metric", "clean_cross_rate"))
            if self.exit_metric not in ("clean_cross_rate", "captured_rate"):
                raise ValueError(f"reverse.exit_metric '{self.exit_metric}' "
                                 "(clean_cross_rate|captured_rate)")
            self.s2_heldout_last = int(
                cur_cfg["s2_exit"]["heldout_clean_nonzero_last"])
            self.r_idx = 0
            self._adv_streak = 0
            self._stall = 0
            self._capped = False
            from shepherd.train import spawn_bank as _sb   # no import cycle
            self._sb = _sb
            self.t0 = _sb.load_t0(str(rv["probe_glob"]))
            if bool(rv.get("verify_t0", True)):
                if env_cfg is None:
                    raise ValueError("reverse.verify_t0=true needs env_cfg "
                                     "(pass verify_t0: false in tests)")
                rmin = rv.get("verify_robust_min")     # A-3b R-8 gate
                rseeds = tuple(rv.get("verify_robust_seeds", (7, 8, 9)))
                self.t0, self.t0_verify = _sb.verify_t0(
                    self.t0, env_cfg, robust_seeds=rseeds,
                    robust_min=(float(rmin) if rmin is not None else None))
        if self.mode == "sbe":                     # A-3d SBE k-ladder (docs/17)
            import json as _json
            import pathlib as _pl
            from shepherd.train import spawn_bank as _sb
            self._sb = _sb
            sc = cur_cfg["sbe"]
            self.sbe_stages = [dict(s) for s in sc["stages"]]
            if not self.sbe_stages or not self.sbe_stages[-1].get("nominal"):
                raise ValueError("sbe.stages must end with a nominal stage "
                                 "(docs/17 SS2 D5)")
            for st in self.sbe_stages[:-1]:
                for kk in ("name", "k", "exit"):
                    if kk not in st:
                        raise KeyError(f"sbe stage missing '{kk}': {st}")
            self.sbe_sigma = float(sc.get("sigma_pos", 0.02))
            g = sc["gate"]                          # U-5 confidence gate
            self.gate_episodes = int(g["episodes"])
            self.gate_z = float(g.get("z", 1.645))
            self.gate_backoff_margin = float(g.get("backoff_margin", 0.05))
            self.sbe_max_steps = int(sc["max_steps"])
            self.s2_heldout_last = int(
                cur_cfg["s2_exit"]["heldout_clean_nonzero_last"])
            self.d_idx = 0
            self._capped = False
            self.t0 = _sb.load_t0(str(sc["robust_bank"]))   # D0 witnesses
            bank = _json.loads(_pl.Path(str(sc["bank"])).read_text())
            self.sbe_by_k: Dict[int, list] = {}
            for e in bank["entries"]:
                self.sbe_by_k.setdefault(int(e["k"]), []).append(e["spawn"])
            for st in self.sbe_stages[:-1]:
                if int(st["k"]) > 0 and int(st["k"]) not in self.sbe_by_k:
                    raise ValueError(f"SBE bank has no k={st['k']} entries")
        if self.mode == "adaptive":                    # A-2 L-adaptive (docs/12 SS3)
            a2 = cur_cfg["s2_adaptive"]
            self.n_width = int(a2["n_width_steps"])
            self.adv_clean_min = float(a2["advance_clean_min"])
            self.adv_sustain = int(a2["advance_sustain"])
            self.stall_evals = int(a2["stall_evals"])
            self.s2_max_steps = int(a2["max_steps"])
            self.lam2_restore_steps = int(a2["lam2_restore_steps"])
            if self.n_width < 1:
                raise ValueError("s2_adaptive.n_width_steps must be >= 1")
            self.k = 0                       # width index: 0 = S1, n_width = frozen
            self._adv_streak = 0
            self._stall = 0
            self._full_step: Optional[int] = None   # env_steps when k first == n_width
            self._capped = False

    def overrides(self, env_steps: int) -> Optional[Dict[str, float]]:
        if self.mode in ("reverse", "sbe"):
            return None      # frozen constants + judgment m3 ALWAYS (R-5/V-3)
        if self.stage == "s1":
            return dict(self.s1)
        if self.stage == "s2":
            if self.mode == "adaptive":
                stage = interp_stage(self.s1, self.frozen,
                                     self.k / self.n_width)
                if "lam2_scale" in self.s1:           # post-full-width restore
                    if self._full_step is None:
                        stage["lam2_scale"] = float(self.s1["lam2_scale"])
                    else:
                        a = min((env_steps - self._full_step)
                                / max(self.lam2_restore_steps, 1), 1.0)
                        stage["lam2_scale"] = ((1.0 - a)
                                               * float(self.s1["lam2_scale"])
                                               + a * 1.0)
                return stage
            alpha = (env_steps - self.entry_step) / max(self.s2_steps, 1)
            return interp_stage(self.s1, self.frozen, alpha)
        return None                                   # s3 -> frozen constants

    def spawn(self, rng: np.random.Generator) -> Optional[dict]:
        """A-3 per-episode spawn directive; None = nominal frozen reset.
        Only the TRAIN rollout path consumes this (R-5: eval spawns frozen
        except the train-eval gating bundle via eval_spawn_fn)."""
        if self.stage != "s2":
            return None
        if self.mode == "sbe":
            st = self.sbe_stages[self.d_idx]
            if st.get("nominal"):
                return None
            return self._sbe_draw(int(st["k"]), rng,
                                  float(st.get("sigma_pos", self.sbe_sigma)))
        if self.mode != "reverse":
            return None
        st = self.rv_stages[self.r_idx]
        if st.get("nominal"):
            return None
        t0 = self.t0[int(rng.integers(len(self.t0)))]
        return self._sb.spawn_from(
            t0, rng, sigma_pos=float(st["sigma_pos"]),
            sigma_vel=float(st["sigma_vel"]),
            rewind_dx=float(st["rewind_dx"]))

    def _sbe_draw(self, k: int, rng: np.random.Generator,
                  sigma: Optional[float] = None) -> dict:
        """One A-3d spawn: k=0 -> robust witness (zero limiter vel);
        k>0 -> SBE bank entry, POSITION jitter only (velocities exact).
        sigma: per-stage override (docs/09 (qq) A-3d' fix -- D0 anchor = 0.0;
        the global sbe_sigma had silently broken the A-3b R0 semantics)."""
        sig = self.sbe_sigma if sigma is None else float(sigma)
        if k == 0:
            t0 = self.t0[int(rng.integers(len(self.t0)))]
            return self._sb.spawn_from(t0, rng, sigma_pos=sig,
                                       sigma_vel=0.0)
        e = self.sbe_by_k[k][int(rng.integers(len(self.sbe_by_k[k])))]
        L = (np.asarray(e["limiters"], float)
             + rng.normal(0.0, sig, (len(e["limiters"]), 3)))
        return {"limiters": L,
                "limiter_v": np.asarray(e["limiter_v"], float).copy(),
                "att_p": (np.asarray(e["att_p"], float)
                          + rng.normal(0.0, sig, 3)),
                "att_v": np.asarray(e["att_v"], float).copy(),
                "att_speed": float(e["att_speed"]),
                "src": f"sbe_k{k}"}

    def eval_spawn_fn(self):
        """Deterministic spawn sampler for the TRAIN-EVAL (gating) bundle --
        stage-stable draws so the advancement metric is comparable across
        evals at the same R-stage. None -> train-eval == frozen bundle."""
        if self.stage != "s2":
            return None
        if self.mode == "sbe":
            st = self.sbe_stages[self.d_idx]
            if st.get("nominal"):
                return None
            d_idx, k = self.d_idx, int(st["k"])
            sig = float(st.get("sigma_pos", self.sbe_sigma))

            def fn(ep: int) -> dict:
                rng = np.random.default_rng(515_151 + d_idx * 991 + ep)
                return self._sbe_draw(k, rng, sig)
            return fn
        if self.mode != "reverse":
            return None
        st = self.rv_stages[self.r_idx]
        if st.get("nominal"):
            return None
        r_idx, t0s, sb = self.r_idx, self.t0, self._sb
        sp, sv, rd = (float(st["sigma_pos"]), float(st["sigma_vel"]),
                      float(st["rewind_dx"]))

        def fn(ep: int) -> dict:
            rng = np.random.default_rng(424_243 + r_idx * 991 + ep)
            t0 = t0s[int(rng.integers(len(t0s)))]
            return sb.spawn_from(t0, rng, sigma_pos=sp, sigma_vel=sv,
                                 rewind_dx=rd)
        return fn

    def on_eval(self, env_steps: int, train_ev: dict,
                frozen_ev: dict) -> Optional[str]:
        self._heldout_clean.append(float(frozen_ev["clean_cross_rate"]))
        if self.mode == "s1_only":
            return None
        if self.stage == "s1":
            cond = (train_ev["clean_cross_rate"] > self.s1_clean_min
                    and train_ev["boxed_fire_rate"] < self.s1_boxed_fire_max
                    and train_ev["fire_rate"] > 0.0)
            self._streak = self._streak + 1 if cond else 0
            if (self._streak >= self.s1_sustain
                    and env_steps - self.entry_step >= self.s1_min_steps):
                self.stage, self.entry_step, self._streak = "s2", env_steps, 0
                self.history.append({"stage": "s2", "step": env_steps})
                return "s2"
        elif self.stage == "s2" and self.mode == "sbe":
            st = self.sbe_stages[self.d_idx]
            nominal = bool(st.get("nominal"))
            if not nominal and not self._capped:
                if env_steps - self.entry_step >= self.sbe_max_steps:
                    self._capped = True            # stall stage = evidence
                    self.history.append({"stage": "s2", "step": env_steps,
                                         "event": "cap", "d": self.d_idx})
                else:
                    from shepherd.train.phi_potential import (wilson_lcb,
                                                              wilson_ucb)
                    n_ep = int(train_ev.get("episodes", 0))
                    kc = int(round(float(train_ev["captured_rate"]) * n_ep))
                    exit_p = float(st["exit"])
                    if (wilson_lcb(kc, n_ep, self.gate_z) > exit_p
                            and self.d_idx < len(self.sbe_stages) - 1):
                        self.d_idx += 1            # U-5 advance: LCB > exit
                        self.history.append(
                            {"stage": "s2", "step": env_steps,
                             "event": "advance", "d": self.d_idx})
                    elif (self.d_idx > 0
                          and wilson_ucb(kc, n_ep, self.gate_z)
                          < exit_p - self.gate_backoff_margin):
                        self.d_idx -= 1            # U-5 backoff: UCB < exit-m
                        self.history.append(
                            {"stage": "s2", "step": env_steps,
                             "event": "backoff", "d": self.d_idx})
            last = self._heldout_clean[-self.s2_heldout_last:]
            nonzero = (len(last) >= self.s2_heldout_last
                       and all(c > 0.0 for c in last))
            if nominal and nonzero:
                self.stage, self.entry_step = "s3", env_steps
                self.history.append({"stage": "s3", "step": env_steps})
                return "s3"
        elif self.stage == "s2" and self.mode == "reverse":
            st = self.rv_stages[self.r_idx]
            nominal = bool(st.get("nominal"))
            if not nominal and not self._capped:
                if env_steps - self.entry_step >= self.rv_max_steps:
                    self._capped = True            # stall stage = evidence
                    self.history.append({"stage": "s2", "step": env_steps,
                                         "event": "cap", "r": self.r_idx})
                else:
                    ok = (float(train_ev[self.exit_metric])   # T-2a (docs/13 SS9)
                          >= float(st["exit_clean"]))
                    self._adv_streak = self._adv_streak + 1 if ok else 0
                    advanced = False
                    if (self._adv_streak >= self.adv_sustain
                            and self.r_idx < len(self.rv_stages) - 1):
                        self.r_idx += 1
                        self._adv_streak = self._stall = 0
                        advanced = True
                        self.history.append(
                            {"stage": "s2", "step": env_steps,
                             "event": "advance", "r": self.r_idx})
                    if not advanced:
                        self._stall += 1
                        if ((not ok) and self._stall >= self.stall_evals
                                and self.r_idx > 0):
                            self.r_idx -= 1        # back off one R-stage
                            self._stall = self._adv_streak = 0
                            self.history.append(
                                {"stage": "s2", "step": env_steps,
                                 "event": "backoff", "r": self.r_idx})
            last = self._heldout_clean[-self.s2_heldout_last:]
            nonzero = (len(last) >= self.s2_heldout_last
                       and all(c > 0.0 for c in last))
            if nominal and nonzero:                # R5 exit (docs/13 SS2)
                self.stage, self.entry_step = "s3", env_steps
                self.history.append({"stage": "s3", "step": env_steps})
                return "s3"
        elif self.stage == "s2" and self.mode == "adaptive":
            if self._full_step is None and not self._capped:
                if env_steps - self.entry_step >= self.s2_max_steps:
                    self._capped = True               # stall width = evidence
                    self.history.append({"stage": "s2", "step": env_steps,
                                         "event": "cap", "k": self.k})
                else:
                    ok = float(train_ev["clean_cross_rate"]) >= self.adv_clean_min
                    self._adv_streak = self._adv_streak + 1 if ok else 0
                    advanced = False
                    if self._adv_streak >= self.adv_sustain and self.k < self.n_width:
                        self.k += 1
                        self._adv_streak = self._stall = 0
                        advanced = True
                        self.history.append({"stage": "s2", "step": env_steps,
                                             "event": "advance", "k": self.k})
                        if self.k == self.n_width:
                            self._full_step = env_steps
                    if not advanced:
                        self._stall += 1
                        if (not ok) and self._stall >= self.stall_evals and self.k > 0:
                            self.k -= 1               # back off one width step
                            self._stall = self._adv_streak = 0
                            self.history.append({"stage": "s2", "step": env_steps,
                                                 "event": "backoff", "k": self.k})
            restored = (self._full_step is not None
                        and ("lam2_scale" not in self.s1
                             or env_steps - self._full_step
                             >= self.lam2_restore_steps))
            last = self._heldout_clean[-self.s2_heldout_last:]
            nonzero = (len(last) >= self.s2_heldout_last
                       and all(c > 0.0 for c in last))
            if restored and nonzero:
                self.stage, self.entry_step = "s3", env_steps
                self.history.append({"stage": "s3", "step": env_steps})
                return "s3"
        elif self.stage == "s2":
            ramp_done = env_steps - self.entry_step >= self.s2_steps
            last = self._heldout_clean[-self.s2_heldout_last:]
            nonzero = (len(last) >= self.s2_heldout_last
                       and all(c > 0.0 for c in last))
            if ramp_done and nonzero:
                self.stage, self.entry_step = "s3", env_steps
                self.history.append({"stage": "s3", "step": env_steps})
                return "s3"
        return None

    def describe(self) -> dict:
        """Compact curriculum state for eval_curve points / prints (A-2)."""
        d = {"stage": self.stage, "mode": self.mode}
        if self.mode == "sbe":
            st = (self.sbe_stages[self.d_idx] if self.stage == "s2"
                  else {"name": "done"})
            d.update(d_idx=self.d_idx, d_name=st.get("name"),
                     k=st.get("k"), nominal=bool(st.get("nominal")),
                     gate_episodes=self.gate_episodes, capped=self._capped)
        if self.mode == "reverse":
            st = (self.rv_stages[self.r_idx] if self.stage == "s2"
                  else {"name": "done"})
            d.update(r_idx=self.r_idx, r_name=st.get("name"),
                     exit_metric=self.exit_metric,
                     nominal=bool(st.get("nominal")),
                     sigma_pos=st.get("sigma_pos"),
                     rewind_dx=st.get("rewind_dx"),
                     n_t0=len(self.t0), capped=self._capped)
        if self.mode == "adaptive":
            a = self.k / self.n_width
            d.update(k=self.k, n_width=self.n_width,
                     half_angle=round((1.0 - a) * float(self.s1["half_angle"])
                                      + a * float(self.frozen["half_angle"]), 4),
                     capped=self._capped,
                     lam2_restoring=self._full_step is not None)
        return d
