"""C-1 G3 deployment-aware search -- torch-free unit locks (c1_g3_deploy).

Locks: (1) separated eligibility + 5-tier verdict from synthetic recs;
(2) lexicographic score ordering (safe > shell-unsafe > lane-only > progress);
(3) g3 seed band disjoint from every legacy family; (4) net-lane perp geometry.
Env-path (E1 winner -> Tier 2) is the smoke baseline (docs/09 (bbbb))."""
from __future__ import annotations

import numpy as np
import pytest

from shepherd.scripts import c1_g3_deploy as G


def _rec(**kw):
    b = {"reset_seed": 0, "len": 21, "fire_step": 11, "penetrated_at": None,
         "E_capture": False, "E_lane": False, "E_safe": False,
         "shell_reached": False, "arrival_capture": False, "captured": False,
         "M_capture": float("-inf"), "m_clear": None, "tier": 1,
         "max_v_soft": 0.5}
    b.update(kw)
    return b


def test_g3_seed_band_disjoint():
    g3 = {G.g3_seed(j, r) for j in range(0, 50, 7) for r in (0, 1, 9)}
    legacy = ({212_121, 777, 90_000}
              | {330_000_000 + i for i in range(0, 200)}      # CEM
              | {331_000_000, 332_000_000}                    # corral/robust
              | {b + 1_000 * k + v for b in (300_000, 310_000, 320_000)
                 for k in (0, 1, 2, 4, 8) for v in (16, 20, 24)})
    assert not (g3 & legacy)
    assert G.RNG_G3_BASE > 332_000_000               # above robust namespace
    # full sweep stays below the next decade
    assert G.g3_seed(50, G.RNG_G3_STRIDE - 1) < G.RNG_G3_BASE + 51 * G.RNG_G3_STRIDE


def test_g3_seed_stride_guard():
    with pytest.raises(AssertionError):
        G.g3_seed(0, G.RNG_G3_STRIDE)


def test_perp_to_axis():
    apex = np.array([2., 0, 0]); u = np.array([1., 0, 0])
    ax, perp = G._perp_to_axis([12, 2, 0], apex, u)
    assert abs(ax - 10.0) < 1e-9 and abs(perp - 2.0) < 1e-9


def test_score_lexicographic_tiers():
    safe_cap = _rec(tier=5, E_capture=True, E_lane=True, E_safe=True,
                    arrival_capture=True, M_capture=1.0, m_clear=0.3)
    safe = _rec(tier=4, E_capture=True, E_lane=True, E_safe=True,
                M_capture=1.0, m_clear=0.1)
    shell_unsafe = _rec(tier=2, E_capture=True, M_capture=1.0, m_clear=-1.7)
    lane_only = _rec(tier=3, E_lane=True, m_clear=0.5)
    progress = _rec(tier=1, M_capture=0.2)
    xs = [safe_cap, safe, lane_only, shell_unsafe, progress]
    ss = [G.score_g3_scalar(x) for x in xs]
    assert ss[0] > ss[1] > ss[2] > ss[3] > ss[4]        # tier ordering exact
    # within Tier 2, deeper (less negative) capture margin ranks higher
    assert G.score_g3(_rec(tier=2, M_capture=1.5, m_clear=-0.5)) \
        > G.score_g3(_rec(tier=2, M_capture=0.5, m_clear=-2.0))


def test_score_g3_key_shape():
    v = G.score_g3(_rec(tier=4, M_capture=1.0, m_clear=0.2, penetrated_at=None))
    assert isinstance(v, tuple) and v[0] == 4


# --- integration smoke: E1 winner is Tier 2 (shell reached, lane unsafe) ------
import pathlib  # noqa: E402
CFG = "configs/m3a_a3e_p1.yaml"
CEM = "results/c1_corridor/cem_warm/c1_cem.json"
try:
    import gymnasium, pettingzoo  # noqa: F401
    _HAVE = pathlib.Path(CFG).exists() and pathlib.Path(CEM).exists()
except Exception:
    _HAVE = False


@pytest.mark.skipif(not _HAVE, reason="env/cem artifacts absent")
def test_e1_winner_is_tier2_lane_unsafe():
    import json
    from shepherd.scripts.c1_corridor_probe import ProbeEnv, _load, _seq_lim
    from shepherd.scripts.c1_g3_deploy import rollout_g3, make_finisher_fn
    env_cfg, m3, theta = _load(CFG)
    pe = ProbeEnv(env_cfg, m3); fin = make_finisher_fn(theta)
    w = json.loads(pathlib.Path(CEM).read_text())
    rec = next(x for x in w["draws"] if x["reset_seed"] == 1100 and x.get("best_acts"))
    r = rollout_g3(pe, _seq_lim(np.asarray(rec["best_acts"], float)), fin, 1100)
    assert r["E_capture"] is True            # shell reached (E1)
    assert r["E_lane"] is False              # lane unsafe (grounded net reach)
    assert r["tier"] == 2
    assert r["m_clear"] is not None and r["m_clear"] < 0
