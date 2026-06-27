"""N1 regression for the flexible-net forward model + cone grounding.

Validation philosophy (option-1, decided with PI -- honest grounding, not perfect
net dynamics):
  * VALIDATED: baseline effective area (calibration-anchored), self-consistency
    invariants (mass, stress, silhouette-vs-cellsum over-count, CFL, D3 benign),
    k_diag insensitivity, and config ORDERING (secondary diagnostic, pre-fixed 20 m).
  * NOT validated (locked as documented discrepancy): hang time T (flat-init
    no-wrapping net breathes -> does NOT reproduce the paper's 1.853 s) and the
    Table-3 config spread (under-predicted ~23%, ordering only).

Run: pip install -e . && python -m pytest tests/test_net_forward.py
"""
import importlib.util
import pathlib
import sys

import numpy as np
import pytest

_PROTO = pathlib.Path(__file__).resolve().parents[1] / "prototypes"
if str(_PROTO) not in sys.path:
    sys.path.insert(0, str(_PROTO))


def _load(name):
    p = _PROTO / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod                     # so ground_cone's `import net_forward` resolves
    spec.loader.exec_module(mod)
    return mod


nf = _load("net_forward")
gc = _load("ground_cone")

# light settings for test speed (engage_dist=20 m is reached by ~0.5 s)
FAST = dict(horizon=1.6, ngrid=64)
_CACHE = {}


def _baseline():
    if "base" not in _CACHE:
        _CACHE["base"] = nf.simulate(theta_deg=45, v0=60, m_block=0.035, **FAST)
    return _CACHE["base"]


# --------------------------------------------------------- self-consistency ----
def test_mass_conservation():
    msh = nf.build_mesh()
    for mb in (0.025, 0.035, 0.065):
        m = nf.lump_node_mass(msh, m_block=mb)
        assert abs(m.sum() - (nf.M_W + 4 * mb)) < 1e-9


def test_cfl_assertion_fires():
    """A dt above the explicit-stability bound must be rejected, not silently blow up."""
    with pytest.raises(AssertionError):
        nf.simulate(theta_deg=45, v0=60, m_block=0.035, dt=0.05, **FAST)


def test_rope_stress_guard():
    r = _baseline()
    assert r["guard_stress_ok"] is True
    assert r["rope_stress"] <= nf.SIGMA_B
    assert r["guard_cfl_ok"] is True


def test_silhouette_collapses_below_cellsum_floor():
    """Risk 7: when the net balls up, the per-cell sum OVER-COUNTS folded overlap and
    floors (~2 m^2), while the true silhouette correctly collapses below the 5%
    threshold. Validates the choice of silhouette as S_NP."""
    r = _baseline()
    min_sil = float(r["S_NP"].min())
    min_cell = float(r["S_cellsum"].min())
    assert min_sil < min_cell - 0.5            # silhouette goes meaningfully lower
    assert min_sil < 0.05 * r["S_des"]         # silhouette actually reaches <5% (collapse)
    assert min_cell > 0.05 * r["S_des"]        # cellsum floors above 5% (the artifact)


def test_d3_density_benign():
    """rho_rope enters only damping; 970 vs 1440 must barely move S_NP / F_max."""
    a = nf.simulate(theta_deg=45, v0=60, m_block=0.035, rho_rope=970.0, **FAST)
    b = nf.simulate(theta_deg=45, v0=60, m_block=0.035, rho_rope=1440.0, **FAST)
    assert abs(a["S_NP_engage"] - b["S_NP_engage"]) < 0.3
    assert abs(a["F_max"] - b["F_max"]) < 3.0


# ----------------------------------------------- baseline anchor + grounding ---
def test_baseline_effective_area():
    """Baseline silhouette at the engagement distance reproduces the paper's
    back-solved S_NP=12.54 (calibration-anchored -- an anchor, not independent
    evidence)."""
    r = _baseline()
    assert abs(r["S_NP_engage"] - nf.S_NP_BASELINE) / nf.S_NP_BASELINE < 0.15
    assert abs(r["coverage_C"] - 2.3174) < 0.1


def test_grounded_constants():
    """ground_cone emits the expected grounded cone constants (so wiring stays
    consistent): net_radius~2.0 (STRONG), half_angle~0.067, range_max~30 (WEAK)."""
    grounded, prov = gc.ground(verbose=False)
    assert abs(grounded["net_radius"] - 1.998) < 0.05
    assert 0.04 < grounded["half_angle"] < 0.10          # ~3.8 deg, far below tuned 0.43
    assert 20.0 < grounded["range_max"] < 40.0           # conservative, below tuned 40
    assert grounded["range_max"] == min(prov["range_estimates"].values())  # conservative pick


def test_k_diag_sensitivity():
    """Grounded net_radius must be stable across the (non-physical) diagonal shear
    stiffness scale -> the grounding is not an artifact of that numerical choice."""
    base = nf.simulate(theta_deg=45, v0=60, m_block=0.035, k_diag_scale=1.0, **FAST)["net_radius"]
    for scale in (0.5, 2.0):
        nr = nf.simulate(theta_deg=45, v0=60, m_block=0.035, k_diag_scale=scale, **FAST)["net_radius"]
        assert abs(nr - base) / base < 0.15


# -------------------------------------- secondary diagnostic (ordering only) ---
def test_config_ordering_secondary():
    """Pre-fixed 20 m effective area: config ORDERING is correct (lo < base < hi),
    even though the magnitude spread is under-predicted (~23%, documented). Secondary
    diagnostic, NOT a tight multi-point anchor."""
    lo = nf.simulate(theta_deg=25, v0=50, m_block=0.025, **FAST)["S_NP_engage"]
    base = nf.simulate(theta_deg=45, v0=60, m_block=0.035, **FAST)["S_NP_engage"]
    hi = nf.simulate(theta_deg=65, v0=90, m_block=0.065, **FAST)["S_NP_engage"]
    assert lo < base < hi


# --------------------------------- documented limitation (locked, not a pass) --
def test_hang_time_is_documented_discrepancy():
    """LOCK the known limitation: the flat-init no-wrapping net does NOT reproduce the
    paper hang time (1.853 s) -- it breathes and first-collapses much earlier. This is
    asserted as a discrepancy so a future 'fix' must consciously update the doc; it is
    NOT dressed up as a loose pass."""
    r = _baseline()
    assert np.isfinite(r["hang_T_sim"])
    assert r["hang_T_sim"] < 0.6 * 1.8529       # genuinely off, not within tolerance
