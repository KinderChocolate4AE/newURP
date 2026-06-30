"""Precomputed reachable-union API (S14 / L2 prep, GPT review Q-D1/Q-D3 + S14 fix).

Locks: (1) eval_union_with_limiters(build_reachable_union(...)) is NUMERICALLY
IDENTICAL to v_shot(..., n_segments=K) (point_mass +/- limiters, se3_cone);
(2) ONE union reused across a COMA limiter swap equals per-layout rebuilds at the
same seed (seed-CRN == shared-union CRN -> endpoints/caught shared, only feasibility
differs); (3) the analytic sphere containment certificate is exact.
"""
import numpy as np

from shepherd.game import viability as V


def _ring(n, c, r):
    return [[c[0], c[1] + r * np.cos(2 * np.pi * i / n), c[2] + r * np.sin(2 * np.pi * i / n)]
            for i in range(n)]


def _kw_pm(nc):
    return dict(judge="point_mass", net_center=nc, net_radius=2.0)


def _kw_cone():
    return dict(judge="se3_cone", net_apex=np.array([2., 0, 0]), n_F=np.array([1., 0, 0]),
                theta_net=0.2, range_min=0.0, range_max=30.0)


def _assert_equal(r1, r2):
    assert abs(r1.v_shot_soft - r2.v_shot_soft) < 1e-12
    assert r1.v_shot_worst == r2.v_shot_worst
    assert r1.n_feasible == r2.n_feasible
    assert r1.boxed_in == r2.boxed_in


def test_union_equiv_point_mass_no_limiters():
    x = np.array([6., 0, 0]); v = np.array([-8., 0, 0]); nc = x + v * 0.4
    u = V.build_reachable_union(x, v, tau=0.4, a_att_max=30., n=800, n_segments=4,
                                seed=3, **_kw_pm(nc))
    r_u = V.eval_union_with_limiters(u, None, 0.0)
    r_v = V.v_shot(x, v, tau=0.4, a_att_max=30., n=800, n_segments=4, seed=3, **_kw_pm(nc))
    _assert_equal(r_u, r_v)


def test_union_equiv_point_mass_with_limiters():
    x = np.array([6., 0, 0]); v = np.array([-8., 0, 0]); nc = x + v * 0.4
    lim = _ring(6, [3., 0, 0], 2.0)
    u = V.build_reachable_union(x, v, tau=0.4, a_att_max=30., n=800, n_segments=4,
                                seed=3, **_kw_pm(nc))
    r_u = V.eval_union_with_limiters(u, lim, 2.0)
    r_v = V.v_shot(x, v, tau=0.4, a_att_max=30., limiters=lim, kill_radius=2.0,
                   n=800, n_segments=4, seed=3, **_kw_pm(nc))
    _assert_equal(r_u, r_v)


def test_union_equiv_se3_cone_with_limiters():
    x = np.array([6., 0, 0]); v = np.array([-8., 0, 0])
    lim = _ring(4, [3., 0, 0], 2.0)
    u = V.build_reachable_union(x, v, tau=0.4, a_att_max=30., n=800, n_segments=4,
                                seed=1, **_kw_cone())
    r_u = V.eval_union_with_limiters(u, lim, 2.0)
    r_v = V.v_shot(x, v, tau=0.4, a_att_max=30., limiters=lim, kill_radius=2.0,
                   n=800, n_segments=4, seed=1, **_kw_cone())
    _assert_equal(r_u, r_v)


def test_union_shared_across_coma_swap_equals_rebuild():
    """CRN manifest: ONE union reused for two limiter layouts equals per-layout
    rebuilds at the same seed (so seed-CRN == shared-union CRN)."""
    x = np.array([6., 0, 0]); v = np.array([-8., 0, 0]); nc = x + v * 0.4
    full = _ring(6, [3., 0, 0], 2.0)
    cf = list(full); cf[0] = [3.0, 5.0, 0.0]                # COMA swap of limiter 0
    u = V.build_reachable_union(x, v, tau=0.4, a_att_max=30., n=600, n_segments=4,
                                seed=7, **_kw_pm(nc))
    _assert_equal(V.eval_union_with_limiters(u, full, 2.0),
                  V.v_shot(x, v, tau=0.4, a_att_max=30., limiters=full, kill_radius=2.0,
                           n=600, n_segments=4, seed=7, **_kw_pm(nc)))
    _assert_equal(V.eval_union_with_limiters(u, cf, 2.0),
                  V.v_shot(x, v, tau=0.4, a_att_max=30., limiters=cf, kill_radius=2.0,
                           n=600, n_segments=4, seed=7, **_kw_pm(nc)))


def test_sphere_containment_certificate_exact():
    x = np.array([0., 0, 0]); v = np.array([8., 0, 0]); nc = x + v * 0.4
    def cert(a, r):
        return V.sphere_containment_certificate(x, v, tau=0.4, a_att_max=a,
                                                net_center=nc, net_radius=r)
    assert cert(30.0, 2.0) is False         # R_reach=2.4 > 2.0 -> a reachable point escapes
    assert cert(30.0, 2.4) is True          # net >= reachable radius -> certified contained
    assert cert(10.0, 2.0) is True          # tiny ball deep inside
    # certificate agrees with the conservative worst on clear cases
    rin = V.v_shot(x, v, tau=0.4, a_att_max=10.0, net_center=nc, net_radius=2.0,
                   n=800, n_segments=4, seed=0, judge="point_mass")
    rout = V.v_shot(x, v, tau=0.4, a_att_max=30.0, net_center=nc, net_radius=2.0,
                    n=800, n_segments=4, seed=0, judge="point_mass")
    assert (rin.v_shot_worst == 1.0) == cert(10.0, 2.0)
    assert (rout.v_shot_worst == 1.0) == cert(30.0, 2.0)
