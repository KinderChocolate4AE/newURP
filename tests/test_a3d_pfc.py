"""Phase 0-d step-1 instrument locks (docs/18 v0.2 RATIFIED, docs/09 (xx)).

torch-free. Covers the 3rd-party review's mandatory items:
  * closed-form R/O vs an integrator replication (the k=1 2x table-error
    class -- docs/18 SS1.1 item 1);
  * zero-action env rollout trace vs the coast closed form (time-index
    contract: k movement steps between spawn and t=0 -- SS1.1 item 2);
  * PFC == open-loop demo on the nominal spawn (zero corrections) and PFC
    cancels spawn position jitter that open-loop replay preserves;
  * dimensionless gain scaling; Gate B constructors are structurally
    reference-free (no bank/demo/witness arguments).
"""
from __future__ import annotations


import inspect
import json
import pathlib

import numpy as np
import pytest
import yaml

from shepherd.train import pfc as P

ROOT = pathlib.Path(__file__).resolve().parents[1]
DT = 0.05
BANK = ROOT / "results/a3d_sbe_bank.json"
BUNDLE = ROOT / "results/a3d_bundle_dev.json"


# ------------------------------------------------------------ closed forms --
def _linear_profile(v0: float, k: int, n_lim: int = 1):
    """1-D synthetic linear-decel arrival profile (a3d_sbe_bank SS1 form):
    per-limiter accel = -(v0/(k dt)) * u along +x; spawn so that the demo
    arrives at the origin at rest."""
    u = np.array([1.0, 0.0, 0.0])
    a = -(v0 / (k * DT)) * u
    accels = np.tile(a, (k, n_lim, 1))
    R = P.spawn_offset(v0, k, DT)
    p0 = np.tile(-R * u, (n_lim, 1))          # slot at origin
    v0v = np.tile(v0 * u, (n_lim, 1))
    return p0, v0v, accels


@pytest.mark.parametrize("k", [1, 2, 4, 8])
@pytest.mark.parametrize("frac", [0.3, 0.8])
def test_closed_forms_match_integrator(k, frac):
    v0 = frac * 30.0 * k * DT
    p0, v0v, accels = _linear_profile(v0, k)
    # demo roll arrives at the slot (origin) at rest
    Pr, Vr = P.reference_rollout(p0, v0v, accels, DT)
    assert np.linalg.norm(Pr[-1]) < 1e-12
    assert np.linalg.norm(Vr[-1]) < 1e-12
    # zero-action coast: overshoot O = v0*dt*(k+1)/2 past the slot
    pz = p0.copy()
    for _ in range(k):
        pz = pz + v0v * DT
    assert np.linalg.norm(pz[0]) == pytest.approx(
        P.zero_overshoot(v0, k, DT), rel=1e-12)
    # spawn offset R = v0*dt*(k-1)/2
    assert np.linalg.norm(p0[0]) == pytest.approx(
        P.spawn_offset(v0, k, DT), rel=1e-12, abs=1e-15)


def test_docs18_k1_table_row():
    """The corrected docs/18 SS1 k=1 row: R = 0, O in [0.0225, 0.06]."""
    assert P.spawn_offset(0.45, 1, DT) == 0.0
    assert P.spawn_offset(1.2, 1, DT) == 0.0
    assert P.zero_overshoot(0.45, 1, DT) == pytest.approx(0.0225)
    assert P.zero_overshoot(1.2, 1, DT) == pytest.approx(0.06)


def test_dimensionless_gain_scaling():
    kp2, kd2 = P.dimensionless_gains(1.0, 1.0, 2, DT)
    kp4, kd4 = P.dimensionless_gains(1.0, 1.0, 4, DT)
    assert kp2 / kp4 == pytest.approx(4.0)
    assert kd2 / kd4 == pytest.approx(2.0)
    with pytest.raises(ValueError):
        P.dimensionless_gains(1.0, 1.0, 0, DT)


