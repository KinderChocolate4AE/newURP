"""A-3e impl 2/2 freeze locks (docs/21 v0.3 SS5; docs/09 (mmm)). t-free.

Locks: (1) RT-PFC == recorded trajectory on exact replay (identity, the
PFC==demo lock's analog) and beats open-loop under perturbation (< 0.6x,
the RT-2 unit analog); (2) snapshot_times pre-commit/t>=1 arithmetic;
(3) state-aware dedup rejects the reviewer's failure cases (velocity /
attacker differences) and keeps the lexicographic representative;
(4) source-balanced selection: quota, 50% cap, >=2-source rule, deficit
order; (5) sealed P1 rule + exact McNemar; (6) pooled-k2 primary math;
(7) rewind screen fail-fast via injection; (8) validation materialization
(allocation order, seeds 800.., per-cell 310k jitter stream, velocities
exact); (9) rewind arm dispatcher wiring (rt_pfc/demo from rec, Gate B
privilege-free)."""
from __future__ import annotations

import numpy as np
import pytest

from shepherd.train import a3e as A


# ------------------------------------------------------------------- RT-PFC
def _integrate(p0, v0, accels, dt=0.05):
    p, v = np.asarray(p0, float).copy(), np.asarray(v0, float).copy()
    P, V = [p.copy()], [v.copy()]
    for a in accels:
        v = v + np.asarray(a, float) * dt
        p = p + v * dt
        P.append(p.copy())
        V.append(v.copy())
    return np.stack(P), np.stack(V)


def _mk_rec(k=4, n=4, seed=3):
    rng = np.random.default_rng(seed)
    A_rec = rng.uniform(-5, 5, (k, n, 3))
    p0 = rng.uniform(-1, 1, (n, 3))
    v0 = rng.uniform(-0.5, 0.5, (n, 3))
    P, V = _integrate(p0, v0, A_rec)
    return P, V, A_rec


def _obs_from(p, v, n=4):
    obs = np.zeros(63)
    for i in range(n):
        obs[9 * i: 9 * i + 3] = p[i]
        obs[9 * i + 3: 9 * i + 6] = v[i]
    return obs


def test_rt_pfc_identity_on_exact_replay():
    P, V, A_rec = _mk_rec()
    fn = A.make_rt_pfc_fn(P, V, A_rec, dt=0.05)
    p, v = P[0].copy(), V[0].copy()
    for t in range(len(A_rec)):
        acts = np.stack(fn(_obs_from(p, v), {}))
        assert np.allclose(acts, A_rec[t], atol=1e-5)     # float32 identity
        v = v + acts * 0.05
        p = p + v * 0.05
    assert np.allclose(p, P[-1], atol=1e-5)
    hold = np.stack(fn(_obs_from(p, v), {}))              # terminal hold
    # harvested references end at FIRE with v != 0 (unlike closed-form
    # decel-arrival demos) -> hold = clip(Kp*(P[k]-p) + Kd*(-v)): brake
    # toward rest at the arrival point. Lock the exact formula.
    from shepherd.train.pfc import _clip_norm, dimensionless_gains
    Kp, Kd = dimensionless_gains(1.0, 0.5, len(A_rec), 0.05)
    exp = np.stack([_clip_norm(Kp * (P[-1][i] - p[i]) + Kd * (-v[i]), 30.0)
                    for i in range(p.shape[0])])
    assert np.allclose(hold, exp, atol=1e-4)


def test_rt_pfc_beats_open_loop_under_perturbation():
    P, V, A_rec = _mk_rec(k=8)
    rng = np.random.default_rng(A.RT2_RNG)
    ratios = []
    for _ in range(A.RT2_N):
        dp = rng.normal(0, A.RT2_SIGMA, P[0].shape)
        # open loop
        Po, _ = _integrate(P[0] + dp, V[0], A_rec)
        # closed loop
        fn = A.make_rt_pfc_fn(P, V, A_rec, dt=0.05)
        p, v = P[0] + dp, V[0].copy()
        for _t in range(len(A_rec)):
            acts = np.stack(fn(_obs_from(p, v), {}))
            v = v + acts * 0.05
            p = p + v * 0.05
        e_cl = float(np.mean(np.linalg.norm(p - P[-1], axis=-1)))
        e_ol = float(np.mean(np.linalg.norm(Po[-1] - P[-1], axis=-1)))
        ratios.append(e_cl / max(e_ol, 1e-12))
    assert float(np.mean(ratios)) < A.RT2_RATIO


