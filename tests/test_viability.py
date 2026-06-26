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

from shepherd.game.viability import VShotResult, reachable_accels, v_shot

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
