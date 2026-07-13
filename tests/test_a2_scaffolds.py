"""A-2 scaffold levers (docs/12 SS3/SS4 NF branch, ratified 2026-07-14; docs/09 (aa)/(bb)).

Locks:
  * judgment invariance: default M3Params (lam2_scale=1, clean_margin_tau=0)
    reproduce the ratified J_M3a BIT-identically (docs/12 SS1 principle 3);
  * L-margin: graded l1 = l1 * sigmoid(margin/tau) * 1[not boxed]; tau=0 =
    binary; tau>0 without clean_margin -> ValueError;
  * L-fire: lam2_scale scales ONLY the l2 wasted term;
  * stage plumbing: SCAFFOLD_KEYS optional in stage dicts, unknown keys still
    rejected, stage=None -> judgment m3 untouched;
  * L-adaptive: metric-gated width ladder -- advance on sustained clean, back
    off on stall, freeze at budget cap (stall width = evidence), lam2 restore
    after full width, exit = full AND restored AND heldout nonzero last-N;
  * staged mode regression: time-linear ramp behavior unchanged.
torch-free.
"""
from __future__ import annotations

import pytest

from shepherd.env_m3 import M3Params, m3_step_terms
from shepherd.train.make_env_m3 import (Curriculum, SCAFFOLD_KEYS, STAGE_KEYS,
                                        _stage_m3, interp_stage,
                                        stage_from_cfg)

FROZEN = {"half_angle": 0.067, "theta_fire": 0.9, "sigma_g": 1.0, "w_g": 0.3}
S1 = {"half_angle": 0.20, "theta_fire": 0.8, "sigma_g": 2.0, "w_g": 1.0,
      "w_gf": 1.5, "lam2_scale": 0.3, "clean_margin_tau": 0.05}


def terms_kwargs(**over):
    kw = dict(v_full=0.8, boxed_full=False, o_full=2e-3,
              v_base=0.5, boxed_base=True, o_base=0.0,
              fire_event=True, clean=True, captured=False,
              wasted_inc=1.0, limiter_loss=1.0)
    kw.update(over)
    return kw


# --------------------------------------------------- reward-side scaffolds ---
def test_default_params_bit_identical_to_ratified_j():
    p = M3Params()
    cases = [terms_kwargs(),
             terms_kwargs(boxed_full=True, clean=False, wasted_inc=0.0),
             terms_kwargs(fire_event=False, captured=True, limiter_loss=0.0),
             terms_kwargs(v_full=0.0, o_full=0.0, clean=False)]
    for kw in cases:
        out = m3_step_terms(**kw, p=p, clean_margin=kw["v_full"] - 0.9)
        expected = (p.w_h * out["headline_m3"]
                    + p.w_g * out["r_geo_step"]
                    + p.w_gf * out["r_geo_fire"]
                    + p.l1 * (1.0 if kw["clean"] else 0.0)
                    + p.lam_cap * (1.0 if kw["captured"] else 0.0)
                    - p.l2 * max(kw["wasted_inc"], 0.0)
                    - p.l3 * kw["limiter_loss"])
        assert out["J"] == expected            # bit-identical, no tolerance
        assert out["l1_term"] == p.l1 * (1.0 if kw["clean"] else 0.0)


def test_tau_zero_ignores_margin_value():
    p = M3Params()
    a = m3_step_terms(**terms_kwargs(), p=p, clean_margin=-999.0)
    b = m3_step_terms(**terms_kwargs(), p=p, clean_margin=+999.0)
    c = m3_step_terms(**terms_kwargs(), p=p)          # default None
    assert a["J"] == b["J"] == c["J"]


def test_graded_margin_sigmoid_and_boxed_gate():
    p = M3Params(clean_margin_tau=0.05)
    mid = m3_step_terms(**terms_kwargs(clean=False), p=p, clean_margin=0.0)
    assert mid["l1_term"] == pytest.approx(0.5 * p.l1)
    hi = m3_step_terms(**terms_kwargs(clean=False), p=p, clean_margin=1.0)
    assert hi["l1_term"] == pytest.approx(p.l1, abs=1e-6)
    lo = m3_step_terms(**terms_kwargs(clean=False), p=p, clean_margin=-1.0)
    assert lo["l1_term"] == pytest.approx(0.0, abs=1e-6)
    boxed = m3_step_terms(**terms_kwargs(boxed_full=True), p=p,
                          clean_margin=1.0)
    assert boxed["l1_term"] == 0.0


