"""Equiv lock for viability.eval_union_with_limiter_sets (2A ratified freeze
exception, docs/09 SS5 Phase 2A / SS8 2026-07-03 (d)).

The batched shared-distance eval MUST be numerically IDENTICAL (bit-exact, every
VShotResult field) to calling eval_union_with_limiters once per layout. These
tests lock that equivalence at the function level (random states/layouts, both
judges, edge cases) and at the ENV level (step() info coma_D / headline /
v-triple vs a sequential reference recomputed from the same union).

torch-free; small n keeps the suite fast.
"""
from __future__ import annotations
import numpy as np
import yaml

from shepherd.game import viability as V
from shepherd.train.make_env import make_train_env, pad_env_actions, live_action_dim

N_SMALL = 300          # Block-1 samples for function-level tests (speed)
KR = 2.0


def _fields_equal(a, b):
    return (a.v_shot_soft == b.v_shot_soft and a.v_shot_worst == b.v_shot_worst
            and a.n_feasible == b.n_feasible and a.n_total == b.n_total
            and a.boxed_in == b.boxed_in and a.p_feasible == b.p_feasible
            and a.p_limiter_blocked == b.p_limiter_blocked
            and a.judge == b.judge and a.seed == b.seed)


def _mk_union(seed, judge="se3_cone", turn=False, x=None, v=None):
    rng = np.random.default_rng(seed)
    x_att = np.array([10.0, 0.0, 0.0]) if x is None else np.asarray(x, float)
    v_att = np.array([-20.0, 0.0, 0.0]) if v is None else np.asarray(v, float)
    kw = dict(judge="se3_cone", net_apex=np.array([2.0, 0.0, 0.0]),
              n_F=np.array([1.0, 0.0, 0.0]), theta_net=0.067,
              range_min=0.0, range_max=29.847)
    if judge == "point_mass":
        kw = dict(judge="point_mass", net_center=x_att + v_att * 0.4, net_radius=2.0)
    extra = dict(attacker_turn_limited=turn)
    if turn:
        extra.update(omega_att_max=8.0, e_att=v_att)
    return V.build_reachable_union(x_att, v_att, tau=0.4, a_att_max=30.0,
                                   n=N_SMALL, n_segments=4, seed=seed, **kw, **extra), rng


def _random_layouts(rng, n_sets=6, n_lim=4, share_pool=True):
    """Layout sets drawing from a shared pool (mimics full/base/counterfactuals),
    including duplicated positions within a set."""
    pool = rng.uniform(-3, 14, size=(2 * n_lim, 3))
    sets = []
    for _ in range(n_sets):
        idx = rng.integers(0, len(pool), size=n_lim) if share_pool else None
        L = pool[idx] if share_pool else rng.uniform(-3, 14, size=(n_lim, 3))
        sets.append([row.copy() for row in L])
    sets[0][1] = np.array(sets[0][0], float).copy()      # duplicate within a set
    return sets


def test_batched_matches_sequential_se3_cone():
    for seed in (0, 1, 2):
        union, rng = _mk_union(seed)
        sets = _random_layouts(rng)
        seq = [V.eval_union_with_limiters(union, L, KR) for L in sets]
        bat = V.eval_union_with_limiter_sets(union, sets, KR)
        assert len(seq) == len(bat)
        for a, b in zip(seq, bat):
            assert _fields_equal(a, b)


def test_batched_matches_sequential_point_mass_and_turn():
    union, rng = _mk_union(7, judge="point_mass", turn=True)
    sets = _random_layouts(rng, n_sets=5)
    seq = [V.eval_union_with_limiters(union, L, KR) for L in sets]
    bat = V.eval_union_with_limiter_sets(union, sets, KR)
    for a, b in zip(seq, bat):
        assert _fields_equal(a, b)


