"""CENTRAL PARAMETER REGISTRY -- every knob in newURP, one file, with provenance.

(2026-07-03 code-review session deliverable.)

WHY THIS FILE EXISTS
--------------------
Parameters live in four different places today:
  1. configs/*.yaml            (ratified scenario values; m2_l2_train.yaml is FROZEN)
  2. constructor kwargs        (ShapingParallelEnv: capture_thresh, cone_*, adv_a_max)
  3. hardcoded constants       (frozen shepherd/env.py; adversary/baseline policy
                                gains; viability sampler internals -- the make_env
                                backend limits were promoted to train.limits config
                                keys on 2026-07-03)
  4. prototype constants       (N1 net forward model -- frozen evidence, doc-only)

This registry is the SINGLE PLACE to (a) SEE every parameter with its value, units,
provenance and consumer, and (b) MANIPULATE every parameter that is actually
wireable without violating the freeze discipline (docs/09 SS0: shepherd/env.py,
docs/03, configs/m2_l2_train.yaml, shepherd/game/exchange.py are FROZEN, diff 0).

    from shepherd.params import as_config
    from shepherd.train.make_env import make_train_env
    env, scn, lay = make_train_env(as_config())                  # ratified values
    env, scn, lay = make_train_env(as_config({"physics.tau_deploy": 0.5}))  # override

    from shepherd.params import as_ppo_config       # PPOConfig kwargs (Phase 1 toy)

    python -m shepherd.params    # provenance table + frozen-YAML drift check

FREEZE SAFETY. This file NEVER mutates the frozen YAML. `check_frozen_yaml()`
asserts that the registry's ratified defaults still equal configs/m2_l2_train.yaml
-- so the registry cannot silently drift from the frozen contract. Experimenting =
pass an `overrides` dict to as_config() (the frozen file stays untouched).

STATUS legend (measured vs assumed -- the review's key ask):
  MEASURED    anchored to an external published number (Xu et al. Drones 2025, 9:190).
  DERIVED     computed from MEASURED values by a stated formula.
  CALIBRATED  fit once against a measurement, then frozen (incl. the fire-gate
              calibration against the exact analytic containment label).
  ASSUMED     scenario assumption -- plausible, NOT externally grounded (most of
              the M2 fixture: attacker agility, speeds, kill radius, dt, ...).
  TUNED       hand-tuned for demo/convergence; explicitly non-physical.
  RESERVED    present in the contract but intentionally inert (parsed-but-unwired).
  DEAD        accepted by code but has NO effect on behavior (documented bug-level
              finding; kept for the frozen contract's sake).

WIRED legend (can you change it HERE and have it take effect?):
  config       yes -- flows through as_config() -> make_train_env()/ScenarioSpec.
  ppo-config   yes -- flows through as_ppo_config() -> PPOConfig.
  kwarg        partially -- a constructor default; make_train_env does not expose it,
               so changing it needs a direct ShapingParallelEnv(...) call.
  code-default a Python function/dataclass default; change at the cited source line
               (file is NOT frozen) or pass the kwarg at the call site.
  frozen-code  hardcoded inside FROZEN shepherd/env.py -- changing requires a
               ratified freeze exception (docs/09 SS0). Listed for visibility only.
  doc-only     prototype / evidence constant; not consumed by the live pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

__all__ = ["Param", "PARAMS", "as_config", "as_ppo_config", "check_frozen_yaml"]


@dataclass(frozen=True)
class Param:
    value: Any
    units: str          # "-" if dimensionless
    status: str         # MEASURED | DERIVED | CALIBRATED | ASSUMED | TUNED | RESERVED | DEAD
    wired: str          # config | ppo-config | kwarg | code-default | frozen-code | doc-only
    where: str          # consumer (file:symbol)
    source: str         # where the NUMBER comes from
    note: str = ""


# ============================================================================
# 1. M2/L2 TRAINING SCENARIO -- ratified 2026-06-26/30, mirrors the FROZEN
#    configs/m2_l2_train.yaml. wired=config: edit here -> as_config() -> env.
# ============================================================================
PARAMS: Dict[str, Param] = {

    # --- scenario ------------------------------------------------------------
    "scenario.n_limiters": Param(4, "-", "ASSUMED", "config",
        "roles.ScenarioSpec / env ring layout",
        "S1 ratified fixture (docs/03)",
        "shaping team size; Fig-7-style N ablation is future work"),
    "scenario.n_adversaries": Param(1, "-", "ASSUMED", "config",
        "roles.ScenarioSpec", "M2 scope (single scripted attacker)"),
    "scenario.finisher.K": Param(1, "shots", "ASSUMED", "config",
        "roles.FinisherSpec / finisher_fsm", "S1: binding scarce resource; M2 K=1",
        "K>1 economics = S9/M3 only"),

    # --- physics ---------------------------------------------------------------
    "physics.dt": Param(0.05, "s", "ASSUMED", "config",
        "AnalyticBackend / FSM tick", "sim convention (20 Hz)"),
    "physics.tau_deploy": Param(0.4, "s", "ASSUMED", "config",
        "FinisherSpec; v_shot horizon; net_center prediction",
        "scenario assumption (prototype reachset fixture)",
        "R_reach = 0.5*a_att_max*tau^2 = 2.40 m depends on this; N1 flip is "
        "conditioned on it (capture returns at tau<=0.365 s, docs/n1 SS3)"),
    "physics.tau_lock": Param(0.1, "s", "ASSUMED", "config",
        "FinisherSpec / FSM LOCKED phase", "S3 irreversible-commit fixture"),
    "physics.a_att_max": Param(30.0, "m/s^2", "ASSUMED", "config",
        "AdversarySpec; v_shot surrogate authority; adversary backend a_max",
        "fixture (~3 g); whether 3 g / 0.4 s is the operational FPV regime is an "
        "open assumptions-register question (docs/n1 post-review #3)",
        "capture returns at a<=25 (net_radius 2.0, tau 0.4)"),
    "physics.att_speed": Param(20.0, "m/s", "ASSUMED", "config",
        "AdversarySpec.speed; spawn v0; scripted forward drive", "fixture"),
    "physics.kill_radius": Param(2.0, "m", "ASSUMED", "config",
        "LimiterSpec; viability no-go filter; limiter_loss count",
        "kamikaze lethality fixture (no external grounding)"),
    "physics.net_radius": Param(2.0, "m", "DERIVED", "config",
        "FinisherSpec; point_mass judge; physical-capture sphere",
        "N1-GROUNDED: sqrt(S_NP/pi), S_NP=12.54 m^2 paper baseline (Xu Drones 9:190); "
        "sim reproduces 1.998",
        "CAVEAT (post-review): equivalent-AREA radius, NOT worst-case inradius -- "
        "r_in <= 2.0, so real net is smaller in the worst direction"),
    "physics.a_lim_max": Param(30.0, "m/s^2", "ASSUMED", "config",
        "LimiterSpec.a_max; limiter action-space bound", "fixture (= attacker authority)"),

    # --- attitude (R3 reduced-attitude, NOT 6-DOF aero) -----------------------
    "attitude.omega_max": Param(3.14159, "rad/s", "ASSUMED", "config",
        "FinisherSpec.omega_max -> finisher backend slew limit",
        "R3 parameter choice (half turn per second)"),
    "attitude.e_net_init": Param((1.0, 0.0, 0.0), "unit vec", "ASSUMED", "config",
        "FinisherSpec.e_net", "corridor geometry (net points +x at the corridor)"),

    # --- viability (v_shot surrogate) -----------------------------------------
    "viability.judge": Param("se3_cone", "-", "ASSUMED", "config",
        "viability.v_shot dispatch", "S5/S8 channel-2 model choice",
        "point_mass = ablation / port-fidelity judge only"),
    "viability.turn_limited": Param(False, "-", "RESERVED", "config",
        "roles.ViabilitySpec (parsed) -- NOT wired into env's v_shot path",
        "docs/09 SS2 (2026-07-03): parsed-but-inert; viability.py already supports "
        "attacker_turn_limited; wire-through deferred to S13/S14"),
    "viability.n_samples": Param(2000, "samples", "CALIBRATED", "config",
        "reachable_accels / union Block-1",
        "2A' spike (2026-07-03): n-cut UNSAFE near the gate (n=500 err_max 0.190 > "
        "zero-waste band width 0.15) -> 2000 ratified for training; n-cuts debug-only"),
    "viability.seed": Param(0, "-", "ASSUMED", "config",
        "ViabilitySpec.seed", "reproducibility convention"),
    "viability.n_segments": Param(4, "segments", "ASSUMED", "config",
        "S14 conservative extreme-point union (doglegs use ceil(K/2)+rest split)",
        "S14 ratified: >1 = trustworthy conservative signal L2 trains on; "
        "1 = legacy bit-exact prototype path (L1 tests)"),
    "viability.cone.half_angle": Param(0.067, "rad", "DERIVED", "config",
        "_caught_se3_cone theta_net",
        "N1: arctan(net_radius/range_max) = arctan(1.998/29.8) = 0.067 (3.8 deg); "
        "tightest cone containing the net capture cylinder",
        "legacy tuned 0.43 rad was ~6.5x oversized -> showcase-only now"),
    "viability.cone.range_min": Param(0.0, "m", "ASSUMED", "config",
        "_caught_se3_cone axial band", "unchanged from tuned era"),
    "viability.cone.range_max": Param(29.847, "m", "DERIVED", "config",
        "_caught_se3_cone axial band",
        "N1 WEAK/FLAGGED: min{sim coverage-window travel 29.8, paper-T travel 69.0}; "
        "sim collapse timing untrustworthy -> conservative smaller value adopted"),

    # --- fire gate (R2 single source of truth) --------------------------------
    "fire_gate.theta_fire": Param(0.9, "-", "CALIBRATED", "config",
        "FSM fire gate: fire iff v_shot_soft >= theta_fire",
        "fire_gate_calibration.py vs EXACT analytic ball-in-sphere label: "
        "zero-wasted-shot band [0.85, 1.0], recommendation 0.925 (mid-band); "
        "0.9 adopted (in-band). Legacy 0.8 sits BELOW the band (would waste shots)",
        "docs/10 proposition: theta in (5/6, 1] is the shaping-forcing window -- "
        "0.9 is inside it, consistent"),
    "fire_gate.B_capture": Param(1.0, "-", "ASSUMED", "config",
        "FireGate (economic doc value)", "normalization choice"),
    "fire_gate.c_fire": Param(0.9, "-", "DERIVED", "config",
        "FireGate consistency assert", "== theta_fire * B_capture (asserted in roles.FireGate)"),

    # --- reward (S6) -----------------------------------------------------------
    "reward.lambda1": Param(1.0, "-", "ASSUMED", "config",
        "env J: threshold-crossing bonus", "S6 ratified weight (no sweep yet)"),
    "reward.lambda2": Param(1.0, "-", "ASSUMED", "config",
        "env J: wasted-fire penalty", "S6 ratified weight"),
    "reward.lambda3": Param(0.5, "-", "ASSUMED", "config",
        "env J: limiter-loss penalty", "S6 ratified weight"),

    # --- credit-assignment baselines (S8, FIXED) -------------------------------
    "baselines.headline_u0": Param("hold_position", "-", "ASSUMED", "config",
        "env vbase layout", "S8: fixed baseline (vary per-step = reward hacking)"),
    "baselines.coma_u0": Param("hold_position", "-", "ASSUMED", "config",
        "env coma_D counterfactual", "S8 fixed baseline"),

    # --- train block (composition-root pins, 2026-07-03) -----------------------
    "train.episode_len": Param(80, "steps", "ASSUMED", "config",
        "Layout.episode_len -> truncation horizon (4 s at dt=0.05)",
        "env contract (docs/09 SS2); demo root uses 70 (rendering-only legacy)"),
    "train.layout.target": Param((0.0, 0.0, 0.0), "m", "ASSUMED", "config",
        "Layout.target (protected point)", "corridor geometry (L1 demo-proven)"),
    "train.layout.target_radius": Param(1.0, "m", "ASSUMED", "config",
        "penetration radius", "corridor geometry"),
    "train.layout.ring_center": Param((8.0, 0.0, 0.0), "m", "ASSUMED", "config",
        "hold-position limiter ring center (u_L^0)", "corridor geometry"),
    "train.layout.ring_radius": Param(5.0, "m", "ASSUMED", "config",
        "hold-position limiter ring radius", "corridor geometry"),
    "train.layout.r_ring": Param(2.1, "m", "TUNED", "config",
        "scripted-shaping escape-ring radius (baselines only; learned policies ignore)",
        "L1 demo tuning"),
    "train.layout.finisher_p0": Param((2.0, 0.0, 0.0), "m", "ASSUMED", "config",
        "finisher spawn", "corridor geometry"),
    "train.layout.adversary_start_x": Param(24.0, "m", "ASSUMED", "config",
        "adversary spawn x", "corridor geometry"),
    "train.layout.x_fire": Param(11.0, "m", "TUNED", "config",
        "scripted-finisher trigger (baseline rollouts only)", "L1 demo tuning"),
    "train.limits.limiter_v_max": Param(80.0, "m/s", "ASSUMED", "config",
        "limiter backend speed clip", "demo-proven backend limit"),
    "train.limits.limiter_omega": Param(12.0, "rad/s", "ASSUMED", "config",
        "limiter backend heading slew", "demo-proven backend limit"),
    "train.limits.adversary_v_max": Param(30.0, "m/s", "ASSUMED", "config",
        "adversary backend speed clip", "demo-proven backend limit (headroom over 20)"),

    # ========================================================================
    # 2. ENV CONSTRUCTOR KWARGS (not exposed by make_train_env)
    # ========================================================================
    "env.capture_thresh": Param(0.95, "-", "DEAD", "kwarg",
        "ShapingParallelEnv.__init__ (stored as self.capture_thresh)",
        "docstring claims 'captured iff v_shot_soft >= capture_thresh'",
        "FINDING (2026-07-03 review): stored but NEVER read -- the actual capture "
        "rule is frozen-at-fire (not boxed_in) AND v_shot_worst >= 1.0 (env.py step). "
        "env.py frozen -> document, don't fix"),
    "env.n_limiters_max": Param(None, "-", "ASSUMED", "kwarg",
        "obs zero-padding width (9*N_max block)", "defaults to n_limiters"),
    "env.baseline_mode": Param("shaping", "-", "ASSUMED", "kwarg",
        "info tag only", "make_train_env(mode=...)"),
    "env.adv_a_max": Param(None, "m/s^2", "ASSUMED", "kwarg",
        "actual scripted-attacker authority (may exceed the v_shot surrogate's, S14)",
        "defaults to physics.a_att_max (surrogate == actual in M2)"),

    # ========================================================================
    # 3. HARDCODED INSIDE FROZEN shepherd/env.py (visibility only)
    # ========================================================================
    "env_frozen.step_seed_multiplier": Param(100003, "-", "ASSUMED", "frozen-code",
        "env.step: step_seed = seed*100003 + step_i", "prime stride for CRN streams"),
    "env_frozen.fire_cmd_threshold": Param(0.5, "-", "ASSUMED", "frozen-code",
        "env.step: fire iff fin_act[4] > 0.5", "binary decode of the fire logit"),
    "env_frozen.adversary_omega_att_max": Param(8.0, "rad/s", "DEAD", "frozen-code",
        "env.step -> scripted_adversary_action(omega_att_max=8.0)",
        "FINDING: the scripted policy ACCEPTS but never USES omega_att_max (heading "
        "slew is enforced by the backend, which uses 10.0 rad/s from make_env.py). "
        "8.0 vs 10.0 mismatch is inert today"),
    "env_frozen.adversary_repel_margin": Param(1.0, "kill_radius mult", "ASSUMED",
        "frozen-code", "env.step -> scripted_adversary_action(repel_margin=1.0)",
        "env overrides the function's own default 1.5"),
    "env_frozen.capture_rule": Param("(not boxed_in) and v_shot_worst >= 1.0 at fire",
        "-", "ASSUMED", "frozen-code",
        "env.step fire_event -> _pending_capture, resolved at lock end",
        "S5 robust worst-case judge frozen at commit"),

    # ========================================================================
    # 4. SCRIPTED-POLICY GAINS (files NOT frozen; change at source or call site)
    #    docs/09 SS7: v_nominal, a_lat_max, amp, react_on_commit + spawn geometry
    #    are the ratified 2B domain-randomization knobs -- config wiring lands in 2B.
    # ========================================================================
    "adversary.fwd_gain": Param(4.0, "1/s", "TUNED", "code-default",
        "agents/adversary.py: a_fwd = 4.0*(v_nominal - v_fwd)*fwd",
        "P-gain hand-tuned for the corridor"),
    "adversary.dodge_amp": Param(1.8, "x a_lat_max", "TUNED", "code-default",
        "agents/adversary.py: post-commit lateral dodge amplitude",
        "deploy-delay escape attempt strength; 0 before commit"),
    "adversary.react_on_commit": Param(True, "-", "ASSUMED", "code-default",
        "agents/adversary.py", "S4: physical commitment reaction (not signaling)"),
    "adversary.a_lat_max": Param(None, "m/s^2", "ASSUMED", "code-default",
        "agents/adversary.py lateral dodge bound", "defaults to a_att_max"),
    "adversary.repel_margin_default": Param(1.5, "kill_radius mult", "TUNED",
        "code-default", "agents/adversary.py signature default",
        "OVERRIDDEN to 1.0 by frozen env.py -- the 1.5 never runs in the M2 env"),
    "scripted.limiter_kp": Param(8.0, "1/s^2", "TUNED", "code-default",
        "agents/baselines.scripted_shaping_limiter PD", "L1 demo tuning"),
    "scripted.limiter_kd": Param(4.0, "1/s", "TUNED", "code-default",
        "agents/baselines.scripted_shaping_limiter PD", "damps ring-slot overshoot"),
    "scripted.limiter_pressure": Param(1.0, "-", "RESERVED", "code-default",
        "Box(4) idx 3 -- env receives-and-ignores (reserved dim)",
        "docs/09 SS2 reserved-dim decision"),
    "scripted.finisher_slew_cmd": Param(1.0, "-", "RESERVED", "code-default",
        "Box(5) idx 3 -- env receives-and-ignores (reserved dim)", "same decision"),

    # ========================================================================
    # 5. VIABILITY SAMPLER INTERNALS (viability.py -- NOT frozen, defaults)
    # ========================================================================
    "sampler.n_t": Param(24, "substeps", "ASSUMED", "code-default",
        "limiter no-go collision test per segment", "prototype-parity value"),
    "sampler.n_dir": Param(32, "directions", "ASSUMED", "code-default",
        "_extreme_dirs Fibonacci+rng boundary directions",
        "finite-witness density: worst==1 is NOT a containment certificate "
        "(post-review caveat in viability.py)"),
    "sampler.n_azimuth": Param(8, "curves", "ASSUMED", "code-default",
        "_turn_curve_segments (turn-limited only; currently a sound no-op)",
        "load-bearing only once true rate-limited dynamics replace the accel-cone proxy"),
    "sampler.turn_safety": Param(0.999, "-", "ASSUMED", "code-default",
        "_turn_curve_segments cone-edge factor", "numerical margin"),

    # ========================================================================
    # 6. BACKEND ASSEMBLY (promoted to train.limits config keys, 2026-07-03
    #    GPT-review fix -- previously hardcoded in make_env.py)
    # ========================================================================
    "train.limits.finisher_a_max": Param(1.0, "m/s^2", "ASSUMED", "config",
        "make_env.py AgentKin finisher limits (env commands a=0 anyway)",
        "finisher is effectively stationary in M2; only its heading slews"),
    "train.limits.finisher_v_max": Param(1.0, "m/s", "ASSUMED", "config",
        "make_env.py AgentKin finisher limits", "same"),
    "train.limits.adversary_omega": Param(10.0, "rad/s", "ASSUMED", "config",
        "make_env.py AgentKin adversary heading slew",
        "the ACTUAL adversary heading limit (the 8.0 passed to the policy is dead)"),

    # ========================================================================
    # 7. PPO (Phase 1 toy -- configs/ppo_toy.yaml; NOT the shepherd scenario)
    # ========================================================================
    "ppo.total_timesteps": Param(300_000, "steps", "TUNED", "ppo-config",
        "PPOConfig", "Pendulum-v1 convergence budget"),
    "ppo.rollout_steps": Param(2048, "steps", "TUNED", "ppo-config", "PPOConfig", "standard"),
    "ppo.epochs": Param(10, "-", "TUNED", "ppo-config", "PPOConfig", "standard"),
    "ppo.minibatch_size": Param(64, "-", "TUNED", "ppo-config", "PPOConfig", "standard"),
    "ppo.lr": Param(3e-4, "-", "TUNED", "ppo-config", "PPOConfig", "standard Adam lr"),
    "ppo.max_grad_norm": Param(0.5, "-", "TUNED", "ppo-config", "PPOConfig", "standard"),
    "ppo.clip_eps": Param(0.2, "-", "TUNED", "ppo-config", "PPOConfig", "standard"),
    "ppo.gamma": Param(0.9, "-", "TUNED", "ppo-config", "PPOConfig",
        "PENDULUM-TUNED (0.99 is the general default) -- docs/09 SS7.1: must be "
        "re-set for shepherd (episode_len=80, dt=0.05)"),
    "ppo.lam": Param(0.95, "-", "TUNED", "ppo-config", "PPOConfig", "standard GAE lambda"),
    "ppo.ent_coef": Param(0.0, "-", "TUNED", "ppo-config", "PPOConfig", ""),
    "ppo.vf_coef": Param(0.5, "-", "TUNED", "ppo-config", "PPOConfig", ""),
    "ppo.hidden_sizes": Param((64, 64), "-", "TUNED", "ppo-config", "PPOConfig", ""),
    "ppo.init_log_std": Param(0.0, "-", "TUNED", "ppo-config", "PPOConfig",
        "docs/09 SS7.1: possibly too wide for shepherd's action space -- retune in 2B"),
    "ppo.seed": Param(0, "-", "ASSUMED", "ppo-config", "PPOConfig", ""),
    "ppo.device": Param("cpu", "-", "ASSUMED", "ppo-config", "PPOConfig", ""),
    "ppo.eval.interval_updates": Param(5, "updates", "TUNED", "ppo-config",
        "train_ppo_toy eval cadence", ""),
    "ppo.eval.episodes": Param(10, "episodes", "TUNED", "ppo-config",
        "train_ppo_toy eval averaging", ""),

    # ========================================================================
    # 8. N1 NET FORWARD MODEL (prototypes/net_forward.py -- frozen evidence,
    #    doc-only here; these are where the DERIVED cone constants come from)
    # ========================================================================
    "n1.rope_diameter": Param(2.181167e-3, "m", "MEASURED", "doc-only",
        "net_forward.D_ROPE", "Xu Drones 9:190 Table 1"),
    "n1.elastic_modulus": Param(0.305e9, "Pa", "MEASURED", "doc-only",
        "net_forward.E_MOD", "paper Table 1"),
    "n1.mesh_edge_l0": Param(0.52, "m", "MEASURED", "doc-only",
        "net_forward.L0", "paper (5.2 m net, 10x10 cells)"),
    "n1.damping_ratio": Param(0.05, "-", "MEASURED", "doc-only",
        "net_forward.ZETA", "paper Table 1"),
    "n1.rho_rope": Param(970.0, "kg/m^3", "MEASURED", "doc-only",
        "net_forward.RHO_ROPE", "paper (D3 flag: 970 not 1440; benign, damping-only)"),
    "n1.net_mass": Param(0.170, "kg", "MEASURED", "doc-only",
        "net_forward.M_W", "paper measured net mass"),
    "n1.sigma_break": Param(30.0e6, "Pa", "MEASURED", "doc-only",
        "net_forward.SIGMA_B", "paper max allowable tensile stress"),
    "n1.operating_point": Param("theta=45deg, v=60 m/s, m_block=35 g", "-",
        "MEASURED", "doc-only", "ground_cone.BASELINE", "paper baseline shot"),
    "n1.S_NP_baseline": Param(12.54, "m^2", "MEASURED", "doc-only",
        "back-solved S_UAV/(1-ln C), C=2.3174", "paper baseline effective area",
        "sim reproduces 12.54 (but rho_air is calibrated TO this point -- anchor, "
        "not independent evidence)"),
    "n1.S_UAV": Param(2.0, "m^2", "ASSUMED", "doc-only",
        "net_forward.S_UAV_DEFAULT (coverage C)", "paper's UAV cross-section value"),
    "n1.rho_air": Param(1.513, "kg/m^3", "CALIBRATED", "doc-only",
        "net_forward.RHO_AIR_CAL (the single free knob)",
        "fit so baseline S_NP matches 12.54, then frozen; ~24% above atmospheric "
        "1.225 -- absorbs the model's drag shortfall (flagged)"),
    "n1.engage_dist": Param(20.0, "m", "ASSUMED", "doc-only",
        "net_forward.ENGAGE_DIST (S_NP read distance)", "pre-fixed, NOT per-config tuned"),
    "n1.hang_time_paper": Param(1.853, "s", "MEASURED", "doc-only",
        "ground_cone.PAPER_BASELINE_T", "paper value; sim does NOT reproduce it "
        "(breathing-net limitation -> all sim-temporal outputs untrusted)"),

    # ========================================================================
    # 9. DERIVED QUANTITIES + LEGACY/DEMO CONSTANTS (context for review)
    # ========================================================================
    "derived.R_reach": Param(2.4, "m", "DERIVED", "doc-only",
        "0.5 * a_att_max * tau_deploy^2 (free reachable ball radius)",
        "= 0.5*30*0.4^2; net_radius 2.0 < 2.4 -> baseline-net absolute capture "
        "honestly fails; L2 target = shaped reachable radius < 2.0 m"),
    "derived.zero_waste_band": Param((0.85, 1.0), "-", "CALIBRATED", "doc-only",
        "results/fire_gate_calibration.md", "thetas firing only when robustly contained"),
    "derived.theta_fire_recommended": Param(0.925, "-", "CALIBRATED", "doc-only",
        "fire_gate_calibration recommend_theta (mid-band)",
        "0.9 adopted instead (also in-band, docs/10-consistent)"),
    "legacy.theta_fire": Param(0.8, "-", "TUNED", "doc-only",
        "roles.FireGate dataclass default; m2_default.yaml; rollout_gif plot line",
        "legacy single-segment-era gate; BELOW the conservative zero-waste band",
        "NOTE: rollout_gif.render() hardcodes the 0.8 line/label -- stale for "
        "m2_l2_train (0.9) GIFs"),
    "legacy.cone_half_angle": Param(0.43, "rad", "TUNED", "doc-only",
        "m2_clean_viability_demo.yaml; tests THETA_SHOWCASE",
        "non-gating optimistic showcase only (~13.7 m effective radius at 30 m)"),
    "legacy.cone_range_max": Param(40.0, "m", "TUNED", "doc-only",
        "showcase cone range", "same showcase"),
    "demo.tight_net_probe_radius": Param(1.5, "m", "ASSUMED", "doc-only",
        "rollout_gif.TIGHT_NET_RADIUS (N1 probe sphere)", "pre-N1 net_radius value"),
    "demo.episode_len": Param(70, "steps", "TUNED", "doc-only",
        "rollout_gif.build_env demo default",
        "!= train contract 80; rendering-only legacy -- training must use make_train_env"),
}


# ---------------------------------------------------------------------------
# config emitters
# ---------------------------------------------------------------------------
def _v(key: str, overrides: Optional[Dict[str, Any]]) -> Any:
    if overrides and key in overrides:
        return overrides[key]
    val = PARAMS[key].value
    return list(val) if isinstance(val, tuple) else val


def as_config(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Emit the m2_l2_train-equivalent config dict from the registry.

    ``make_train_env(as_config())`` builds the ratified training env. Pass
    ``overrides={"dotted.key": value}`` to experiment WITHOUT touching the
    frozen YAML. Only wired=config keys are consumed here.
    """
    o = overrides
    return {
        "scenario": {
            "n_limiters": _v("scenario.n_limiters", o),
            "n_adversaries": _v("scenario.n_adversaries", o),
            "finisher": {"K": _v("scenario.finisher.K", o)},
        },
        "physics": {
            "dt": _v("physics.dt", o),
            "tau_deploy": _v("physics.tau_deploy", o),
            "tau_lock": _v("physics.tau_lock", o),
            "a_att_max": _v("physics.a_att_max", o),
            "att_speed": _v("physics.att_speed", o),
            "kill_radius": _v("physics.kill_radius", o),
            "net_radius": _v("physics.net_radius", o),
            "a_lim_max": _v("physics.a_lim_max", o),
        },
        "attitude": {
            "omega_max": _v("attitude.omega_max", o),
            "e_net_init": _v("attitude.e_net_init", o),
        },
        "viability": {
            "judge": _v("viability.judge", o),
            "turn_limited": _v("viability.turn_limited", o),
            "n_samples": _v("viability.n_samples", o),
            "seed": _v("viability.seed", o),
            "n_segments": _v("viability.n_segments", o),
            "cone": {
                "half_angle": _v("viability.cone.half_angle", o),
                "range_min": _v("viability.cone.range_min", o),
                "range_max": _v("viability.cone.range_max", o),
            },
        },
        "fire_gate": {
            "theta_fire": _v("fire_gate.theta_fire", o),
            "B_capture": _v("fire_gate.B_capture", o),
            "c_fire": _v("fire_gate.c_fire", o),
        },
        "reward": {
            "lambda1": _v("reward.lambda1", o),
            "lambda2": _v("reward.lambda2", o),
            "lambda3": _v("reward.lambda3", o),
        },
        "baselines": {
            "headline_u0": _v("baselines.headline_u0", o),
            "coma_u0": _v("baselines.coma_u0", o),
        },
        "train": {
            "episode_len": _v("train.episode_len", o),
            "layout": {
                "target": _v("train.layout.target", o),
                "target_radius": _v("train.layout.target_radius", o),
                "ring_center": _v("train.layout.ring_center", o),
                "ring_radius": _v("train.layout.ring_radius", o),
                "r_ring": _v("train.layout.r_ring", o),
                "finisher_p0": _v("train.layout.finisher_p0", o),
                "adversary_start_x": _v("train.layout.adversary_start_x", o),
                "x_fire": _v("train.layout.x_fire", o),
            },
            "limits": {
                "limiter_v_max": _v("train.limits.limiter_v_max", o),
                "limiter_omega": _v("train.limits.limiter_omega", o),
                "adversary_v_max": _v("train.limits.adversary_v_max", o),
                "finisher_a_max": _v("train.limits.finisher_a_max", o),
                "finisher_v_max": _v("train.limits.finisher_v_max", o),
                "adversary_omega": _v("train.limits.adversary_omega", o),
            },
        },
    }


