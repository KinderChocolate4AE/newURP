"""W5 판정기의 crossing·coverage 분기 검사."""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shepherd.scripts.b2_w5_decision import coverage_pass, frontier  # noqa: E402


def _fixture(low=0.8, high=0.2):
    cells, rates = [], {}
    for row in range(14):
        for col, (chi, p) in enumerate(zip((0.4, 0.5, 0.6, 0.7),
                                            (low, 0.6, 0.4, high))):
            cid = f"r{row:02d}c{col}"
            cells.append({"cell_id": cid, "row": row, "chi": chi,
                          "eta": 2.1 + 0.3 * (row % 7),
                          "lam_slice": 0 if row < 7 else 2,
                          "lam": 4.6 if row < 7 else 3.6})
            for seed in (0, 1, 2):
                rates[f"{cid}|RULE_COOP|{seed}"] = {"n": 300, "p_N": p}
    return {"cells": cells, "crn": {"seeds": [0, 1, 2]}}, {
        "by_cell_arm_seed": rates,
    }


def test_all_rows_and_slices_pass_when_crossings_are_inside_grid():
    m, readout = _fixture()
    result = frontier(m, readout)
    assert result["row_estimable"] == 14
    assert result["slice_counts"]["0"]["row_estimable"] == 7
    assert result["slice_counts"]["2"]["row_estimable"] == 7
    assert not result["any_censored"]
    assert coverage_pass(result)


def test_censoring_blocks_pass_and_requests_extension():
    m, readout = _fixture(low=0.9, high=0.8)
    result = frontier(m, readout)
    assert result["any_censored"]
    assert result["row_estimable"] == 0
    assert not coverage_pass(result)