def test_batched_edge_kr_zero_and_empty_sets():
    union, rng = _mk_union(3)
    sets = _random_layouts(rng, n_sets=3)
    # kill_radius = 0 -> no-go never fires; must match sequential exactly
    seq = [V.eval_union_with_limiters(union, L, 0.0) for L in sets]
    bat = V.eval_union_with_limiter_sets(union, sets, 0.0)
    for a, b in zip(seq, bat):
        assert _fields_equal(a, b)
    # empty / None layouts mixed with a live one
    mixed = [[], None, sets[0]]
    seq = [V.eval_union_with_limiters(union, L, KR) for L in mixed]
    bat = V.eval_union_with_limiter_sets(union, mixed, KR)
    for a, b in zip(seq, bat):
        assert _fields_equal(a, b)


def test_batched_boxed_in_state():
    """Attacker ringed at sub-kill-radius distance -> boxed_in on BOTH paths."""
    union, _ = _mk_union(11, x=[10.0, 0.0, 0.0], v=[-5.0, 0.0, 0.0])
    tight = [[10.0 + dx, dy, dz] for dx, dy, dz in
             [(1.0, 0, 0), (-1.0, 0, 0), (0, 1.0, 0), (0, -1.0, 0),
              (0, 0, 1.0), (0, 0, -1.0), (0.5, 0.5, 0), (-0.5, -0.5, 0)]]
    seq = V.eval_union_with_limiters(union, tight, KR)
    bat = V.eval_union_with_limiter_sets(union, [tight], KR)[0]
    assert seq.boxed_in and _fields_equal(seq, bat)


def test_env_step_matches_sequential_reference():
    """ENV-level lock: step() coma_D / headline / v-triple == sequential
    eval_union_with_limiters reference recomputed from the same union."""
    with open("configs/m2_l2_train.yaml") as f:
        cfg = yaml.safe_load(f)
    env, scn, lay = make_train_env(cfg)
    env.reset(seed=0)
    rng = np.random.default_rng(0)
    p0 = [np.asarray(p, float) for p in lay.limiter_p0]

    for _ in range(3):
        lims, fin, att = env._states()
        p_att, v_att = env._p(att), env._v(att)
        lim_pos = [env._p(s) for s in lims]
        step_seed = env._seed * 100003 + (env._step_i + 1)
        union = V.build_reachable_union(
            p_att, v_att, tau=env.tau_deploy, a_att_max=env.a_att_max,
            n=env.n_samples, n_segments=env.n_segments, seed=step_seed,
            judge="se3_cone", net_apex=env._p(fin), n_F=env._e(fin),
            theta_net=env.cone_half_angle, range_min=env.cone_range_min,
            range_max=env.cone_range_max)
        vfull = V.eval_union_with_limiters(union, lim_pos, env.kill_radius)
        vbase = V.eval_union_with_limiters(union, p0, env.kill_radius)
        ref_headline = vfull.v_shot_soft - vbase.v_shot_soft
        ref_coma = {}
        for i in range(len(lim_pos)):
            cf = list(lim_pos)
            cf[i] = p0[i]
            vcf = V.eval_union_with_limiters(union, cf, env.kill_radius)
            ref_coma[f"limiter_{i}"] = float(vfull.v_shot_soft - vcf.v_shot_soft)

        live = {}
        for a in env.agents:
            d = live_action_dim(a)
            act = rng.uniform(-1.0, 1.0, d).astype(np.float32)
            if a.startswith(("limiter", "adversary")):
                act *= 30.0
            if a == "finisher_0":
                act[-1] = 0.0                                  # no fire
            live[a] = act
        obs, rew, te, tr, infos = env.step(pad_env_actions(live))

        fin_info = infos["finisher_0"]
        assert fin_info["delta_v_shot_headline"] == ref_headline
        assert fin_info["v_shot_soft"] == vfull.v_shot_soft
        assert fin_info["v_shot_worst"] == vfull.v_shot_worst
        assert fin_info["p_feasible"] == vfull.p_feasible
        assert fin_info["boxed_in"] == vfull.boxed_in
        for lid, d_ref in ref_coma.items():
            assert infos[lid]["coma_D"] == d_ref
        if not env.agents:
            break
