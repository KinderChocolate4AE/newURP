"""C-1 corridor probe v0.2 -- torch-free unit locks (script: c1_corridor_probe).

Covers the review (docs/24) adoption: (1) WIDE seed bands structurally
non-colliding + budget asserts; (2) tiered verdict fields; (3) lexicographic
score ordering (4+ locks incl. boxed<clean, capture>eligible); (4) knot
expansion + fit; (5) finisher pointing scope (point vs hold); (6) corral
determinism/clip/stable-slot via fn.state; (7) sampler FULL bounds incl.
R1<=R0; (8) guard boundary incl. ==theta, NaN/Inf; (9) CEM determinism +
winner==returned-acts + early-stop reason; (10) score/summary math.
Env-path integration (eligibility same-timestep/pre-penetration, snapshot
restore) is exercised by the smoke run (discovery, logged in docs/09 (ttt))."""
from __future__ import annotations

import pathlib

import numpy as np
import pytest

from shepherd.scripts import c1_corridor_probe as C


# ----------------------------------------------------- seed bands (review SS9)
def test_c1_reset_bands_disjoint_from_legacy():
    c1 = set(range(C.RESET_SEARCH0, C.RESET_SEARCH1 + 1)) \
        | set(range(C.RESET_ROBUST0, C.RESET_ROBUST1 + 1))
    legacy = (set(range(300, 320)) | set(range(400, 420))
              | set(range(420, 440)) | set(range(600, 700))
              | set(range(700, 750)) | set(range(750, 770))
              | set(range(800, 900)) | set(range(950, 1050))
              | {500_000, 1_500_000, 2_500_000, 31_000_000}
              | {b + 10_000 * k + i
                 for b in (7_000_000, 8_000_000, 9_000_000)
                 for k in (0, 1, 2, 4, 8) for i in range(400)}
              | {12_000_000 + i for i in range(40)}
              | {12_010_000 + i for i in range(120)}
              | {13_000_000 + i for i in range(40)}
              | {13_010_000 + i for i in range(120)})
    assert not (c1 & legacy)


def test_c1_rng_namespaces_structurally_disjoint():
    # widened bases: no CEM(reset,restart) can reach the corral/robust base
    assert C.RNG_CEM_BASE < C.RNG_CORRAL_BASE < C.RNG_ROBUST_BASE
    # a full reset sweep of the search band, each with the max stride, stays
    # strictly below the corral base (the old 330_000+draw collision is gone)
    max_reset_idx = C.RESET_SEARCH1 - C.RESET_SEARCH0
    top = C.cem_seed(max_reset_idx, C.RNG_CEM_RESET_STRIDE - 1)
    assert top < C.RNG_CORRAL_BASE
    # legacy rng families untouched
    c1_rngs = ({C.cem_seed(j, r) for j in range(0, 100, 7) for r in (0, 1, 5)}
               | {C.RNG_CORRAL_BASE} | {C.RNG_ROBUST_BASE + i
                                        for i in range(0, 50)})
    legacy = ({212_121, 777, 90_000}
              | {b + 1_000 * k + v
                 for b in (47_000, 71_000, 75_000, 76_000, 81_000,
                           93_000, 95_000, 300_000, 310_000, 320_000)
                 for k in (0, 1, 2, 4, 8) for v in (16, 20, 24)})
    assert not (c1_rngs & legacy)


def test_cem_seed_stride_guard():
    with pytest.raises(AssertionError):
        C.cem_seed(0, C.RNG_CEM_RESET_STRIDE)      # restart overruns stride


# -------------------------------------------------------------------- corral
def _obs(att_p, att_v, lim_p=None, lim_v=None, fin_p=(2, 0, 0),
         v_soft=0.5, p_feas=0.0):
    o = np.zeros(63)
    for i in range(4):
        if lim_p is not None:
            o[9 * i: 9 * i + 3] = lim_p[i]
        if lim_v is not None:
            o[9 * i + 3: 9 * i + 6] = lim_v[i]
    o[C.FIN_P0:C.FIN_P0 + 3] = fin_p
    o[C.ATT_P0:C.ATT_P0 + 3] = att_p
    o[C.ATT_V0:C.ATT_V0 + 3] = att_v
    o[-3], o[-1] = v_soft, p_feas
    return o


def _params(pattern="ring4"):
    return {"pattern": pattern, "d_lead": 3.0, "d_back": 2.0, "R0": 2.0,
            "R1": 0.5, "t_shrink0": 2.0, "shrink_len": 5.0, "phi0": 0.3,
            "kp": 4.0, "kd": 2.0, "vmatch": 0.5}


