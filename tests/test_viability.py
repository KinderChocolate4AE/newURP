"""Gate tests for shepherd.game.viability (commit 2).

Covers: determinism, BIT-EXACT port fidelity vs prototypes/reachset.py,
R4 boxed_in split (limiter-block != clean capture), SE(3) cone judge liveness,
degenerate-cone -> wide volume, corridor-FIXTURE-ONLY monotonicity (R5; NOT
global), and turn-limit monotonicity.

Run: pip install -e . && python -m pytest tests/test_viability.py
"""
import importlib.util
import pathlib

import numpy as np
import pytest

from shepherd.game.viability import (
    VShotResult, reachable_accels, v_shot,
    _union_sets, _turn_curve_segments, _segments_endpoints_feasible,
)

# --- shared corridor fixture (attacker funnels +x; net at straight-line predicted pos) ---
TAU, A_MAX = 0.4, 30.0
X = np.array([0.0, 0.0, 0.0])
V = np.array([20.0, 0.0, 0.0])
NC = X + V * TAU                      # net_center = predicted straight-line position
NR, KR = 1.5, 2.0
MID = X + V * (TAU * 0.5)             # mid-path point on the active escape route


def _proto():
    """Import prototypes/reachset.py as a module (it has no package __init__)."""
    p = pathlib.Path(__file__).resolve().parents[1] / "prototypes" / "reachset.py"
    spec = importlib.util.spec_from_file_location("reachset_proto", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------- #
def test_determinism():
    """Same seed -> identical VShotResult fields."""
    kw = dict(tau=TAU, a_att_max=A_MAX, judge="point_mass",
              net_center=NC, net_radius=NR, seed=0)
    a = v_shot(X, V, **kw)
    b = v_shot(X, V, **kw)
    assert isinstance(a, VShotResult)
    assert a == b


def test_port_fidelity_point_mass_no_turn_limit():
    """point_mass + attacker_turn_limited=False at seed=0 reproduces
    prototypes/reachset.py v_shot EXACTLY for its __main__ scenarios.

    Runtime comparison against the prototype -- no hardcoded golden.
    (For the record, the prototype emits soft 0.250/0.250/0.250/0.275723,
    worst 0/0/0/0, n_feasible 2000/2000/2000/1244 for 0/2/4/6 limiters.)
    """
    rs = _proto()
    mid = X + V * (TAU * 0.55)        # prototype's ring center

    def ring(dirs):
        return np.array([mid + np.array(d) for d in dirs])

    scenarios = {
        "0": None,
        "2": ring([[0, 3.5, 0], [0, -3.5, 0]]),
        "4": ring([[0, 3.5, 0], [0, -3.5, 0], [0, 0, 3.5], [0, 0, -3.5]]),
        "6": ring([[0, 3.5, 0], [0, -3.5, 0], [0, 0, 3.5], [0, 0, -3.5],
                   [4.0, 2.5, 0], [4.0, -2.5, 0]]),
    }
    for name, lim in scenarios.items():
        p = rs.v_shot(X, V, tau=TAU, a_att_max=A_MAX, net_center=NC, net_radius=NR,
                      limiters=lim, kill_radius=KR)            # defaults n=2000, seed=0
        q = v_shot(X, V, tau=TAU, a_att_max=A_MAX, judge="point_mass",
                   net_center=NC, net_radius=NR, limiters=lim, kill_radius=KR,
                   attacker_turn_limited=False, n=2000, seed=0)
        p_nf = p.get("n_feasible", 2000)
        assert q.v_shot_soft == p["v_shot_soft"], f"soft mismatch @ {name}"
        assert q.v_shot_worst == p["v_shot_worst"], f"worst mismatch @ {name}"
        assert q.n_feasible == p_nf, f"n_feasible mismatch @ {name}"


def test_reachable_accels_matches_prototype():
    """The accel sample itself is bit-identical to the prototype RNG sequence."""
    rs = _proto()
    a = reachable_accels(A_MAX, n=2000, seed=0)
    b = rs.reachable_accels(A_MAX, n=2000, seed=0)
    assert np.array_equal(a, b)


def test_boxed_in_is_limiter_block_not_capture():
    """R4: a dense plug at the corridor mouth boxes the attacker in. This is a
    LIMITER-BLOCK / containment signal, NOT a clean net-shot threshold crossing.
    """
    plug = np.array([[0.5, 0.0, 0.0]])      # all parabolas funnel through the start
    r = v_shot(X, V, tau=TAU, a_att_max=A_MAX, judge="point_mass",
               net_center=NC, net_radius=NR, limiters=plug, kill_radius=KR, seed=0)
    assert r.boxed_in is True
    assert r.n_feasible == 0
    assert r.p_feasible == 0.0
    assert r.p_limiter_blocked == 1.0
    # v_shot_soft==1.0 is continuity only; the headline must NOT read this as a
    # clean capture -- that is what p_limiter_blocked is for.


def test_judge_flag_live():
    """point_mass vs se3_cone give DIFFERENT v_shot on a non-degenerate fixture
    (both partial values), proving the judge flag is wired through."""
    rp = v_shot(X, V, tau=TAU, a_att_max=A_MAX, judge="point_mass",
                net_center=NC, net_radius=NR, seed=0)
    rc = v_shot(X, V, tau=TAU, a_att_max=A_MAX, judge="se3_cone",
                net_apex=np.array([-1.0, 0.0, 0.0]), n_F=np.array([1.0, 0.0, 0.0]),
                theta_net=0.30, range_min=8.0, range_max=9.0, seed=0)
    assert 0.0 < rp.v_shot_soft < 1.0
    assert 0.0 < rc.v_shot_soft < 1.0
    assert abs(rp.v_shot_soft - rc.v_shot_soft) > 0.05


def test_degenerate_cone_is_wide_volume():
    """theta_net ~ pi with a wide axial band behaves like a wide capture volume
    (~ sphere): it catches (essentially) all feasible endpoints."""
    r = v_shot(X, V, tau=TAU, a_att_max=A_MAX, judge="se3_cone",
               net_apex=NC, n_F=np.array([1.0, 0.0, 0.0]), theta_net=np.pi - 1e-3,
               range_min=-50.0, range_max=50.0, seed=0)
    assert r.v_shot_soft >= 0.99


def test_zero_pointing_axis_rejected():
    """se3_cone with a (near) zero net axis is a degenerate attitude -> rejected."""
    with pytest.raises(ValueError):
        v_shot(X, V, tau=TAU, a_att_max=A_MAX, judge="se3_cone",
               net_apex=NC, n_F=np.zeros(3), theta_net=0.3, seed=0)


def test_corridor_fixture_monotonicity():
    """R5: in THIS corridor fixture, adding a limiter on the ACTIVE escape route
    (the lateral ring) removes uncaught escapes and increases v_shot_soft.

    NOT a global-monotonicity claim -- free-evasion fixtures can decrease v_shot
    (see prototypes/corridor_frontier.py); the prototype's far ±3.5 ring does not
    move v_shot at all. Here the ring sits ON the escape route within kill-radius.
    """
    def soft(lims):
        return v_shot(X, V, tau=TAU, a_att_max=A_MAX, judge="point_mass",
                      net_center=NC, net_radius=NR, limiters=lims, kill_radius=KR,
                      seed=0).v_shot_soft

    s0 = soft(None)
    s1 = soft(np.array([MID + [0, 2.2, 0]]))
    s2 = soft(np.array([MID + [0, 2.2, 0], MID + [0, -2.2, 0]]))
    s3 = soft(np.array([MID + [0, 2.2, 0], MID + [0, -2.2, 0],
                        MID + [0, 0, 2.2], MID + [0, 0, -2.2]]))
    assert s0 < s1 < s2 < s3


def test_turn_limit_monotonicity():
    """Stricter (smaller) omega_att_max does NOT increase n_feasible (the heading
    cone shrinks the anisotropic reachable set)."""
    def nf(omega):
        return v_shot(X, V, tau=TAU, a_att_max=A_MAX, judge="point_mass",
                      net_center=NC, net_radius=NR, attacker_turn_limited=True,
                      omega_att_max=omega, seed=0).n_feasible

    counts = [nf(om) for om in (10.0, 4.0, 2.0, 1.0)]
    assert counts == sorted(counts, reverse=True)
    assert counts[-1] < counts[0]      # strictly tighter at the small end


# --------------------------------------------------------------------------- #
# S14 — conservative EXTREME-POINT reachable set (n_segments>1). The default
# path (n_segments=1) is the frozen legacy surrogate, exercised bit-exactly by
# test_port_fidelity_* above (those must stay untouched -> port fidelity intact).
# --------------------------------------------------------------------------- #
def test_s14_superset_no_shrink():
    """The conservative union concatenates the single-segment uniform-in-ball block
    VERBATIM (first n entries), so its feasible reachable set is a guaranteed
    SUPERSET of the legacy set -- reachability never shrinks."""
    n = 200
    endpoints, feasible, _ = _union_sets(
        X, V, tau=TAU, a_att_max=A_MAX, judge="point_mass",
        net_center=NC, net_radius=NR, net_apex=None, n_F=None, theta_net=None,
        range_min=0.0, range_max=None, limiters=None, kill_radius=0.0,
        attacker_turn_limited=False, omega_att_max=None, e_att=None,
        n=n, n_segments=2, seed=0)
    a1 = reachable_accels(A_MAX, n, 0)
    end1 = X + V * TAU + 0.5 * a1 * TAU ** 2
    feas1 = np.ones(n, bool)                          # no limiter / no turn limit here
    assert len(endpoints) > n                         # extreme points were added
    assert np.array_equal(endpoints[:n], end1)        # single-seg block verbatim
    assert np.array_equal(feasible[:n], feas1)


def test_s14_worst_monotone():
    """v_shot_worst(n_segments>1) <= v_shot_worst(1): adding extreme (boundary /
    dogleg) points can only EXPOSE escapes, never remove them. The equal-case
    fixture (a wide capture volume that catches even boundary points) keeps both at
    1.0 -- proving the monotonicity is not vacuously always 0."""
    pm = dict(judge="point_mass", net_center=NC)

    def worst(nr, nseg):
        return v_shot(X, V, tau=TAU, a_att_max=A_MAX, net_radius=nr,
                      n=200, seed=0, n_segments=nseg, **pm).v_shot_worst

    # tight net: boundary overshoot escapes -> conservative <= single
    assert worst(1.5, 2) <= worst(1.5, 1)
    # wide net: catches the whole reachable ball incl. boundary -> both stay 1.0
    assert worst(5.0, 1) == 1.0 and worst(5.0, 2) == 1.0


def test_s14_cone_overshoot_synthetic_local():
    """S14 fix in action (SYNTHETIC LOCAL cone -- decoupling rule 1; NO global
    config constants). Demo geometry tau=0.4, a_att_max=30 => the pure-forward
    a_max boundary endpoint overshoots by R = 1/2 a_max tau^2 = 2.4 to axial 10.4.
    Point a forward cone whose range_max (10.2) sits JUST BELOW that extreme but
    ABOVE the uniform-in-ball seed=0 reach (9.95 @ n=100): the legacy single-segment
    surrogate reads worst=1.0 (it never lands the exact forward extreme) while the
    conservative boundary set ALWAYS includes it -> worst=0.0, now agreeing with
    the demo's trajectory_capture=False."""
    R = 0.5 * A_MAX * TAU ** 2                         # 2.4 overshoot radius
    center_x = V[0] * TAU                              # 8.0 straight-line axial
    forward_extreme = center_x + R                     # 10.4 boundary endpoint
    # --- cone params defined LOCALLY (not read from any config) ---
    net_apex = np.array([0.0, 0.0, 0.0])
    n_F = np.array([1.0, 0.0, 0.0])                    # forward finisher axis
    theta_net = 0.5                                    # > 0.31 max sample half-angle
    range_min = 0.0
    range_max = 10.2                                   # 9.95 < 10.2 < 10.4 (margins ~0.2)
    assert range_max < forward_extreme                 # the extreme overshoots the band

    cone = dict(judge="se3_cone", net_apex=net_apex, n_F=n_F, theta_net=theta_net,
                range_min=range_min, range_max=range_max)
    legacy = v_shot(X, V, tau=TAU, a_att_max=A_MAX, n=100, seed=0,
                    n_segments=1, **cone)
    conservative = v_shot(X, V, tau=TAU, a_att_max=A_MAX, n=100, seed=0,
                          n_segments=2, **cone)
    assert legacy.v_shot_worst == 1.0                  # optimistic: claims containment
    assert conservative.v_shot_worst == 0.0            # honest: the overshoot escapes


def test_s14_turn_curve_sound():
    """Turn-curve block soundness (honest form of the optional turn-curve test).
    Every max-rate turn-curve segment respects the per-segment turn limit, so the
    integrated controls are ALL feasible -- the block never fabricates an
    infeasible 'escape'. (Under the current accel-cone _feasible_turn proxy these
    endpoints stay inside the single-segment turn-limited set; the block becomes
    capture-relevant only under a true turn-RATE-limited dynamics -- see the
    _turn_curve_segments docstring caveat.)"""
    om = 2.0
    curves = _turn_curve_segments(V, om, TAU, A_MAX, 4, e_att=None, n_azimuth=12)
    _, feasible = _segments_endpoints_feasible(
        X, V, curves, tau=TAU, limiters=None, kill_radius=0.0,
        attacker_turn_limited=True, omega_att_max=om, e_att=None)
    assert len(curves) == 12
    assert feasible.all()                              # all curves are valid controls

    # and the turn-limited conservative path stays monotone (never claims more
    # capture than the legacy single-segment turn-limited surrogate).
    tl = dict(judge="point_mass", net_center=NC, net_radius=2.0,
              attacker_turn_limited=True, omega_att_max=om)
    w1 = v_shot(X, V, tau=TAU, a_att_max=A_MAX, n=200, seed=0, n_segments=1,
                **tl).v_shot_worst
    wc = v_shot(X, V, tau=TAU, a_att_max=A_MAX, n=200, seed=0, n_segments=3,
                **tl).v_shot_worst
    assert wc <= w1
