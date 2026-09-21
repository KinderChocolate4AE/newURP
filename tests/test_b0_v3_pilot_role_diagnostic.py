import json
from types import SimpleNamespace

import numpy as np

from scripts.b0_v3_pilot_role_diagnostic import (
    _cached_learned_both, _mean_axis_policy,
)
from shepherd.scripts.b0_v3_mappo_pilot import OUT, boundary_cells
from shepherd.scripts.b2_manifest import load as load_b2


def test_cached_learned_both_is_exact_sealed_scenario_subset():
    saved = json.loads((OUT / "c0_base" / "seed0" / "summary.json").read_text())
    result = _cached_learned_both(saved, boundary_cells(load_b2()), 3, 10)
    assert result["n"] == 84
    assert len({(r["cell_id"], r["scenario_id"]) for r in result["records"]}) == 84
    assert all(r["scenario_id"] % 10 < 3 for r in result["records"])


def test_mean_axis_probe_preserves_stochastic_fire_sample():
    class Runner:
        _adapter = SimpleNamespace(finisher_id="finisher")

        def policy_fn(self, deterministic):
            value = [9., 8., 7., 0., 0.] if deterministic else [1., 2., 3., 0., 1.]
            return lambda obs, flags: {"finisher": np.array(value, np.float32)}

    out = _mean_axis_policy(Runner())(None, {})["finisher"]
    np.testing.assert_array_equal(out, [9., 8., 7., 0., 1.])
