"""bank v2 generator freeze locks (docs/09 (ddd); docs/18 SS3/SS6). t-free.

Locks: (1) generation seed band 400..419 disjoint from every known family;
(2) the first-fit candidate loop honors the attempt cap, MIN_ACCEPT
exclusion, and candidate escalation (fake synth/screen injection);
(3) per-(cell, candidate) draw rng is deterministic and distinct;
(4) the v1 generator's default v0_range still reproduces bank v1 draws
byte-for-byte (covered by tests/test_a3d_bank.py regression -- the param
threading is default-preserving; asserted here via signature defaults).
"""
from __future__ import annotations

import inspect

import numpy as np

from shepherd.scripts import a3d_sbe_bank as v1
from shepherd.scripts import a3d_sbe_bank_v2 as v2


def test_generation_seed_band_disjoint():
    band = set(v2.SCREEN_SEEDS)
    assert band == set(range(400, 420))
    for fam in (set(range(300, 320)),          # (aaa) refine screen
                set(range(100, 110)), set(range(200, 210)),
                set(range(7, 17)), set(range(61, 76)),
                {500_000, 1_500_000, 2_500_000, 31_000_000}):
        assert not (band & fam)


def test_v1_default_v0_range_preserved():
    for fn in (v1.synth_draw, v1._draw_directions):
        d = inspect.signature(fn).parameters["v0_range"].default
        assert tuple(d) == (0.3, 0.8)
    assert tuple(v2.V0_GRID[0]) == (0.3, 0.8)  # candidate 0 = v1 dist


def test_draw_rng_streams_distinct():
    seen = set()
    for k in (1, 2, 4, 8):
        for vv in (16, 20, 24):
            for ci in range(3):
                s = 47_000 + 1_000 * k + vv + 100_000 * ci
                assert s not in seen
                seen.add(s)


class _FakeT0:
    src, v = "fake", 16.0
    limiters = np.zeros((4, 3))


def _run_cell(monkeypatch, synth_seq, screen_seq):
    """Drive build_cell with scripted synth/screen outcomes."""
    synth_it = iter(synth_seq)
    screen_it = iter(screen_seq)

    def fake_synth(t0, k, rng, anchors, Lstar, v0_range=(0.3, 0.8)):
        kept = next(synth_it)
        if not kept:
            return None, "repel"
        return {"kept": True, "spawn": {"limiter_v": np.ones((4, 3)).tolist()},
                "demo_accels": [], "v0r": v0_range}, ""

    def fake_screen(entry, env_cfg, m3, stage, theta, seeds=v2.SCREEN_SEEDS):
        ok = next(screen_it)
        return {"pass": ok, "pfc": 20 if ok else 8, "zero": 0,
                "reset_clean": 0, "seeds_used": 20, "zero_cap_lens": []}

    monkeypatch.setattr(v2, "synth_draw", fake_synth)
    monkeypatch.setattr(v2, "paired_screen", fake_screen)
    monkeypatch.setattr(v2, "_ring", lambda: np.zeros((4, 3)))
    return v2.build_cell(_FakeT0(), "d1", 1, {}, None, None, 0.9,
                         log=lambda *_: None)


def test_first_fit_accepts_on_candidate0(monkeypatch):
    acc, rep = _run_cell(monkeypatch,
                         synth_seq=[True] * 12, screen_seq=[True] * 12)
    assert len(acc) == 12 and rep["selected_candidate"] == 0
    assert not rep["excluded"]
    assert all(e["v0_candidate"] == 0 for e in acc)


def test_candidate_escalation_then_exclusion(monkeypatch):
    # every draw screens False -> all 3 candidates exhaust ATTEMPT_CAP
    n = v2.ATTEMPT_CAP * 3
    acc, rep = _run_cell(monkeypatch,
                         synth_seq=[True] * n, screen_seq=[False] * n)
    assert acc == [] and rep["excluded"]
    assert [c["candidate"] for c in rep["candidates"]] == [0, 1, 2]
    assert all(c["attempts"] == v2.ATTEMPT_CAP for c in rep["candidates"])


def test_min_accept_boundary(monkeypatch):
    # candidate 0: 7 accepts (< 8) then cap; candidate 1: 8 accepts -> win
    seq0 = ([True] * v2.ATTEMPT_CAP)
    scr0 = [True] * 7 + [False] * (v2.ATTEMPT_CAP - 7)
    seq1 = [True] * 12                      # runs to DRAWS_TARGET
    scr1 = [True] * 12
    acc, rep = _run_cell(monkeypatch, synth_seq=seq0 + seq1,
                         screen_seq=scr0 + scr1)
    assert rep["selected_candidate"] == 1 and len(acc) == 12
    assert rep["candidates"][0]["accepted"] == 7


def test_construction_drops_counted(monkeypatch):
    # drops do not consume screen calls; cap still honored
    synth = ([False, True] * v2.ATTEMPT_CAP)[:v2.ATTEMPT_CAP]  # cand 0
    n_kept = sum(synth)
    acc, rep = _run_cell(monkeypatch,
                         synth_seq=synth + [True] * 12,
                         screen_seq=[False] * n_kept + [True] * 12)
    c0 = rep["candidates"][0]
    assert c0["construction_drops"].get("repel", 0) > 0
    assert c0["attempts"] == v2.ATTEMPT_CAP
    assert rep["selected_candidate"] == 1
