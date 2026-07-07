"""M3a env variant + composition root + curriculum (docs/11 v0.2). torch-free.

Locks the ratified invariants:
  * SIGNED headline_M3 (level form, hold-vs) -- NO positive-only clipping;
  * hard v_eff gate (boxed -> 0) as MAIN, smooth = explicit ablation knob;
  * inverted-U g(o): peak 1 at o*, symmetric in ln o, g(0)=0;
  * obs layout UNCHANGED vs the frozen M2 env (warm-start ckpt compatibility);
  * coma_D / delta_v_shot_headline unchanged (M2 aux continuity);
  * eval path = frozen constants (stage=None); S1 scaffold only via stage;
  * FireGate R2 consistency (theta+c_fire) under curriculum theta overrides;
  * play-in configs: arms differ ONLY in warm_start; pre-registered values.
"""
from __future__ import annotations

import copy
import math
import pathlib

import numpy as np
import pytest
import yaml

from shepherd.env_m3 import (M3Params, M3ShapingEnv, g_geo, m3_step_terms,
                             release_transition, v_effective)
from shepherd.train.adapter import ShepherdAdapter, SHARED_FLAG_KEYS
from shepherd.train.make_env import make_train_env
from shepherd.train.make_env_m3 import (Curriculum, M3Adapter, M3_FLAG_KEYS,
                                        apply_stage_env_overrides,
                                        build_m3_attacker_env,
                                        frozen_constants, interp_stage,
                                        m3_params_from_cfg, make_m3_train_env,
                                        stage_from_cfg)

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENV_YAML = ROOT / "configs" / "m2_l2_train.yaml"
SCRATCH_YAML = ROOT / "configs" / "m3a_s1_scratch.yaml"
WARM_YAML = ROOT / "configs" / "m3a_s1_warm.yaml"


def _env_cfg():
    return yaml.safe_load(open(ENV_YAML))


def _fast_cfg():
    """Reduced-cost copy for step smokes (single-segment, few samples)."""
    cfg = _env_cfg()
    cfg["viability"]["n_samples"] = 200
    cfg["viability"]["n_segments"] = 1
    cfg["train"]["episode_len"] = 12
    return cfg


def _m3(env_cfg, **over):
    base = dict(o_star=1e-3, sigma_g=1.0, w_h=1.0, w_g=0.3, w_gf=1.0,
                lambda_cap=5.0)
    base.update(over)
    return m3_params_from_cfg(base, env_cfg)


# ------------------------------------------------------------ pure pieces ---
def test_g_geo_peak_zero_symmetry():
    assert g_geo(1e-3, 1e-3, 1.0) == pytest.approx(1.0)
    assert g_geo(0.0, 1e-3, 1.0) == 0.0
    assert g_geo(-0.1, 1e-3, 1.0) == 0.0
    up = g_geo(1e-3 * math.e, 1e-3, 1.0)
    dn = g_geo(1e-3 / math.e, 1e-3, 1.0)
    assert up == pytest.approx(dn)                      # symmetric in ln o
    assert up == pytest.approx(math.exp(-0.5))
    assert g_geo(1e-1, 1e-3, 1.0) < g_geo(1e-2, 1e-3, 1.0) < 1.0


def test_g_geo_sigma_widens():
    o = 3e-3
    assert g_geo(o, 1e-3, 2.0) > g_geo(o, 1e-3, 1.0)    # S1 sigma x2 = wider


def test_v_effective_hard_gate():
    assert v_effective(0.9, True, 0.0) == 0.0           # boxed -> 0 (req A)
    assert v_effective(0.9, False, 0.5) == pytest.approx(0.9)


def test_v_effective_smooth_is_explicit_ablation():
    lo = v_effective(1.0, True, 0.0, mode="smooth", o_star=1e-3, tau_m=3e-4)
    hi = v_effective(1.0, False, 1e-2, mode="smooth", o_star=1e-3, tau_m=3e-4)
    assert 0.0 <= lo < 0.1 and hi > 0.9                 # sigmoid in o - o*
    with pytest.raises(ValueError):
        v_effective(1.0, False, 0.5, mode="clipped")


