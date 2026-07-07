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
"""
from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Dict, List, Optional, Tuple

import numpy as np

from shepherd.env_m3 import M3Params, M3ShapingEnv
from shepherd.train.adapter import ShepherdAdapter, StepResult, SHARED_FLAG_KEYS
from shepherd.train.make_env import make_train_env, pad_env_action

__all__ = ["M3_REQUIRED", "M3_OPTIONAL", "STAGE_KEYS", "M3_FLAG_KEYS", "Curriculum",
           "m3_params_from_cfg", "stage_from_cfg", "frozen_constants",
           "interp_stage", "apply_stage_env_overrides", "make_m3_train_env",
           "build_m3_attacker_env", "M3Adapter"]

M3_REQUIRED = ("o_star", "sigma_g", "w_h", "w_g", "w_gf", "lambda_cap")
M3_OPTIONAL = {"v_eff_mode": "hard", "tau_m": 3e-4, "o_hi_release": 1e-2}
STAGE_KEYS = ("half_angle", "theta_fire", "sigma_g", "w_g")

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
    unknown = set(stage_cfg) - set(STAGE_KEYS)
    if unknown:
        raise KeyError(f"unknown stage keys: {sorted(unknown)} "
                       f"(allowed: {list(STAGE_KEYS)})")
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
    return M3Params(**{**m3.__dict__, "sigma_g": float(stage["sigma_g"]),
                       "w_g": float(stage["w_g"])})


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

    def __init__(self, cur_cfg: dict, frozen: Dict[str, float]):
        self.mode = str(cur_cfg["mode"])
        if self.mode not in ("s1_only", "staged"):
            raise ValueError(f"curriculum.mode '{self.mode}' (s1_only|staged)")
        self.s1 = stage_from_cfg(cur_cfg["s1"])
        self.frozen = dict(frozen)
        self.stage = "s1"
        self.entry_step = 0
        self.history: List[dict] = [{"stage": "s1", "step": 0}]
        self._streak = 0
        self._heldout_clean: List[float] = []
        if self.mode == "staged":
            self.s1_min_steps = int(cur_cfg["s1_min_steps"])
            e1 = cur_cfg["s1_exit"]
            self.s1_clean_min = float(e1["clean_cross_min"])
            self.s1_boxed_fire_max = float(e1["boxed_fire_max"])
            self.s1_sustain = int(e1["sustain_evals"])
            self.s2_steps = int(cur_cfg["s2_steps"])
            self.s2_heldout_last = int(cur_cfg["s2_exit"]["heldout_clean_nonzero_last"])

    def overrides(self, env_steps: int) -> Optional[Dict[str, float]]:
        if self.stage == "s1":
            return dict(self.s1)
        if self.stage == "s2":
            alpha = (env_steps - self.entry_step) / max(self.s2_steps, 1)
            return interp_stage(self.s1, self.frozen, alpha)
        return None                                   # s3 -> frozen constants

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