def as_ppo_config(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """PPOConfig kwargs from the registry (Phase 1 toy values)."""
    o = overrides
    return {
        "total_timesteps": _v("ppo.total_timesteps", o),
        "rollout_steps": _v("ppo.rollout_steps", o),
        "epochs": _v("ppo.epochs", o),
        "minibatch_size": _v("ppo.minibatch_size", o),
        "lr": _v("ppo.lr", o),
        "max_grad_norm": _v("ppo.max_grad_norm", o),
        "clip_eps": _v("ppo.clip_eps", o),
        "gamma": _v("ppo.gamma", o),
        "lam": _v("ppo.lam", o),
        "ent_coef": _v("ppo.ent_coef", o),
        "vf_coef": _v("ppo.vf_coef", o),
        "hidden_sizes": tuple(_v("ppo.hidden_sizes", o)),
        "init_log_std": _v("ppo.init_log_std", o),
        "seed": _v("ppo.seed", o),
        "device": _v("ppo.device", o),
    }


# ---------------------------------------------------------------------------
# frozen-YAML drift check
# ---------------------------------------------------------------------------
def _deep_compare(a: Any, b: Any, path: str, out: list) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f"{path}.{k}: missing in registry")
            elif k not in b:
                out.append(f"{path}.{k}: missing in YAML")
            else:
                _deep_compare(a[k], b[k], f"{path}.{k}", out)
    elif isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            out.append(f"{path}: length {len(a)} != {len(b)}")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                _deep_compare(x, y, f"{path}[{i}]", out)
    elif isinstance(a, float) or isinstance(b, float):
        if abs(float(a) - float(b)) > 1e-9:
            out.append(f"{path}: registry {a} != YAML {b}")
    elif a != b:
        out.append(f"{path}: registry {a!r} != YAML {b!r}")