# ------------------------------------------------------------------ PFC -----
def _obs_from_state(pos, vel, n_max=4):
    """63-dim obs with limiter pos/vel planted at the frozen offsets."""
    o = np.zeros(9 * n_max + 9 + 9 + 6 + 3, np.float32)
    for i in range(len(pos)):
        o[9 * i: 9 * i + 3] = pos[i]
        o[9 * i + 3: 9 * i + 6] = vel[i]
    return o


def test_pfc_equals_demo_on_nominal():
    p0, v0v, accels = _linear_profile(2.4, 4, n_lim=4)
    spawn = {"limiters": p0, "limiter_v": v0v}
    fn = P.make_pfc_fn(spawn, accels, DT, c_p=1.0, c_d=1.0)
    Pr, Vr = P.reference_rollout(p0, v0v, accels, DT)
    for t in range(4):
        acts = fn(_obs_from_state(Pr[t], Vr[t]), None)
        for i in range(4):
            np.testing.assert_allclose(acts[i], accels[t, i],
                                       rtol=0, atol=1e-6)


def _roll_arm(fn, p0, v0, k_steps):
    """Roll the limiter kinematics under a controller closure."""
    p, v = np.asarray(p0, float).copy(), np.asarray(v0, float).copy()
    for _ in range(k_steps):
        acts = np.asarray(fn(_obs_from_state(p, v), None), float)
        v = v + acts * DT
        p = p + v * DT
    return p, v


def test_pfc_cancels_spawn_jitter_open_loop_does_not():
    k, v0 = 4, 2.4
    p0, v0v, accels = _linear_profile(v0, k, n_lim=4)
    rng = np.random.default_rng(7)
    delta = rng.normal(0.0, 0.02, (4, 3))          # sigma_pos-scale jitter
    pj = p0 + delta
    # open-loop demo from the jittered spawn keeps the offset verbatim
    cnt = {"t": 0}

    def demo_fn(o, f):
        t = cnt["t"]; cnt["t"] += 1
        return accels[t] if t < k else np.zeros((4, 3))

    p_ol, _ = _roll_arm(demo_fn, pj, v0v, k)
    err_ol = np.linalg.norm(p_ol, axis=1)          # slot at origin
    np.testing.assert_allclose(err_ol, np.linalg.norm(delta, axis=1),
                               rtol=0, atol=1e-9)
    # PFC tracks the NOMINAL reference -> endpoint error shrinks
    fn = P.make_pfc_fn({"limiters": p0, "limiter_v": v0v}, accels, DT,
                       c_p=1.0, c_d=1.0)
    p_cl, _ = _roll_arm(fn, pj, v0v, k)
    err_cl = np.linalg.norm(p_cl, axis=1)
    assert (err_cl < err_ol - 1e-9).all()
    assert (err_cl < 0.6 * err_ol).all()


def test_pfc_clip_bound_and_terminal_hold():
    p0, v0v, accels = _linear_profile(2.4, 2, n_lim=4)
    fn = P.make_pfc_fn({"limiters": p0, "limiter_v": v0v}, accels, DT,
                       c_p=1.0, c_d=1.0)
    # huge state error -> output saturates at the accel budget
    far = _obs_from_state(p0 + 100.0, v0v)
    acts = fn(far, None)
    for a in acts:
        assert np.linalg.norm(a) <= 30.0 + 1e-6
    # past the reference horizon: terminal hold pulls back to the slot
    Pr, _ = P.reference_rollout(p0, v0v, accels, DT)
    hold = fn(_obs_from_state(Pr[-1] + 0.1, np.zeros((4, 3))), None)
    for i, a in enumerate(hold):
        d = np.asarray(a, float)
        assert d @ (Pr[-1][i] - (Pr[-1][i] + 0.1)) > 0  # points at the slot


def test_pfc_rejects_empty_demo():
    with pytest.raises(ValueError):
        P.make_pfc_fn({"limiters": np.zeros((4, 3)),
                       "limiter_v": np.zeros((4, 3))},
                      np.zeros((0, 4, 3)), DT, 1.0, 1.0)