def test_corral_shapes_clip_deterministic():
    obs = _obs([10, 0, 0], [-20, 0, 0],
               lim_p=[[0, 0, 0], [1, 1, 0], [2, -1, 0], [3, 0, 1]])
    a1 = C.make_corral_fn(_params())(obs, {})
    a2 = C.make_corral_fn(_params())(obs, {})
    assert len(a1) == 4 and all(a.shape == (3,) for a in a1)
    assert all(np.allclose(x, y) for x, y in zip(a1, a2))
    assert all(np.linalg.norm(a) <= C.A_MAX + 1e-5 for a in a1)


def test_corral_slot_assignment_stable_via_state():
    fn = C.make_corral_fn(_params("wall3_chase1"))
    obs = _obs([10, 0, 0], [-20, 0, 0],
               lim_p=[[6, 1, 0], [6, -1, 0], [6, 0, 1], [13, 0, 0]])
    fn(obs, {})
    perm1 = list(fn.state["perm"])          # introspect exposed state (SS10.1)
    assert perm1[3] == 3                     # rear limiter -> chaser slot
    fn(obs, {})
    assert list(fn.state["perm"]) == perm1   # held, not re-assigned


def test_corral_all_patterns_and_frame_fallback():
    for pat in C.CORRAL_PATTERNS:
        assert len(C.corral_slots(_params(pat))) == 4
        acts = C.make_corral_fn(_params(pat))(_obs([5, 0, 0], [0, 0, 0]), {})
        assert len(acts) == 4 and all(np.all(np.isfinite(a)) for a in acts)


def test_sampler_deterministic_and_full_bounds():
    p1 = C.sample_corral_params(np.random.default_rng(C.RNG_CORRAL_BASE))
    p2 = C.sample_corral_params(np.random.default_rng(C.RNG_CORRAL_BASE))
    assert p1 == p2
    for seed in range(80):                   # SS10.2: every param + R1<=R0
        p = C.sample_corral_params(np.random.default_rng(seed))
        assert p["pattern"] in C.CORRAL_PATTERNS
        assert 0.5 <= p["d_lead"] <= 8.0 and 1.0 <= p["d_back"] <= 6.0
        assert 0.5 <= p["R0"] <= 4.0 and 0.1 <= p["R1"] <= 1.5
        assert p["R1"] <= p["R0"]
        assert 0.0 <= p["t_shrink0"] <= 15.0 and p["shrink_len"] > 0.0
        assert 0.0 <= p["phi0"] <= np.pi / 2 + 1e-9
        assert 1.0 <= p["kp"] <= 12.0 and 0.5 <= p["kd"] <= 8.0
        assert 0.0 <= p["vmatch"] <= 1.0
        assert all(np.isfinite(v) for v in p.values()
                   if isinstance(v, float))


# ------------------------------------------------------------ finisher (SS4)
def test_finisher_pointing_and_hold():
    obs = _obs([12, 0, 0], [-20, 0, 0], fin_p=[2, 0, 0],
               v_soft=0.95, p_feas=1e-3)
    point = C.make_finisher_fn(0.9, "point_at_attacker")(obs, {})
    hold = C.make_finisher_fn(0.9, "hold")(obs, {})
    assert point.shape == (4,) and hold.shape == (4,)
    # points from finisher (2,0,0) toward attacker (12,0,0) -> +x unit
    assert np.allclose(point[:3], [1, 0, 0], atol=1e-6)
    assert np.allclose(hold[:3], [0, 0, 0])        # hold -> backend default
    assert point[3] == 1.0 and hold[3] == 1.0      # both fire (eligible)


def test_finisher_lead_uses_attacker_velocity():
    obs = _obs([12, 0, 0], [0, 10, 0], fin_p=[2, 0, 0],
               v_soft=0.95, p_feas=1e-3)
    ax = C.make_finisher_fn(0.9, "point_at_attacker", d_lead=1.0)(obs, {})[:3]
    aim = np.array([12, 0, 0]) + 1.0 * np.array([0, 10, 0]) - np.array([2, 0, 0])
    assert np.allclose(ax, aim / np.linalg.norm(aim), atol=1e-6)