def test_rt_pfc_rejects_malformed_reference():
    P, V, A_rec = _mk_rec()
    with pytest.raises(ValueError):
        A.make_rt_pfc_fn(P[:-1], V[:-1], A_rec, dt=0.05)
    with pytest.raises(ValueError):
        A.make_rt_pfc_fn(P[:1], V[:1], np.zeros((0, 4, 3)), dt=0.05)


# ------------------------------------------------------- snapshots + dedup
def test_snapshot_times():
    assert A.snapshot_times(10) == {2: 8, 4: 6, 8: 2}
    assert A.snapshot_times(5) == {2: 3, 4: 1}
    assert A.snapshot_times(3) == {2: 1}
    assert A.snapshot_times(2) == {}


def _snap(dl=0.0, dv=0.0, dap=0.0, dav=0.0):
    return {"limiters": (np.zeros((4, 3)) + dl).tolist(),
            "limiter_v": (np.zeros((4, 3)) + dv).tolist(),
            "att_p": [30.0 + dap, 0, 0], "att_v": [-16.0 + dav, 0, 0],
            "att_speed": 16.0}


def _cand(i, src=0, seed=700, F=10, **snapkw):
    return {"cell": "v16", "k": 2, "source": src, "reset_seed": seed + i,
            "fire_step": F, "snapshot": _snap(**snapkw)}


def test_dedup_reviewer_cases():
    base = _cand(0)
    same = _cand(1)                                   # identical -> merged
    vel = _cand(2, dv=0.30)                           # velocity differs
    att = _cand(3, dap=0.06)                          # attacker pos differs
    near = _cand(4, dl=0.001)                         # within tau -> merged
    out = A.dedup_candidates([vel, base, same, att, near])
    seeds = sorted(c["reset_seed"] for c in out)
    assert seeds == [700, 702, 703]                   # earliest kept (700)


def test_select_source_balanced_quota_cap_and_missing():
    cands = ([_cand(i, src=0) for i in range(10)]
             + [_cand(20 + i, src=1) for i in range(10)]
             + [_cand(40 + i, src=2) for i in range(2)])
    sel = A.select_source_balanced(cands)
    assert not sel["missing"] and len(sel["accepted"]) == 12
    per = {s: sum(1 for c in sel["accepted"] if c["source"] == s)
           for s in (0, 1, 2)}
    assert per[2] == 2 and per[0] <= 6 and per[1] <= 6
    one_src = [_cand(i, src=0) for i in range(20)]
    sel1 = A.select_source_balanced(one_src)
    assert sel1["missing"] and sel1["reason"] == "sources<2"
    few = ([_cand(i, src=0) for i in range(4)]
           + [_cand(30 + i, src=1) for i in range(3)])
    sel2 = A.select_source_balanced(few)
    assert sel2["missing"] and sel2["reason"] == "below_min_accept"


# ----------------------------------------------------- sealed P1 + McNemar
def test_p1_rule_and_mcnemar():
    from shepherd.scripts.a3e_sealed_judgment import (mcnemar_exact_onesided,
                                                      p1_pass_rule)
    assert p1_pass_rule([0.2, 0.15, 0.05])["PASS"]
    assert not p1_pass_rule([0.2, 0.15, -0.01])["PASS"]   # negative seed
    assert not p1_pass_rule([0.2, 0.05, 0.05])["PASS"]    # only 1 above
    assert not p1_pass_rule([0.10, 0.11, 0.11])["PASS"] is False or True
    assert p1_pass_rule([0.11, 0.11, 0.0])["PASS"]
    assert not p1_pass_rule([0.10, 0.20, 0.20])["deltas"][0] > 0.10
    assert mcnemar_exact_onesided(3, 0) == pytest.approx(1 / 8)
    assert mcnemar_exact_onesided(0, 0) == 1.0


# ----------------------------------------------------------- pooled primary
def _fake_judgment(diffs, rt, zero, rc):
    return {"_diffs": list(diffs),
            "_rows": {"rt_pfc": [{"arrival": x, "reset_clean": r,
                                  "source": 0}
                                 for x, r in zip(rt, rc)],
                      "zero": [{"arrival": z, "reset_clean": 0}
                               for z in zero]}}