def test_release_transition():
    assert release_transition(0.0, 5e-3, 1e-2)          # 0 -> (0, o_hi]
    assert not release_transition(0.0, 5e-2, 1e-2)      # overshoot past o_hi
    assert not release_transition(0.5, 5e-3, 1e-2)      # was not boxed
    assert not release_transition(None, 5e-3, 1e-2)     # no previous state
    assert not release_transition(0.0, 0.0, 1e-2)       # still boxed


def test_m3_terms_signed_headline_no_clipping():
    """Ratified invariant (docs/11 SS1): boxed transition keeps the FULL
    negative level; nothing clips it."""
    p = M3Params(w_h=1.0, w_g=0.0, w_gf=0.0, lam_cap=0.0, l1=0.0, l2=0.0, l3=0.0)
    t = m3_step_terms(v_full=0.9, boxed_full=True, o_full=0.0,
                      v_base=0.7, boxed_base=False, o_base=0.4,
                      fire_event=False, clean=False, captured=False,
                      wasted_inc=0, limiter_loss=0.0, p=p)
    assert t["v_eff"] == 0.0
    assert t["headline_m3"] == pytest.approx(-0.7)      # SIGNED, un-clipped
    assert t["J"] == pytest.approx(-0.7)
    # and the mirror case stays positive
    t2 = m3_step_terms(v_full=0.9, boxed_full=False, o_full=0.3,
                       v_base=0.7, boxed_base=True, o_base=0.0,
                       fire_event=False, clean=False, captured=False,
                       wasted_inc=0, limiter_loss=0.0, p=p)
    assert t2["headline_m3"] == pytest.approx(0.9)


def test_m3_terms_full_j_assembly():
    p = M3Params(o_star=1e-3, sigma_g=1.0, w_h=1.0, w_g=1.0, w_gf=1.0,
                 lam_cap=5.0, l1=1.0, l2=1.0, l3=0.5)
    t = m3_step_terms(v_full=0.95, boxed_full=False, o_full=1e-3,
                      v_base=0.2, boxed_base=False, o_base=0.5,
                      fire_event=True, clean=True, captured=True,
                      wasted_inc=0, limiter_loss=1.0, p=p)
    assert t["g_o"] == pytest.approx(1.0)               # at o*
    assert t["r_geo_step"] == pytest.approx(0.95)
    assert t["r_geo_fire"] == pytest.approx(0.95)       # fire -> same commit v*g
    expect = 1.0 * (0.95 - 0.2) + 0.95 + 0.95 + 1.0 + 5.0 - 0.0 - 0.5
    assert t["J"] == pytest.approx(expect)
    # no fire -> r_geo_fire drops out
    t2 = m3_step_terms(v_full=0.95, boxed_full=False, o_full=1e-3,
                       v_base=0.2, boxed_base=False, o_base=0.5,
                       fire_event=False, clean=True, captured=True,
                       wasted_inc=0, limiter_loss=1.0, p=p)
    assert t2["r_geo_fire"] == 0.0
    assert t2["J"] == pytest.approx(expect - 0.95)
    # wasted penalty sign
    t3 = m3_step_terms(v_full=0.5, boxed_full=False, o_full=0.5,
                       v_base=0.5, boxed_base=False, o_base=0.5,
                       fire_event=False, clean=False, captured=False,
                       wasted_inc=1, limiter_loss=0.0, p=p)
    assert t3["J"] == pytest.approx(0.0 + 1.0 * 0.5 * g_geo(0.5, 1e-3, 1.0) - 1.0)


# --------------------------------------------------- config -> params/stage ---
def test_m3_params_from_cfg_strict_and_reward_source():
    env_cfg = _env_cfg()
    m3 = _m3(env_cfg)
    assert (m3.l1, m3.l2, m3.l3) == (1.0, 1.0, 0.5)      # from frozen reward block
    assert m3.v_eff_mode == "hard" and m3.o_hi_release == pytest.approx(1e-2)
    with pytest.raises(KeyError):
        m3_params_from_cfg({"o_star": 1e-3}, env_cfg)     # missing keys
    with pytest.raises(KeyError):
        m3_params_from_cfg({"o_star": 1e-3, "sigma_g": 1, "w_h": 1, "w_g": 1,
                            "w_gf": 1, "lambda_cap": 5, "typo": 1}, env_cfg)