def test_graded_requires_margin():
    p = M3Params(clean_margin_tau=0.05)
    with pytest.raises(ValueError, match="clean_margin"):
        m3_step_terms(**terms_kwargs(), p=p)


def test_lam2_scale_hits_only_wasted_term():
    base = m3_step_terms(**terms_kwargs(), p=M3Params())
    relieved = m3_step_terms(**terms_kwargs(), p=M3Params(lam2_scale=0.3))
    assert relieved["J"] - base["J"] == pytest.approx(0.7)   # (1-0.3)*l2*wasted
    nw_a = m3_step_terms(**terms_kwargs(wasted_inc=0.0), p=M3Params())
    nw_b = m3_step_terms(**terms_kwargs(wasted_inc=0.0),
                         p=M3Params(lam2_scale=0.3))
    assert nw_a["J"] == nw_b["J"]


# ------------------------------------------------------------ stage plumbing ---
def test_stage_from_cfg_scaffolds_optional_unknown_rejected():
    full = stage_from_cfg(S1)
    assert all(k in full for k in STAGE_KEYS + SCAFFOLD_KEYS)
    bare = stage_from_cfg({k: S1[k] for k in STAGE_KEYS})
    assert not any(k in bare for k in SCAFFOLD_KEYS)
    with pytest.raises(KeyError, match="unknown stage keys"):
        stage_from_cfg({**S1, "foo": 1.0})
    with pytest.raises(KeyError):
        stage_from_cfg({k: S1[k] for k in STAGE_KEYS[1:]})


def test_interp_carries_scaffolds_and_holds_w_g():
    mid = interp_stage(dict(S1), dict(FROZEN), 0.5)
    assert mid["half_angle"] == pytest.approx(0.5 * (0.20 + 0.067))
    assert mid["w_g"] == S1["w_g"]
    for k in SCAFFOLD_KEYS:
        assert mid[k] == S1[k]
    bare = interp_stage({k: S1[k] for k in STAGE_KEYS}, dict(FROZEN), 0.5)
    assert not any(k in bare for k in SCAFFOLD_KEYS)


def test_stage_m3_applies_scaffolds_and_none_is_neutral():
    m3 = M3Params(w_g=0.3)
    st = _stage_m3(m3, stage_from_cfg(S1))
    assert (st.w_gf, st.lam2_scale, st.clean_margin_tau) == (1.5, 0.3, 0.05)
    assert st.w_g == 1.0 and st.sigma_g == 2.0
    assert _stage_m3(m3, None) is m3
    bare = _stage_m3(m3, {k: S1[k] for k in STAGE_KEYS})
    assert (bare.w_gf, bare.lam2_scale, bare.clean_margin_tau) == (1.0, 1.0, 0.0)


# --------------------------------------------------------------- L-adaptive ---
def adaptive_cfg(**over):
    cfg = {"mode": "adaptive", "s1": dict(S1),
           "s1_min_steps": 0,
           "s1_exit": {"clean_cross_min": 0.2, "boxed_fire_max": 0.5,
                       "sustain_evals": 1},
           "s2_adaptive": {"n_width_steps": 4, "advance_clean_min": 0.1,
                           "advance_sustain": 2, "stall_evals": 3,
                           "max_steps": 10_000, "lam2_restore_steps": 100},
           "s2_exit": {"heldout_clean_nonzero_last": 3}}
    cfg["s2_adaptive"].update(over)
    return cfg


GOOD = {"clean_cross_rate": 1.0, "boxed_fire_rate": 0.0, "fire_rate": 1.0}
BAD = {"clean_cross_rate": 0.0, "boxed_fire_rate": 0.0, "fire_rate": 0.0}
FZ = {"clean_cross_rate": 0.0}


def to_s2(cur, step=10):
    assert cur.on_eval(step, dict(GOOD), dict(FZ)) == "s2"
    return step


def test_adaptive_s1_exit_gate():
    cur = Curriculum(adaptive_cfg(), dict(FROZEN))
    assert cur.on_eval(5, dict(BAD), dict(FZ)) is None
    assert cur.stage == "s1"
    assert cur.on_eval(6, dict(GOOD), dict(FZ)) == "s2"


