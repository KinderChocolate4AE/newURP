"""RunningNorm unit tests (L2 Phase 2B; torch-free)."""
from __future__ import annotations

import numpy as np
import pytest

from shepherd.train.obs_norm import RunningNorm


def test_running_stats_match_numpy():
    rng = np.random.default_rng(0)
    data = rng.normal(loc=3.0, scale=5.0, size=(1000, 7))
    norm = RunningNorm(7)
    # mixed single-obs and batch updates must agree with global stats
    for row in data[:100]:
        norm.update(row)
    norm.update(data[100:])
    assert np.allclose(norm.mean, data.mean(axis=0), atol=1e-8)
    assert np.allclose(norm.var, data.var(axis=0), rtol=1e-6, atol=1e-8)


def test_normalize_whitens_and_clips():
    rng = np.random.default_rng(1)
    data = rng.normal(loc=-2.0, scale=0.5, size=(500, 3))
    norm = RunningNorm(3, clip=5.0)
    norm.update(data)
    z = norm.normalize(data)
    assert z.dtype == np.float32
    assert np.allclose(z.mean(axis=0), 0.0, atol=1e-3)
    assert np.allclose(z.std(axis=0), 1.0, atol=1e-2)
    far = norm.normalize(np.full(3, 1e9))
    assert np.all(far <= 5.0) and np.all(np.isfinite(far))


def test_normalize_update_flag_uses_updated_stats():
    norm = RunningNorm(2)
    x = np.array([4.0, -4.0])
    z1 = norm.normalize(x, update=True)
    ref = RunningNorm(2)
    ref.update(x)
    assert np.allclose(z1, ref.normalize(x))


def test_state_dict_roundtrip():
    rng = np.random.default_rng(2)
    a = RunningNorm(4)
    a.update(rng.normal(size=(50, 4)))
    b = RunningNorm(4)
    b.load_state_dict(a.state_dict())
    x = rng.normal(size=4)
    assert np.allclose(a.normalize(x), b.normalize(x))
    assert b.count == a.count


def test_guards():
    norm = RunningNorm(3)
    with pytest.raises(ValueError):
        norm.update(np.zeros(4))                      # wrong dim
    with pytest.raises(FloatingPointError):
        norm.update(np.array([1.0, np.nan, 0.0]))     # non-finite
    with pytest.raises(ValueError):
        RunningNorm(0)                                # bad dim
    with pytest.raises(ValueError):
        b = RunningNorm(2)
        b.load_state_dict(norm.state_dict())          # dim mismatch


def test_early_updates_dominate_prior():
    # after a single update the output should already be ~zero-mean, not
    # dominated by the zero/one init prior
    norm = RunningNorm(2, eps=1e-4)
    batch = np.array([[10.0, -10.0], [12.0, -12.0]])
    norm.update(batch)
    z = norm.normalize(np.array([11.0, -11.0]))
    assert np.all(np.abs(z) < 1.0)
