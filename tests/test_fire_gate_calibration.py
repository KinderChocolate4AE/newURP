"""theta_fire calibration harness (L2 prep, GPT review item W-W.a).

Locks the calibration's load-bearing facts: the conservative soft separates
robustly-contained (worst==1, soft==1.0) from escaping (worst==0, soft<1.0); the
zero-wasted-shot band starts ABOVE the legacy 0.8 (so the gate must be RAISED, not
lowered); and the recommended theta fires on a contained fixture but stays shut on
the a=30/net=2.0 operating point (no wasted miss-is-free shot).
"""
import numpy as np

from shepherd.eval import fire_gate_calibration as C


def test_analytic_containment_label():
    # R_reach = 1/2 a tau^2; at tau=0.4, net=2.0 contained iff a<=25 (boundary admitted)
    assert C.analytic_contained(10.0, 0.4, 2.0) is True
    assert C.analytic_contained(25.0, 0.4, 2.0) is True       # exact boundary (eps)
    assert C.analytic_contained(30.0, 0.4, 2.0) is False
    assert C.analytic_contained(30.0, 0.4, 2.4) is True       # bigger net contains 30


def test_conservative_worst_tracks_exact_containment():
    """Empirical: the conservative v_shot_worst equals the EXACT analytic
    ball-in-sphere containment at every swept point (evidence the worst tracks
    true containment, though it is still not a formal certificate)."""
    rows = C.agility_sweep(a_grid=np.arange(10.0, 40.01, 2.5), n_segments=4, n_samples=400)
    for r in rows:
        assert (r["worst"] == 1.0) == r["contained"]


def test_theta_raised_above_legacy_and_separates_positive_negative():
    a = C.agility_sweep(a_grid=np.arange(10.0, 40.01, 2.5), n_segments=4, n_samples=400)
    r = C.net_radius_sweep(r_grid=np.arange(1.5, 3.01, 0.1), n_segments=4, n_samples=400)
    th = C.threshold_sweep(a + r)
    lo, hi = C.zero_wasted_band(th)
    theta = C.recommend_theta(th)

    assert lo is not None
    assert lo > 0.80                       # zero-wasted band starts ABOVE the legacy 0.8
    assert lo <= theta <= hi               # recommendation sits inside the band

    a10 = next(x for x in a if x["x"] == 10.0)     # deeply contained
    a30 = next(x for x in a if x["x"] == 30.0)     # the operating point (escapes)
    assert a10["soft"] == 1.0 and a10["worst"] == 1.0
    assert a10["soft"] >= theta            # gate FIRES on the contained fixture
    assert a30["worst"] == 0.0
    assert a30["soft"] < theta             # gate STAYS SHUT on the escaping operating point