def test_adaptive_advance_and_width_mapping():
    cur = Curriculum(adaptive_cfg(), dict(FROZEN))
    t = to_s2(cur)
    assert cur.overrides(t)["half_angle"] == pytest.approx(S1["half_angle"])
    for i in range(2):                                # sustain=2
        cur.on_eval(t + 10 + i, dict(GOOD), dict(FZ))
    assert cur.k == 1
    st = cur.overrides(t + 30)
    assert st["half_angle"] == pytest.approx(0.75 * 0.20 + 0.25 * 0.067)
    assert st["lam2_scale"] == pytest.approx(0.3)     # not yet restoring
    assert st["clean_margin_tau"] == pytest.approx(0.05)
    assert st["w_gf"] == pytest.approx(1.5)
    d = cur.describe()
    assert d["mode"] == "adaptive" and d["k"] == 1 and not d["capped"]


def test_adaptive_stall_backoff():
    cur = Curriculum(adaptive_cfg(), dict(FROZEN))
    t = to_s2(cur)
    for i in range(2):
        cur.on_eval(t + 1 + i, dict(GOOD), dict(FZ))
    assert cur.k == 1
    for i in range(3):                                # 3 bad evals -> backoff
        cur.on_eval(t + 10 + i, dict(BAD), dict(FZ))
    assert cur.k == 0
    assert any(h.get("event") == "backoff" for h in cur.history)


def test_adaptive_cap_freezes():
    cur = Curriculum(adaptive_cfg(max_steps=50), dict(FROZEN))
    t = to_s2(cur, step=10)
    cur.on_eval(t + 100, dict(GOOD), dict(FZ))        # beyond cap
    assert cur._capped and cur.k == 0
    for i in range(4):
        cur.on_eval(t + 110 + i, dict(GOOD), dict(FZ))
    assert cur.k == 0
    assert cur.describe()["capped"] is True
    assert any(h.get("event") == "cap" for h in cur.history)


def test_adaptive_full_width_lam2_restore_then_exit():
    cur = Curriculum(adaptive_cfg(n_width_steps=1, advance_sustain=1,
                                  max_steps=100000, lam2_restore_steps=100),
                     dict(FROZEN))
    t = to_s2(cur)
    assert cur.on_eval(t + 10, dict(GOOD), dict(FZ)) is None
    assert cur.k == 1 and cur._full_step == t + 10
    st0 = cur.overrides(t + 10)
    assert st0["half_angle"] == pytest.approx(FROZEN["half_angle"])
    assert st0["lam2_scale"] == pytest.approx(0.3)
    mid = cur.overrides(t + 60)
    assert 0.3 < mid["lam2_scale"] < 1.0
    end = cur.overrides(t + 110)
    assert end["lam2_scale"] == pytest.approx(1.0)
    assert cur.on_eval(t + 50, dict(GOOD),
                       {"clean_cross_rate": 0.1}) is None   # not restored yet
    assert cur.on_eval(t + 120, dict(GOOD),
                       {"clean_cross_rate": 0.1}) is None   # last-3 not all > 0
    assert cur.on_eval(t + 130, dict(GOOD),
                       {"clean_cross_rate": 0.1}) == "s3"
    assert cur.overrides(t + 140) is None


def test_staged_mode_regression_unchanged():
    cfg = {"mode": "staged", "s1": {k: S1[k] for k in STAGE_KEYS},
           "s1_min_steps": 0,
           "s1_exit": {"clean_cross_min": 0.2, "boxed_fire_max": 0.5,
                       "sustain_evals": 1},
           "s2_steps": 100,
           "s2_exit": {"heldout_clean_nonzero_last": 3}}
    cur = Curriculum(cfg, dict(FROZEN))
    assert cur.on_eval(10, dict(GOOD), dict(FZ)) == "s2"
    st = cur.overrides(60)                            # alpha = 0.5
    assert st["half_angle"] == pytest.approx(0.5 * (0.20 + 0.067))
    assert "lam2_scale" not in st
    r = None
    for s, c in ((120, 0.1), (130, 0.1), (140, 0.1)):
        r = cur.on_eval(s, dict(GOOD), {"clean_cross_rate": c})
    assert r == "s3" and cur.overrides(150) is None