def test_stage_and_interp():
    s1 = stage_from_cfg({"half_angle": 0.20, "theta_fire": 0.8,
                         "sigma_g": 2.0, "w_g": 1.0})
    frozen = {"half_angle": 0.067, "theta_fire": 0.9, "sigma_g": 1.0, "w_g": 0.3}
    assert interp_stage(s1, frozen, 0.0) == pytest.approx(s1)
    end = interp_stage(s1, frozen, 1.0)
    assert end["half_angle"] == pytest.approx(0.067)
    assert end["theta_fire"] == pytest.approx(0.9)
    assert end["sigma_g"] == pytest.approx(1.0)
    assert end["w_g"] == pytest.approx(1.0)              # w_g HOLDS through S2
    mid = interp_stage(s1, frozen, 0.5)
    assert mid["theta_fire"] == pytest.approx(0.85)
    assert interp_stage(s1, frozen, 7.0)["theta_fire"] == pytest.approx(0.9)  # clamp
    with pytest.raises(KeyError):
        stage_from_cfg({"half_angle": 0.2})


def test_apply_stage_env_overrides_theta_and_no_mutation():
    env_cfg = _env_cfg()
    before = copy.deepcopy(env_cfg)
    stage = {"half_angle": 0.20, "theta_fire": 0.8, "sigma_g": 2.0, "w_g": 1.0}
    cfg = apply_stage_env_overrides(env_cfg, stage)
    assert cfg["viability"]["cone"]["half_angle"] == pytest.approx(0.20)
    assert cfg["fire_gate"]["theta_fire"] == pytest.approx(0.8)
    assert cfg["fire_gate"]["c_fire"] == pytest.approx(0.8)   # R2 consistency
    assert env_cfg == before                                  # source untouched
    assert apply_stage_env_overrides(env_cfg, None) == before


def test_frozen_constants_reads_scenario():
    env_cfg = _env_cfg()
    fz = frozen_constants(env_cfg, _m3(env_cfg))
    assert fz == pytest.approx({"half_angle": 0.067, "theta_fire": 0.9,
                                "sigma_g": 1.0, "w_g": 0.3})


# ------------------------------------------------------------- env smokes ---
def test_obs_layout_unchanged_vs_frozen_m2():
    """Warm-start compatibility lock (docs/11 SS3): M3 env keeps the M2 obs."""
    cfg = _fast_cfg()
    m2_env, _, _ = make_train_env(copy.deepcopy(cfg))
    m3_env, _, _ = make_m3_train_env(cfg, _m3(cfg))
    a = m2_env.observation_space(m2_env.possible_agents[0]).shape
    b = m3_env.observation_space(m3_env.possible_agents[0]).shape
    assert a == b
    full_cfg = _env_cfg()
    m3_full, _, _ = make_m3_train_env(full_cfg, _m3(full_cfg))
    assert m3_full.observation_space(m3_full.possible_agents[0]).shape[0] == 63


def test_frozen_eval_env_constants_and_s1_scaffold():
    cfg = _fast_cfg()
    m3 = _m3(cfg)
    env, scn, _ = make_m3_train_env(cfg, m3, stage=None)
    assert env.cone_half_angle == pytest.approx(0.067)
    assert env.theta_fire == pytest.approx(0.9)
    assert scn.fire_gate.theta_fire == pytest.approx(0.9)
    assert env.m3.sigma_g == pytest.approx(1.0) and env.m3.w_g == pytest.approx(0.3)
    s1 = {"half_angle": 0.20, "theta_fire": 0.8, "sigma_g": 2.0, "w_g": 1.0}
    env1, scn1, _ = make_m3_train_env(cfg, m3, stage=s1)
    assert env1.cone_half_angle == pytest.approx(0.20)
    assert env1.theta_fire == pytest.approx(0.8)          # threshold path
    assert scn1.fire_gate.theta_fire == pytest.approx(0.8)  # FSM gate path
    assert env1.m3.sigma_g == pytest.approx(2.0) and env1.m3.w_g == pytest.approx(1.0)
    assert env1.m3.o_star == pytest.approx(m3.o_star)     # o* NOT staged