# ---------------------------------------------------------------- Gate B ----
def test_gateb_constructors_are_reference_free():
    """Structural no-privilege lock (docs/18 SS5): Gate B constructors take
    no bank/demo/witness/reference arguments."""
    banned = ("spawn", "demo", "bank", "witness", "entry", "ref")
    for ctor in (P.make_lambda_brake_fn, P.make_att_pd_fn):
        for name in inspect.signature(ctor).parameters:
            assert not any(b in name.lower() for b in banned), \
                f"{ctor.__name__} arg '{name}' smells privileged"


def test_gateb_lambda_brake_and_attpd_read_obs_only():
    pos = np.tile(np.array([1.0, 0.0, 0.0]), (4, 1))
    vel = np.tile(np.array([0.0, 2.0, 0.0]), (4, 1))
    o = _obs_from_state(pos, vel)
    lb = P.make_lambda_brake_fn(5.0)(o, None)
    for a in lb:
        np.testing.assert_allclose(a, [0.0, -10.0, 0.0], atol=1e-6)
    # attacker block drives attpd's target
    o[P.ATT_P0:P.ATT_P0 + 3] = [10.0, 0.0, 0.0]
    o[P.ATT_V0:P.ATT_V0 + 3] = [-20.0, 0.0, 0.0]
    ap = P.make_att_pd_fn(kp=1.0, kd=0.0, d_lead=1.0)(o, None)
    tgt = np.array([9.0, 0.0, 0.0])                # att_p + 1m along unit(v)
    for i, a in enumerate(ap):
        np.testing.assert_allclose(a, tgt - pos[i], atol=1e-6)


# ------------------------------------------- env rollout trace (SS1.1 (2)) --
@pytest.mark.skipif(not (BANK.exists() and BUNDLE.exists()),
                    reason="bank/bundle artifacts not present")
def test_zero_coast_env_trace_matches_closed_form():
    """3rd-party mandatory check: the env performs exactly k movement steps
    between the SBE spawn and the witness time, and zero-action limiter
    kinematics equal the coast closed form (p_j = p0 + j*v0*dt)."""
    from shepherd.train.make_env_m3 import (M3Adapter, gating_env_for_spawn,
                                            m3_params_from_cfg)
    run_cfg = yaml.safe_load((ROOT / "configs/m3a_a3d_pilot.yaml").read_text())
    env_cfg = yaml.safe_load((ROOT / run_cfg["env_config"]).read_text())
    m3 = m3_params_from_cfg(run_cfg["m3"], env_cfg)
    bundle = json.loads(BUNDLE.read_text())
    st = bundle["stages"]["d2"]
    e = st["episodes"][0]
    k = int(st["k"])
    env, _, _ = gating_env_for_spawn(env_cfg, m3, e["spawn"])
    ad = M3Adapter(env)
    obs, _ = ad.reset_to(dict(e["spawn"]), seed=int(e["reset_seed"]))
    lid0 = ad.limiter_ids[0]
    L0 = np.asarray(e["spawn"]["limiters"], float)
    V0 = np.asarray(e["spawn"]["limiter_v"], float)
    o = np.asarray(obs[lid0], float)
    for i in range(4):
        np.testing.assert_allclose(o[9 * i: 9 * i + 3], L0[i], atol=2e-4)
        np.testing.assert_allclose(o[9 * i + 3: 9 * i + 6], V0[i], atol=2e-4)
    zeros_lim = {lid: np.zeros(3, np.float32) for lid in ad.limiter_ids}
    acts = dict(zeros_lim)
    acts[ad.finisher_id] = np.zeros(4, np.float32)   # never fires
    for j in range(1, k + 2):                        # beyond t=0 as well
        res = ad.step(dict(acts))
        o = np.asarray(res.obs[lid0], float)
        expect = L0 + j * V0 * DT                    # coast closed form
        for i in range(4):
            np.testing.assert_allclose(o[9 * i: 9 * i + 3], expect[i],
                                       atol=5e-4,
                                       err_msg=f"step {j} limiter {i}")
        if res.done:
            pytest.fail(f"episode ended at step {j} < k+1 (no-fire zero run)")