def check_frozen_yaml(yaml_path: str = "configs/m2_l2_train.yaml") -> list:
    """Return a list of mismatches between the registry's ratified defaults and
    the FROZEN training YAML (empty list = no drift). Protects the freeze: if you
    edit a ratified value here, this check will name it."""
    import pathlib
    import yaml
    root = pathlib.Path(__file__).resolve().parents[1]
    with open(root / yaml_path, encoding="utf-8") as f:
        frozen = yaml.safe_load(f)
    mismatches: list = []
    _deep_compare(as_config(), frozen, "<cfg>", mismatches)
    return mismatches


def _print_table() -> None:
    by_status: Dict[str, int] = {}
    print(f"{'key':46} {'value':>22} {'units':12} {'status':10} {'wired':12}")
    print("-" * 108)
    for key, p in PARAMS.items():
        by_status[p.status] = by_status.get(p.status, 0) + 1
        val = str(p.value)
        if len(val) > 22:
            val = val[:19] + "..."
        print(f"{key:46} {val:>22} {p.units:12} {p.status:10} {p.wired:12}")
    print("-" * 108)
    print("status counts:", ", ".join(f"{k}={v}" for k, v in sorted(by_status.items())))


if __name__ == "__main__":
    _print_table()
    print()
    bad = check_frozen_yaml()
    if bad:
        print("FROZEN-YAML DRIFT DETECTED (registry != configs/m2_l2_train.yaml):")
        for m in bad:
            print("  -", m)
        raise SystemExit(1)
    print("frozen-YAML drift check: OK (registry ratified defaults == m2_l2_train.yaml)")
