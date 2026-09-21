import json

from shepherd.scripts.b0_v3_mappo_pilot import (make_run_cfg, scheduled_cell,
                                                 select_candidate)
from shepherd.scripts.b0_v3_pilot_manifest import MANIFEST, build, load
from shepherd.scripts.b2_manifest import load as load_b2


def test_manifest_file_is_exact_builder_output():
    assert load() == build()
    assert json.loads(MANIFEST.read_text(encoding="utf-8")) == build()


def test_sampler_has_declared_mix_and_row_coverage():
    b2 = load_b2()
    strata, rows = [], []
    for ep in range(140):
        cell, stratum = scheduled_cell(b2, 0, ep)
        strata.append(stratum)
        rows.append(cell["row"])
        if stratum == "frontier":
            assert cell["chi_role"] in ("lo", "hi")
        elif stratum == "anchor":
            assert cell["chi_role"] in ("lo_out", "hi_out")
    assert strata.count("frontier") == 98
    assert strata.count("anchor") == 28
    assert strata.count("uniform") == 14
    assert {r: rows.count(r) for r in range(14)} == {r: 10 for r in range(14)}


def test_all_candidates_keep_kinetic_commit_absent():
    m = build()
    for candidate in m["candidates"]:
        cfg = make_run_cfg(m, candidate)
        assert cfg["mappo"]["limiter_commit"] is False
        assert cfg["mappo"]["coma_mix"] == 0.0
        assert cfg["loop"]["total_env_steps"] == 32768


def _summary(pn, ph, pf):
    return {"evaluation": {"p_N": pn, "p_H_illegal": ph, "p_FIRE": pf}}


def test_selection_applies_gate_then_tie_break():
    m = build()
    summaries = {
        "c0_base": [_summary(.205, .02, .7), _summary(.205, .02, .7)],
        "c1_entropy": [_summary(.20, .01, .7), _summary(.20, .01, .7)],
        "c2_low_lr": [_summary(.30, .10, .7), _summary(.30, .10, .7)],
        "c3_no_pbrs": [_summary(.01, .00, .7), _summary(.01, .00, .7)],
    }
    out = select_candidate(summaries, m)
    assert out["decision"] == "SELECT"
    assert out["selected"] == "c1_entropy"  # within .01; lower illegal wins


def test_no_selection_when_every_candidate_misses_gate():
    m = build()
    summaries = {c: [_summary(.01, .00, .7), _summary(.01, .00, .7)]
                 for c in m["candidates"]}
    assert select_candidate(summaries, m)["decision"] == "NO_SELECTION"
