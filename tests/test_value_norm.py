"""ValueNorm unit tests (L2 Phase 2C; torch-free)."""
from __future__ import annotations

import numpy as np
import pytest

from shepherd.train.value_norm import ValueNorm


def test_running_stats_match_numpy():
    rng = np.random.default_rng(0)
    data = rng.normal(loc=5.0, scale=3.0, size=1000)
    vn = ValueNorm()
    for chunk in np.split(data, 10):
        vn.update(chunk)
    # eps pseudo-count (1e-4) leaves a ~1e-6 bias vs exact batch stats
    assert vn.mean == pytest.approx(data.mean(), abs=1e-5)
    assert vn.var == pytest.approx(data.var(), rel=1e-4)


def test_normalize_denormalize_roundtrip():
    rng = np.random.default_rng(1)
    vn = ValueNorm()
    data = rng.normal(loc=-2.0, scale=7.0, size=2000)
    vn.update(data)
    x = rng.normal(size=64)
    assert np.allclose(vn.denormalize(vn.normalize(x)), x, atol=1e-10)
    z = vn.normalize(data)          # same data the stats were built from
    assert abs(float(z.mean())) < 0.05 and abs(float(z.std()) - 1.0) < 0.05


def test_guards():
    vn = ValueNorm()
    with pytest.raises(ValueError):
        vn.update(np.array([]))
    with pytest.raises(FloatingPointError):
        vn.update(np.array([1.0, np.nan]))


def test_state_dict_roundtrip():
    rng = np.random.default_rng(2)
    a = ValueNorm()
    a.update(rng.normal(size=100))
    b = ValueNorm()
    b.load_state_dict(a.state_dict())
    x = rng.normal(size=5)
    assert np.allclose(a.normalize(x), b.normalize(x))
    assert b.count == a.count


def test_scale_drift_tracking():
    # mode switch: returns jump from ~N(3,1) to ~N(40,5); running stats follow
    vn = ValueNorm()
    rng = np.random.default_rng(3)
    vn.update(rng.normal(3.0, 1.0, size=500))
    m1 = vn.mean
    vn.update(rng.normal(40.0, 5.0, size=2000))
    assert vn.mean > m1 + 20.0            # stats moved toward the new regime
