"""docs/79 r1 §3 — 게이트 7 unit gates (G7-A ~ G7-E). 위반 1건 = 게이트 7 무효."""
from fractions import Fraction

import numpy as np
import pytest

from shepherd.scripts.gate7_relaxation import (
    d_max_from_rest, fixture_blockable, fixture_n1_vs_n2, fixture_outer_trap,
    fixture_unblockable, run_unit_gates, true_v, u_rel)


def test_g7a_soundness_all_fixtures_all_levels():
    for inst, meta in (fixture_blockable(), fixture_unblockable(),
                       fixture_outer_trap()):
        for lv in (0, 1, 2):
            r = u_rel(inst, meta["N"], level=lv)
            assert r["status"] == "OPTIMAL"
            assert r["u_bound"] >= meta["vstar"], (meta, lv, r)


def test_g7a_n1_vs_n2_truth():
    inst, m = fixture_n1_vs_n2()
    for lv in (0, 1, 2):
        assert u_rel(inst, 1, level=lv)["u_bound"] >= m["vstar_n1"]
        assert u_rel(inst, 2, level=lv)["u_bound"] >= m["vstar_n2"]
    # 최종 레벨은 truth 에 정확히 수렴해야 한다 (relaxation 이 공허하지 않음)
    assert u_rel(inst, 1, level=2)["u"] == m["vstar_n1"]
    assert u_rel(inst, 2, level=2)["u"] == m["vstar_n2"]


def test_g7a_trap_coarse_overestimates_then_converges():
    inst, m = fixture_outer_trap()
    us = [u_rel(inst, 1, level=lv)["u"] for lv in (0, 1, 2)]
    assert us[0] > m["vstar"]                 # 낙관 방향: coarse 는 반드시 과대
    assert us[2] == m["vstar"]                # refinement 로 truth 수렴


def test_g7b_refinement_monotone():
    for inst, meta in (fixture_blockable(), fixture_unblockable(),
                       fixture_outer_trap()):
        us = [u_rel(inst, meta["N"], level=lv)["u"] for lv in (0, 1, 2)]
        assert us[0] >= us[1] >= us[2]        # 등호 허용


def test_g7d_n_nesting():
    inst, _ = fixture_n1_vs_n2()
    for lv in (0, 1, 2):
        assert u_rel(inst, 1, level=lv)["u"] <= u_rel(inst, 2, level=lv)["u"]


def test_g7c_random_placement_domination():
    rng = np.random.default_rng(11)
    for inst, meta in (fixture_blockable(), fixture_unblockable(),
                       fixture_outer_trap()):
        u_fin = u_rel(inst, meta["N"], level=2)["u"]
        d_max = d_max_from_rest(inst["T"], inst["v_lim"], inst["a_lim"])
        for _ in range(500):
            pts = []
            for l0 in inst["lim0"][: meta["N"]]:
                x = l0 + rng.normal(size=3) * d_max / 3
                if (np.linalg.norm(x - l0) <= d_max
                        and np.linalg.norm(x - inst["asset"]) > inst["r_nk"]):
                    pts.append(x)
            if not pts:
                continue
            v = true_v(inst, pts)
            if v is not None:
                assert v <= u_fin


def test_g7e_reach_formula_is_outer():
    from shepherd.scripts.gate7_relaxation import d_max_outer
    rng = np.random.default_rng(13)
    for _ in range(100):
        T = float(rng.uniform(0.1, 10.0))
        v_max = float(rng.uniform(0.5, 8.0))
        a_max = float(rng.uniform(0.5, 8.0))
        v0 = float(rng.uniform(0.0, v_max))
        dt = 0.01
        v, x = np.array([v0, 0.0, 0.0]), np.zeros(3)
        for _t in range(max(int(T / dt), 1)):
            a = rng.normal(size=3)
            a = a / max(np.linalg.norm(a), 1e-9) * a_max
            v = v + a * dt
            s = np.linalg.norm(v)
            if s > v_max:
                v = v * (v_max / s)
            x = x + v * dt
        assert np.linalg.norm(x) <= d_max_outer(v0, v_max, a_max, T) + 1e-6
        if v0 == 0.0:
            assert d_max_from_rest(T, v_max, a_max) <= d_max_outer(0.0, v_max,
                                                                   a_max, T) + 1e-12


def test_g7f_elapsed_time_invariance_adapter():
    """docs/79 r2 G7-F: 동일 물리 snapshot 에 t 메타데이터만 달라도 게이트 7
    인스턴스·U 가 동일해야 한다 (경과시간이 입력 어디에도 없음)."""
    from types import SimpleNamespace
    from shepherd.scripts.gate7_pilot_adapter import _gate7_input

    pb = np.array([[[10.0, y, 5.0] for y in np.linspace(-1, 1, 5)],
                   [[12.0, y, 5.0] for y in np.linspace(-1, 1, 5)]])
    union = SimpleNamespace(caught=np.array([True, False]),
                            turn_feasible=np.array([True, True]),
                            path_blocks=(pb,))
    kw = dict(asset=np.zeros(3), lim_snap=[(8.0, 0.0, 5.0)], lim_v0=[0.0],
              v_lim=5.0, a_lim=5.0, r_kill=1.0)
    s_t2 = dict(ep=0, t=2)
    s_t18 = dict(ep=0, t=360)
    inst_a, meta_a = _gate7_input(union, s_t2, **kw)
    inst_b, meta_b = _gate7_input(union, s_t18, **kw)
    assert meta_a == meta_b
    assert inst_a["T"] == inst_b["T"]
    ua = u_rel(inst_a, 1, level=1)["u"]
    ub = u_rel(inst_b, 1, level=1)["u"]
    assert ua == ub


def test_runner_all_pass():
    res = run_unit_gates()
    assert res["all_pass"], {k: v.get("ok") for k, v in res.items()
                             if isinstance(v, dict)}
