import jax, jax.numpy as jnp, numpy as np
from sim import *

jax.config.update("jax_platform_name", "cpu")
NOACT = lambda n: DefAct(jnp.zeros((n, 3)), jnp.zeros(3), jnp.bool_(False))


def test_cpa():
    assert abs(float(cpa(jnp.array([-5., 1, 0]), jnp.array([5., 1, 0]))) - 1.0) < 1e-5
    assert abs(float(cpa(jnp.array([2., 0, 0]), jnp.array([4., 0, 0]))) - 2.0) < 1e-5


def test_lead_aim():
    u, t, ok = lead_aim(jnp.array([20., 0, 0]), jnp.zeros(3), 25.)
    assert ok and abs(float(t) - 0.8) < 1e-5 and np.allclose(u, [1, 0, 0], atol=1e-5)
    r, w = jnp.array([30., 10, 5]), jnp.array([-20., 5, 0])
    u, t, ok = lead_aim(r, w, 25.)
    assert ok and np.allclose(r + w * t, 25. * u * t, atol=1e-3)


def test_kin_limits_and_ground():
    p, v, a = jnp.array([0., 0, 0.1]), jnp.array([0., 0, -10]), jnp.zeros(3)
    for _ in range(200):
        p, v, a = kin(p, v, a, jnp.array([100., 0, -100]), 20., 30., 0.2, 0.02)
    assert float(norm(v)) <= 30. + 1e-4 and float(p[2]) >= 0.
    assert float(norm(a)) <= 20. + 1e-4


def _state(n=1, **kw):
    s = reset(jax.random.PRNGKey(0), n)
    if "ap" in kw:  # perfect track for geometry unit tests
        kw = dict(kw, trk_p=kw["ap"], trk_v=kw.get("av", [0., 0, 0]))
    return s._replace(**{k: jnp.asarray(v, jnp.float32) if not isinstance(v, bool) else jnp.bool_(v) for k, v in kw.items()})


def test_limiter_fly_through_detected():
    # attacker crosses a stationary limiter at 30 m/s with 1 m offset; positions straddle within one substep
    s = _state(ap=[200., 1., 50.], av=[-30., 0, 0], lp=[[199.7, 0., 50.]], aa=[0., 0, 0])
    s = s._replace(lalive=jnp.array([True]))
    s = step(s, NOACT(1), jnp.array([-100., 0, 0]))
    assert int(s.status) == 2 and not bool(s.lalive[0])


def test_net_capture_in_range_and_not_beyond():
    for dist, want in ((10., 1), (40., 0)):
        s = _state(ap=[dist, 0., 25.], av=[0., 0, 0], lalive=False)
        s = s._replace(lalive=jnp.array([False]))
        act = DefAct(jnp.zeros((1, 3)), jnp.zeros(3), jnp.bool_(True))
        for i in range(15):
            s = step(s, act if i == 0 else NOACT(1), jnp.zeros(3))
        assert int(s.status) == want, (dist, int(s.status))
        assert int(s.shots) == 1


def test_net_not_before_open():
    # target at 3 m: net passes it at t=0.12 s < open time -> no capture
    s = _state(ap=[3., 0., 25.], av=[0., 0, 0])
    s = s._replace(lalive=jnp.array([False]))
    act = DefAct(jnp.zeros((1, 3)), jnp.zeros(3), jnp.bool_(True))
    for i in range(15):
        s = step(s, act if i == 0 else NOACT(1), jnp.zeros(3))
    assert int(s.status) == 0


def test_undefended_all_leak_no_timeout():
    for kind in (0, 1, 2):
        s = run_episodes(jax.random.PRNGKey(1), 64, 2, lambda x: NOACT(2), att_script,
                         use_net=False, use_lim=False, kind=kind)
        assert bool(jnp.all(s.status == 3)), (kind, np.bincount(np.array(s.status)))
        assert float(jnp.max(s.t)) < P.T - 1  # episodes end well inside the 30 s window


def test_summarize_names():
    st = jnp.array([1, 1, 2, 3, 4, 0, 0, 0])
    r = summarize(st)
    assert r["intercept"] == 3 / 8 and r["net"] == 2 / 8 and r["lim"] == 1 / 8 and r["leak"] == 1 / 8 and r["timeout"] == 1 / 8


if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f(); print("ok", k)
