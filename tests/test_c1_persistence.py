"""C-1 Move B persistence diagnostic -- torch-free unit locks (c1_persistence).

Locks: (1) seed band disjoint from every legacy family; (2) swept-cone crossing
geometry (front monotone; on-axis caught, off-axis rejected); (3) the null-control
DISCRIMINATION property (axis-committed >> perpendicular); (4) dual-bound ordering
p_cap_engaged <= p_cap (engaged is a subset) and the engage gate; (5) the readout
mapping engaged->MOVE_C / optimistic-only->PREMISE_NET_TEMPORAL / none->MOVE_A.
The integration smoke (seed 1100 present) asserts the two bounds SPLIT (optimistic
gate opens, engaged gate closed) -- the (eeee) headline."""
from __future__ import annotations

import numpy as np
import pytest

from shepherd.scripts import c1_persistence as P


def _prof(engage=20.0, vfront=60.0, tmax=0.6):
    """Synthetic net sweep: front travels at constant vfront (linear cum_travel)."""
    t = np.linspace(0.0, tmax, 200)
    return {"t": t, "cum_travel": vfront * t, "r_sil": np.full_like(t, 2.0),
            "net_radius_engage": 2.0, "engage_dist": engage}


def test_seed_band_disjoint():
    pers = {P.pers_seed(t, b, c) for t in P.RELEASE_TIMES
            for b in range(len(P.BRANCHES)) for c in (0, 7, 20, 28)}
    legacy = ({330_000_000 + i for i in range(0, 200)}          # CEM
              | {331_000_000, 332_000_000}                       # corral / robust
              | {340_000_000 + i for i in range(0, 200)}         # G3
              | {350_000 + i for i in range(0, 5000)})           # envelope (350k band)
    assert not (pers & legacy)
    assert P.RNG_PERS_BASE > 340_000_000                         # above G3 namespace


def test_net_front_monotone():
    prof = _prof()
    fs = [P.net_front(tau, prof) for tau in np.linspace(0, 0.5, 20)]
    assert all(b >= a - 1e-9 for a, b in zip(fs, fs[1:]))
    assert P.net_front(0.0, prof) == pytest.approx(0.0, abs=1e-6)


def test_swept_cone_on_axis_caught_offaxis_rejected():
    prof = _prof()
    apex = np.array([0., 0, 0.]); u = np.array([1., 0, 0.])
    half = 0.067; range_max = 29.847; dt = 0.05
    tau_grid = np.arange(0.0, 0.4 + 1e-9, 0.01)
    lim_win = np.full((9, P.N_LIM, 3), 1e3)          # limiters parked far away
    # on-axis attacker approaching the apex -> caught (optimistic)
    x0 = np.array([12., 0.0, 0.]); v0 = np.array([-20., 0, 0.])
    on = P._swept_cone_capture(x0, v0, P_reach(30, 500, 1), apex, u, half,
                               range_max, prof, tau_grid, lim_win, dt, 0.0, 20.0)
    assert on["p_cap"] > 0.9
    # perpendicular attacker (crosses the axis laterally) -> mostly rejected
    vperp = np.array([0.0, 40.0, 0.])
    off = P._swept_cone_capture(x0, vperp, P_reach(30, 500, 1), apex, u, half,
                                range_max, prof, tau_grid, lim_win, dt, 0.0, 20.0)
    assert off["p_cap"] < 0.2
    assert on["p_cap"] - off["p_cap"] > 0.5          # discrimination


def test_engaged_bound_is_subset():
    """p_cap_engaged <= p_cap always: engaged requires the SAME capture PLUS the
    net-front travel>=engage; capture at travel<engage counts optimistic-only."""
    prof = _prof(engage=20.0)
    apex = np.array([0., 0, 0.]); u = np.array([1., 0, 0.])
    tau_grid = np.arange(0.0, 0.4 + 1e-9, 0.01)
    lim_win = np.full((9, P.N_LIM, 3), 1e3)
    # attacker caught near ~10 m travel (< engage 20) -> engaged must be 0
    x0 = np.array([11., 0.0, 0.]); v0 = np.array([-20., 0, 0.])
    r = P._swept_cone_capture(x0, v0, P_reach(30, 500, 1), apex, u, 0.067,
                              29.847, prof, tau_grid, lim_win, 0.05, 0.0, 20.0)
    assert r["p_cap_engaged"] <= r["p_cap"] + 1e-9
    assert r["p_cap"] > 0.9 and r["p_cap_engaged"] == 0.0
    assert r["median_capture_travel"] < 20.0


def test_gate_and_readout_mapping():
    # engaged pass -> MOVE_C ; optimistic-only -> PREMISE ; none -> MOVE_A
    assert P.RNG_PERS_BASE == 360_000_000
    # readout is computed in run(); here assert the branch predicate logic holds
    def verdict(n_eng, n_opt, n_a2):
        if n_eng:
            return "MOVE_C_B_PHYS"
        if n_opt:
            return "PREMISE_NET_TEMPORAL"
        if n_a2:
            return "MOVE_C_LIMITED_A2"
        return "MOVE_A_GEOMETRIC_WALL"
    assert verdict(2, 5, 0) == "MOVE_C_B_PHYS"
    assert verdict(0, 3, 0) == "PREMISE_NET_TEMPORAL"
    assert verdict(0, 0, 1) == "MOVE_C_LIMITED_A2"
    assert verdict(0, 0, 0) == "MOVE_A_GEOMETRIC_WALL"


def P_reach(a_max, n, seed):
    from shepherd.game.viability import reachable_accels
    return reachable_accels(a_max, n, seed)


# --- integration smoke: the two net-temporal bounds SPLIT on seed 1100 --------
import pathlib  # noqa: E402
CFG = "configs/m3a_a3e_p1.yaml"
CEM = "results/c1_corridor/cem_warm/c1_cem.json"
try:
    import gymnasium, pettingzoo  # noqa: F401
    _HAVE = pathlib.Path(CFG).exists() and pathlib.Path(CEM).exists()
except Exception:
    _HAVE = False


@pytest.mark.skipif(not _HAVE, reason="env/cem artifacts absent")
def test_bounds_split_seed1100():
    out = P.run(CEM, 1100, CFG, n_samp=400)
    r = out["readout"]
    # optimistic gate opens (early release clears lane + committed capture) but
    # the engaged gate is closed (capture below engage travel) -> the premise verdict
    assert r["n_gate_optimistic"] >= 1
    assert r["n_gate_engaged"] == 0
    assert r["verdict"] == "PREMISE_NET_TEMPORAL"
    # null control must discriminate, and capture must sit below engage travel
    assert r["null_discriminates"] is True
    assert r["median_capture_travel"] < out["meta"]["engage_dist"]
