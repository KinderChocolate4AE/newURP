"""[D-3] validation harness freeze locks (docs/19 v0.3 SS6; docs/09 (hhh)).
t-free; committed BEFORE any validation result is read.

Locks: (1) seed band 600..699 disjoint from every family (incl. 420..439
generation + retired 400..419 smoke); (2) allocation = floor+remainder-to-
front, sums to 100 for n_d 8..12; (3) jitter streams distinct per cell,
76k namespace; (4) 4-condition verdict pure function incl. inclusive
boundaries; (5) bootstrap LCB deterministic under rng 777 and sensitive to
discordance (p01 lowers LCB vs nested); (6) pairing structural: both arms
of an episode receive the SAME materialized spawn + reset seed, PFC
reference stays nominal; (7) Gate B membership = exactly the 8 frozen
names, constructors privilege-free."""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

from shepherd.scripts import a3d_bankv2_validate as V


def test_val_seed_band_disjoint():
    band = set(V.VAL_SEEDS)
    assert band == set(range(600, 700))
    for fam in (set(range(420, 440)), set(range(400, 420)),
                set(range(300, 320)), set(range(100, 110)),
                set(range(200, 210)), set(range(7, 17)),
                set(range(61, 76)),
                {500_000, 1_500_000, 2_500_000, 31_000_000}):
        assert not (band & fam)


def test_allocation_floor_remainder_front():
    for n in range(8, 13):
        al = V.allocation(n)
        assert sum(al) == 100 and len(al) == n
        assert max(al) - min(al) <= 1
        assert al == sorted(al, reverse=True)       # extras at the front
    assert V.allocation(12) == [9, 9, 9, 9] + [8] * 8
    assert V.allocation(9) == [12] + [11] * 8


def test_jitter_streams_distinct_and_in_band():
    seen = set()
    for k, v in ((1, 16), (2, 16), (1, 20), (2, 20), (2, 24), (4, 24),
                 (8, 24)):
        s = V.JITTER_BASE + 1_000 * k + v
        assert 76_000 <= s < 85_000 and s not in seen
        seen.add(s)
    for other in (71_000, 75_000, 81_000, 90_000, 93_000, 95_000):
        assert other not in seen


def test_verdict_pure_and_inclusive_boundaries():
    ok = V.cell_verdict(0.2, 0.8, 0.2, 0.401)       # all inclusive edges
    assert ok["admissible"] and all(ok[k] for k in
                                    ("A_no_preempt", "B_feasibility",
                                     "C_action_necessity", "D_gap_lcb"))
    assert not V.cell_verdict(0.21, 0.9, 0.0, 0.9)["admissible"]   # A
    assert not V.cell_verdict(0.0, 0.79, 0.0, 0.9)["admissible"]   # B
    assert not V.cell_verdict(0.0, 0.9, 0.21, 0.9)["admissible"]   # C
    assert not V.cell_verdict(0.0, 0.9, 0.0, 0.4)["admissible"]    # D strict


def test_boot_lcb_deterministic_and_discordance_sensitive():
    nested = [1] * 60 + [0] * 40                    # p01 = 0
    disc = [1] * 70 + [0] * 20 + [-1] * 10          # same mean, p01 = .1
    a = V.lcb_mean(nested, np.random.default_rng(V.BOOT_SEED))
    b = V.lcb_mean(nested, np.random.default_rng(V.BOOT_SEED))
    assert a == b                                   # rng-777 determinism
    c = V.lcb_mean(disc, np.random.default_rng(V.BOOT_SEED))
    assert abs(np.mean(nested) - np.mean(disc)) < 1e-12
    assert c < a                                    # discordance lowers LCB
    g = [[1, 1, 1], [1, 0, 1], [0, 0, 1]]
    d1 = V.cluster_lcb(g, np.random.default_rng(7))
    assert -1.0 <= d1 <= 1.0


def test_pairing_structural(monkeypatch):
    entries = [{"spawn": {"limiters": np.zeros((4, 3)).tolist(),
                          "limiter_v": np.ones((4, 3)).tolist(),
                          "att_p": [30.0, 0, 0], "att_v": [-16.0, 0, 0],
                          "att_speed": 16.0},
                "demo_accels": np.zeros((1, 4, 3)).tolist()}
               for _ in range(10)]
    calls = {}

    def fake_eval(lim_fn, spawn, seed):
        calls.setdefault(seed, []).append(json.dumps(spawn, sort_keys=True))
        return {"arrival_capture": 1, "reset_clean": 0, "captured": 1,
                "len": 5}

    plan, out = V.run_cell(entries, 1, 16.0, 0.005, {}, None, None, 0.9,
                           arms=("pfc", "zero"), eval_fn=fake_eval,
                           log=lambda *_, **__: None)
    assert len(plan) == 100 and {s for s, c in calls.items()
                                 if len(c) == 2} == set(range(600, 700))
    for seed, reprs in calls.items():
        assert reprs[0] == reprs[1]                 # identical spawn per pair
    spawns = [p[2] for p in plan]
    assert json.dumps(spawns[0]) != json.dumps(spawns[1])   # jitter varies
    al = V.allocation(10)
    assert [p[0] for p in plan] == [i for i, n in enumerate(al)
                                    for _ in range(n)]


def test_gateb_membership_and_privilege_free():
    assert V.GATEB == ("brake", "lam2", "lam5", "lam10", "lam20",
                      "attpd_2_3", "attpd_4_4", "attpd_8_6")
    entry = {"spawn": None, "demo_accels": None}    # would crash if touched
    for arm in V.GATEB:
        fn = V.arm_fn(arm, entry, 601)              # no bank/demo access
        assert callable(fn)


def test_real_bank_shape_lock():
    p = pathlib.Path("results/a3d_sbe_bank_v2.json")
    if not p.exists():
        pytest.skip("bank artifact not present")
    bank = json.loads(p.read_text())
    cells = {}
    for e in bank["entries"]:
        cells.setdefault((e["witness"], int(e["k"])), []).append(e)
    assert len(cells) == 7 and len(bank["entries"]) == 81
    sizes = sorted(len(v) for v in cells.values())
    assert sizes == [9, 12, 12, 12, 12, 12, 12]
    for (w, k), es in cells.items():
        assert V.allocation(len(es))                # 8..12 supported