def test_step_reward_identity_and_m2_equivalence_when_unboxed():
    """J reconstruction from flags + headline_m3 == M2 headline when neither
    layout is boxed (hard v_eff == v_soft on both sides)."""
    cfg = _fast_cfg()
    m3 = _m3(cfg)
    env, _, _ = make_m3_train_env(cfg, m3)
    ad = M3Adapter(env)
    ad.reset(seed=7)
    zeros_l = np.zeros(3, np.float32)
    for _ in range(4):
        live = {lid: zeros_l for lid in ad.limiter_ids}
        live[ad.finisher_id] = np.zeros(4, np.float32)     # axis + no fire
        r = ad.step(live)
        f = r.flags
        recon = (m3.w_h * f["headline_m3"] + m3.w_g * f["r_geo_step"]
                 + m3.w_gf * f["r_geo_fire"]
                 + m3.l1 * (1.0 if f["clean_net_threshold_crossed"] else 0.0)
                 - m3.l3 * float(f["limiter_loss"]))
        # no fire/capture/waste in a 4-step zero-action prefix
        assert not f["fire_event"] and not f["captured"]
        assert r.rewards[ad.finisher_id] == pytest.approx(recon, abs=1e-9)
        assert r.rewards[ad.adversary_id] == pytest.approx(-recon, abs=1e-9)
        if not f["boxed_in"]:
            base_boxed_free = f["v_eff_base"] == pytest.approx(
                f["v_eff"] - f["headline_m3"], abs=1e-12)
            assert base_boxed_free
        if r.done:
            break
    # M2-equivalence: unboxed-both steps must reproduce the M2 headline
    env2, _, _ = make_m3_train_env(cfg, m3)
    ad2 = M3Adapter(env2)
    ad2.reset(seed=7)
    r2 = ad2.step({**{lid: zeros_l for lid in ad2.limiter_ids},
                   ad2.finisher_id: np.zeros(4, np.float32)})
    f2 = r2.flags
    if not f2["boxed_in"] and f2["v_eff_base"] > 0:        # base unboxed too
        assert f2["headline_m3"] == pytest.approx(r2.headline, abs=1e-12)


def test_m3_flags_and_fire_chain_shape():
    cfg = _fast_cfg()
    env, _, _ = make_m3_train_env(cfg, _m3(cfg))
    ad = M3Adapter(env)
    ad.reset(seed=3)
    r = ad.step({**{lid: np.zeros(3, np.float32) for lid in ad.limiter_ids},
                 ad.finisher_id: np.zeros(4, np.float32)})
    for k in M3_FLAG_KEYS:
        assert k in r.flags, k
    assert set(SHARED_FLAG_KEYS) < set(M3_FLAG_KEYS)
    assert r.flags["fire_chains"] == []                    # no fire yet
    assert isinstance(r.flags["boxed_dwell"], int)
    assert np.isfinite(r.flags["headline_m3"])
    # obs must stay finite/M2-shaped through the adapter checks (implicit)


def test_m3params_reward_mismatch_raises():
    cfg = _fast_cfg()
    base_env, scn, lay = make_train_env(copy.deepcopy(cfg))
    bad = M3Params(l1=9.0, l2=1.0, l3=0.5)                 # != scenario reward
    with pytest.raises(ValueError):
        M3ShapingEnv(base_env.backend, scn, lay, m3=bad)


def test_build_m3_attacker_env_routes_family_draw():
    cfg = _fast_cfg()
    before = copy.deepcopy(cfg)
    params = {"att_speed": 18.0, "adversary_start_x": 22.0,
              "adversary_omega": 9.0, "adv_a_max": 25.0}
    env, scn, lay = build_m3_attacker_env(cfg, _m3(cfg), params)
    assert scn.adversary.speed == pytest.approx(18.0)
    assert lay.adversary_p0[0] == pytest.approx(22.0)
    assert env.adv_a_max == pytest.approx(25.0)
    assert env.a_att_max == pytest.approx(30.0)            # surrogate untouched
    assert cfg == before