def test_guard_boundary(  # SS10.3
        ):
    f = lambda v, p: C.make_finisher_fn(0.9)(_obs([1, 0, 0], [0, 0, 0],
                                                  v_soft=v, p_feas=p), {})[3]
    assert f(0.9, 1e-3) == 1.0                      # == theta -> fire
    assert f(0.95, 0.0) == 0.0                      # p_feas == 0 -> no fire
    assert f(0.95, -1.0) == 0.0                     # p_feas < 0 -> no fire
    assert f(0.89, 1e-3) == 0.0                     # below theta -> no fire
    assert f(float("nan"), 1e-3) == 0.0             # NaN -> no fire
    assert f(0.95, float("inf")) == 1.0             # inf p_feas still fires


# --------------------------------------------------------------- knots (SS6)
def test_knots_expand_and_fit():
    knots = np.arange(5 * 4 * 3).reshape(5, 4, 3).astype(float)
    seq = C.knots_to_seq(knots, 24)
    assert seq.shape == (24, 4, 3)
    assert np.allclose(seq[0], knots[0]) and np.allclose(seq[-1], knots[-1])
    back = C._fit_knots(seq, 5)
    assert back.shape == (5, 4, 3)


# --------------------------------------------------- seq / verdict / score
def test_seq_lim_zero_hold_and_seq_attr():
    acc = np.ones((2, 4, 3), np.float32)
    fn = C._seq_lim(acc)
    assert np.allclose(fn.seq, acc)
    assert np.allclose(fn(None, {})[0], 1.0)
    fn(None, {})
    assert np.allclose(fn(None, {})[0], 0.0)


def _rec(**kw):
    base = {"max_v_soft": 0.5, "M_v_given_pfeas": 0.0, "M_p_given_vsoft": 0.0,
            "M_joint": float("-inf"), "boxed_shell_steps": 0,
            "eligible": False, "eligible_dwell": 0, "SHELL_REACHED": False,
            "GUARD_FIRED": False, "LOCAL_CAPTURE": False,
            "MISSION_CAPTURE": False, "sustained": False,
            "single_frame_only": False, "penetrated": True,
            "penetrated_at": 5, "wasted": 0.0, "len": 23,
            "first_eligible_step": None}
    base.update(kw)
    return base


def test_score_lexicographic_ordering():   # SS7
    cap = _rec(LOCAL_CAPTURE=True, SHELL_REACHED=True, eligible=True,
               M_joint=2.0, penetrated=False, penetrated_at=None)
    shell = _rec(SHELL_REACHED=True, eligible=True, M_joint=1.0)
    boxed = _rec(max_v_soft=1.0, boxed_shell_steps=3)       # v_soft 1, p_feas 0
    clean_near = _rec(eligible=True, SHELL_REACHED=True, M_joint=0.3,
                      max_v_soft=0.6)
    # capture > shell-only > boxed; clean near-miss > boxed over-compression
    assert C.score(cap) > C.score(shell) > C.score(boxed)
    assert C.score(clean_near) > C.score(boxed)
    # deeper joint margin beats shallower, all else equal
    assert C.score(_rec(SHELL_REACHED=True, eligible=True, M_joint=5.0)) \
        > C.score(shell)
    # among non-eligible, later penetration beats earlier (delay tier)
    assert C.score(_rec(penetrated_at=20)) > C.score(_rec(penetrated_at=3))


def test_score_vector_tiers():
    v = C.score_vector(_rec(LOCAL_CAPTURE=True, SHELL_REACHED=True,
                            M_joint=1.0, eligible_dwell=4))
    assert v[0] == 1.0 and v[1] == 1.0 and v[2] == 1.0 and v[3] == 4.0


def test_summary_math():
    s = C._summ([_rec(), _rec(SHELL_REACHED=True, eligible=True,
                              first_eligible_step=7, M_joint=0.8,
                              M_v_given_pfeas=0.95)])
    assert s["n"] == 2 and s["n_shell_reached"] == 1
    assert s["first_eligible_steps"] == [7]
    assert abs(s["M_v_given_pfeas_max"] - 0.95) < 1e-12
    assert abs(s["M_joint_max"] - 0.8) < 1e-12


# ----------------------------------------------------------------------- CEM
class _StubPE:
    """Surrogate: clean margin peaks at knots == 3.0; shell-reach when close."""

    def rollout(self, lim_fn, fin, seed, **kw):
        acts = np.asarray(lim_fn.seq, float)
        close = float(np.mean((acts - 3.0) ** 2)) < 1.0
        mv = float(1.0 - np.mean((acts - 3.0) ** 2) / 900.0)
        return _rec(max_v_soft=mv, M_v_given_pfeas=mv,
                    M_joint=(2.0 if close else float("-inf")),
                    eligible=close, SHELL_REACHED=close,
                    penetrated=not close,
                    penetrated_at=(None if close else 5))


