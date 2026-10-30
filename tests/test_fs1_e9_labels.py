"""E9 (docs/144) 라벨 의미 단위 테스트 + 참조 셀 χ_eff 정합 + 보어사이트 오프셋 기하."""
import math
import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import fs1_e4_manifest as E4  # noqa: E402
import fs1_e9_manifest as M  # noqa: E402
from fs1_e7_probe import _offset  # noqa: E402


def _win(cell=3.0, ref=3.0, base=4.0, override=None):
    w = {}
    for c in M.GRID:
        w[c["name"]] = base if c["family"] == "base" else ref if c["family"] == "ref" else cell
    w.update(override or {})
    return w


def test_conservative_when_nonideal_not_below_ref():
    v = M.verdict(_win(cell=3.0, ref=2.0))
    assert {f: v[f]["verdict"] for f in M.FAMILIES} == {f: "FOLD_CONSERVATIVE" for f in M.FAMILIES}


def test_tolerance_edge_passes_and_beyond_breaks():
    assert M.verdict(_win(cell=1.5, ref=3.0))["L"]["verdict"] == "FOLD_CONSERVATIVE"   # gap −1.5 = 허용 끝
    one = "t0.5_h1.0_cv_L2"
    v = M.verdict(_win(cell=3.0, ref=3.0, override={one: 1.0}))                         # gap −2 한 셀
    assert v["L"]["verdict"] == "FOLD_BREAKS" and v["L"]["failing"] == [one]
    assert v["d"]["verdict"] == "FOLD_CONSERVATIVE"                                       # 다른 가족 불변


def test_floor_is_undecidable_not_conservative():
    v = M.verdict(_win(cell=0.0, ref=0.0, base=0.0))
    assert all(v[f]["verdict"] == "FOLD_UNDECIDABLE_FLOOR" for f in M.FAMILIES)


def test_reference_cell_sits_at_cell_chi_eff():
    by = {c["name"]: c for c in M.GRID}
    for c in M.GRID:
        if c["family"] in M.FAMILIES:
            assert 1.0 / E4.rho(by[c["ref"]]) == pytest.approx(M.chi_eff(c), rel=1e-12)
        if c["family"] == "base":
            assert c["name"] in {g["name"] for g in E4.GRID}                               # E4 wiring 이름
            assert M.chi_eff(c) == pytest.approx(1.0 / E4.rho(c), rel=1e-12)


@pytest.mark.parametrize("axis", [[1, 0, 0], [0.3, -0.2, 0.93], [0, 0, 1]])
@pytest.mark.parametrize("phi", [0.0, 1.0, 4.0])
def test_offset_angle_is_delta(axis, phi):
    a = np.asarray(axis, float) / np.linalg.norm(axis)
    for d in M.DELTAS:
        n = _offset(a, d, phi)
        assert np.linalg.norm(n) == pytest.approx(1.0, abs=1e-12)
        assert math.acos(np.clip(n @ a, -1, 1)) == pytest.approx(d, abs=1e-12)