# -------------------------------------------------------------- curriculum ---
def _cur_cfg(mode="staged"):
    return {"mode": mode,
            "s1": {"half_angle": 0.20, "theta_fire": 0.8, "sigma_g": 2.0,
                   "w_g": 1.0},
            "s1_min_steps": 100, "s2_steps": 200,
            "s1_exit": {"clean_cross_min": 0.2, "boxed_fire_max": 0.5,
                        "sustain_evals": 2},
            "s2_exit": {"heldout_clean_nonzero_last": 3}}


FROZEN = {"half_angle": 0.067, "theta_fire": 0.9, "sigma_g": 1.0, "w_g": 0.3}
GOOD = {"clean_cross_rate": 0.3, "boxed_fire_rate": 0.1, "fire_rate": 0.5}
BAD = {"clean_cross_rate": 0.0, "boxed_fire_rate": 0.9, "fire_rate": 0.0}
HELD = {"clean_cross_rate": 0.1}
HELD0 = {"clean_cross_rate": 0.0}


def test_curriculum_s1_only_never_advances():
    cur = Curriculum(_cur_cfg("s1_only"), FROZEN)
    for step in (50, 5000, 500000):
        assert cur.on_eval(step, GOOD, HELD) is None
        assert cur.overrides(step)["theta_fire"] == pytest.approx(0.8)
    assert cur.stage == "s1"


def test_curriculum_staged_exits():
    cur = Curriculum(_cur_cfg(), FROZEN)
    assert cur.on_eval(50, GOOD, HELD) is None             # min_steps not met
    assert cur.on_eval(120, BAD, HELD) is None             # streak reset
    assert cur.on_eval(150, GOOD, HELD) is None            # streak 1 < sustain 2
    assert cur.on_eval(180, GOOD, HELD) == "s2"            # sustained + min ok
    assert cur.stage == "s2" and cur.entry_step == 180
    mid = cur.overrides(280)                               # alpha = 0.5
    assert mid["theta_fire"] == pytest.approx(0.85)
    assert mid["w_g"] == pytest.approx(1.0)
    # ramp done but held-out clean has zeros in the last 3 -> HOLD in s2
    assert cur.on_eval(380, GOOD, HELD0) is None
    assert cur.on_eval(400, GOOD, HELD) is None
    assert cur.on_eval(420, GOOD, HELD) is None            # last3 = {0,.1,.1}
    assert cur.on_eval(440, GOOD, HELD) == "s3"            # last3 all nonzero
    assert cur.overrides(500) is None                      # s3 = frozen
    assert [h["stage"] for h in cur.history] == ["s1", "s2", "s3"]


def test_curriculum_rejects_bad_mode():
    with pytest.raises(ValueError):
        Curriculum({**_cur_cfg(), "mode": "warp"}, FROZEN)


# ------------------------------------------------------------ config locks ---
def test_playin_configs_locked():
    sc = yaml.safe_load(open(SCRATCH_YAML))
    wm = yaml.safe_load(open(WARM_YAML))
    assert sc["env_config"] == "configs/m2_l2_train.yaml"
    assert sc["m3"]["o_star"] == pytest.approx(1e-3)
    assert sc["m3"]["w_g"] == pytest.approx(0.3)            # judgment S3 value
    assert sc["m3"]["v_eff_mode"] == "hard"                 # MAIN, not smooth
    assert sc["curriculum"]["mode"] == "s1_only"
    assert sc["curriculum"]["s1"] == {"half_angle": 0.20, "theta_fire": 0.8,
                                      "sigma_g": 2.0, "w_g": 1.0}
    assert sc["loop"]["total_env_steps"] == 200000
    assert sc["mappo"]["coma_mix"] == pytest.approx(0.5)    # P1 main recipe
    assert sc["warm_start"]["enabled"] is False
    assert wm["warm_start"]["enabled"] is True
    assert wm["warm_start"]["tag"] == "best"
    # the two arms must differ ONLY in warm_start (paired play-in)
    assert ({k: v for k, v in sc.items() if k != "warm_start"}
            == {k: v for k, v in wm.items() if k != "warm_start"})