def test_cem_deterministic_and_winner_is_returned():   # SS10.4
    pe = _StubPE()
    kw = dict(knots=4, t_open=12, pop=16, iters=8, elite_frac=0.25, sigma0=8.0)
    r1 = C.cem_optimise(pe, None, 0, np.random.default_rng(C.cem_seed(0, 0)),
                        **kw)
    r2 = C.cem_optimise(pe, None, 0, np.random.default_rng(C.cem_seed(0, 0)),
                        **kw)
    assert r1["best_score"] == r2["best_score"]
    # the returned best_acts, replayed, reproduce the winning verdict
    replay = pe.rollout(C._seq_lim(np.asarray(r1["best_acts"])), None, 0)
    assert replay["SHELL_REACHED"] == r1["best_record"]["SHELL_REACHED"]
    assert abs(C.score(replay) - r1["best_score"]) < 1e-6


def test_cem_early_stop_reason_shell():
    class _Shell(_StubPE):
        def rollout(self, lim_fn, fin, seed, **kw):
            return _rec(SHELL_REACHED=True, eligible=True, M_joint=1.0,
                        penetrated=False, penetrated_at=None)
    r = C.cem_optimise(_Shell(), None, 0, np.random.default_rng(1),
                       knots=4, t_open=8, pop=6, iters=10, elite_frac=0.3,
                       sigma0=5.0)
    assert len(r["curve"]) == 1
    assert r["early_stop_reason"] == "shell_reached"
    assert r["best_record"]["SHELL_REACHED"]


def test_cem_early_stop_reason_capture():
    class _Cap(_StubPE):
        def rollout(self, lim_fn, fin, seed, **kw):
            return _rec(SHELL_REACHED=True, LOCAL_CAPTURE=True, eligible=True,
                        M_joint=2.0, penetrated=False, penetrated_at=None)
    r = C.cem_optimise(_Cap(), None, 0, np.random.default_rng(1),
                       knots=4, t_open=8, pop=6, iters=10, elite_frac=0.3,
                       sigma0=5.0)
    assert r["early_stop_reason"] == "capture"


# --------------------------------------------- integration (env path, SS10.5)
CFG = "configs/m3a_a3e_p1.yaml"
try:
    import gymnasium  # noqa: F401
    import pettingzoo  # noqa: F401
    _HAVE_ENV = pathlib.Path(CFG).exists()
except Exception:
    _HAVE_ENV = False


@pytest.mark.skipif(not _HAVE_ENV, reason="env deps / config absent")
def test_integration_determinism_guard_and_restore():
    env_cfg, m3, theta = C._load(CFG)
    pe = C.ProbeEnv(env_cfg, m3)
    fin = C.make_finisher_fn(theta, "point_at_attacker")
    p = {"pattern": "ring4", "d_lead": 4.0, "d_back": 2.0, "R0": 2.5,
         "R1": 0.4, "t_shrink0": 8.0, "shrink_len": 8.0, "phi0": 0.2,
         "kp": 8.0, "kd": 4.0, "vmatch": 0.8}
    # (1) same seed + controller -> identical trace
    r1 = pe.rollout(C.make_corral_fn(p), fin, 1100, trace=True)
    r2 = pe.rollout(C.make_corral_fn(p), fin, 1100, trace=True)
    assert r1["trace"]["v_soft"] == r2["trace"]["v_soft"]
    # (2) guard fire implies an eligible state existed (predicate consistency)
    if r1["GUARD_FIRED"]:
        assert r1["eligible"]
    # (3) snapshot restore: tier-1 exact replay AND tier-2 pre-commit restore
    res = C.snapshot_restore_check(pe, lambda: C.make_corral_fn(p), fin,
                                   1100, t_snap=10, theta=theta)
    assert res["tier1_exact_replay_err"] < 1e-6
    if res["tier2"]["applicable"]:
        assert res["tier2"]["restore_err"] < 1e-3      # A-3e restore atol


@pytest.mark.skipif(not _HAVE_ENV, reason="env deps / config absent")
def test_integration_verdict_tiers_are_nested():
    env_cfg, m3, theta = C._load(CFG)
    pe = C.ProbeEnv(env_cfg, m3)
    fin = C.make_finisher_fn(theta, "point_at_attacker")
    rec = pe.rollout(C._zero_fn, fin, 1100)
    # nesting: capture => guard fired; shell reached => eligible
    if rec["LOCAL_CAPTURE"]:
        assert rec["GUARD_FIRED"]
    if rec["SHELL_REACHED"]:
        assert rec["eligible"] and not rec["reset_clean"]
