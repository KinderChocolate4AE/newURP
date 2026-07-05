"""eval_heldout smoke (torch venv only; sandbox CI skips)."""
import pytest

torch = pytest.importorskip("torch")
pytestmark = pytest.mark.torch


def test_module_surface():
    from shepherd.scripts import eval_heldout as m
    assert m.EVAL_SEED0 == 77_000_000 and m.EPISODES == 200
    assert callable(m.learned_fns) and callable(m.run_episodes)


def test_heldout_seed_disjoint_from_training():
    """Training eval seeds (s*1_000_003+500_000) and episode seeds stay below
    the held-out base for all campaign seeds 0..9."""
    from shepherd.scripts.eval_heldout import EVAL_SEED0
    for s in range(10):
        assert s * 1_000_003 + 500_000 + 10_000 < EVAL_SEED0
        assert s * 1_000_003 + 1 + 50_000 < EVAL_SEED0