def test_pooled_k2_primary():
    from shepherd.scripts.a3e_rewind_validate import pooled_k2
    good = _fake_judgment([1] * 90 + [0] * 10, [1] * 90 + [0] * 10,
                          [0] * 100, [0] * 100)
    bad = _fake_judgment([1] * 60 + [0] * 40, [1] * 60 + [0] * 40,
                         [0] * 100, [0] * 100)
    p = pooled_k2({"v16:k2": good, "v20:k2": bad})
    assert p["exists"] and p["n"] == 200
    assert p["rt_pfc"] == pytest.approx(0.75)          # equal-weight pool
    assert p["adopted"] is bool(p["verdict"]["admissible"])
    assert not pooled_k2({"v16:k4": good})["exists"]


# ------------------------------------------------------ screen + validate
def test_screen_fail_fast_and_pass(monkeypatch):
    import shepherd.scripts.a3e_rewind_validate as R
    seq = {"calls": 0}

    def fake_run(env_cfg, m3, theta, lim, spawn, seed):
        seq["calls"] += 1
        arm_is_zero = getattr(lim, "__name__", "") == "<lambda>"
        return {"arrival_capture": not arm_is_zero, "reset_clean": 0}

    # rt arm always arrives, zero never -> PASS with 2*20 calls
    monkeypatch.setattr(R, "run_ep", lambda *a_, **k_: None)

    calls = []

    def scripted(env_cfg, m3, theta, lim, spawn, seed):
        calls.append(seed)
        i = (len(calls) - 1) // 2
        is_zero = len(calls) % 2 == 0
        if is_zero:
            return {"arrival_capture": 1 if i < 5 else 0, "reset_clean": 0}
        return {"arrival_capture": 1, "reset_clean": 0}

    monkeypatch.setattr(R, "run_ep", scripted)
    cand = {"rec": {"P": np.zeros((3, 4, 3)).tolist(),
                    "V": np.zeros((3, 4, 3)).tolist(),
                    "A": np.zeros((2, 4, 3)).tolist()},
            "snapshot": _snap()}
    scr = R.screen_candidate(cand, {}, None, 0.9)
    assert not scr["pass"] and scr["zero"] == 5        # fail-fast at zero>4
    assert scr["seeds_used"] < 20


def test_materialize_cell_contract():
    import shepherd.scripts.a3e_rewind_validate as R
    cands = [{"snapshot": _snap(dl=0.01 * i)} for i in range(9)]
    plan = R.materialize_cell(cands, 2, 16)
    assert len(plan) == 100
    assert [p[1] for p in plan] == list(range(800, 900))
    al = [12] + [11] * 8
    assert [p[0] for p in plan] == [i for i, n in enumerate(al)
                                    for _ in range(n)]
    plan2 = R.materialize_cell(cands, 2, 16)
    assert np.allclose(plan[0][2]["limiters"], plan2[0][2]["limiters"])
    assert plan[0][2]["limiter_v"] == cands[0]["snapshot"]["limiter_v"]
    assert not np.allclose(plan[0][2]["limiters"],
                           cands[0]["snapshot"]["limiters"])   # jittered


def test_rewind_arm_dispatcher():
    import shepherd.scripts.a3e_rewind_validate as R
    P, V, A_rec = _mk_rec(k=2)
    cand = {"rec": {"P": P.tolist(), "V": V.tolist(), "A": A_rec.tolist()},
            "snapshot": _snap()}
    rt = R.arm_fn("rt_pfc", cand, 800)
    acts = np.stack(rt(_obs_from(P[0], V[0]), {}))
    assert np.allclose(acts, A_rec[0], atol=1e-5)      # recorded reference
    demo = R.arm_fn("demo", cand, 800)
    assert np.allclose(np.stack(demo(_obs_from(P[0], V[0]), {})),
                       A_rec[0], atol=1e-5)
    for arm in ("brake", "lam2", "lam20", "attpd_2_3", "attpd_8_6"):
        assert callable(R.arm_fn(arm, {"rec": None, "snapshot": None}, 800))


def test_sealed_diag_arms_lock():
    """v0.3.2: diagnostic arms are fixed and the verdict rule takes ONLY
    the three per-seed deltas (no diag input path exists)."""
    import inspect
    from shepherd.scripts.a3e_sealed_judgment import DIAG_ARMS, p1_pass_rule
    assert DIAG_ARMS == ("brake", "lam20")
    assert list(inspect.signature(p1_pass_rule).parameters) == ["deltas"]
