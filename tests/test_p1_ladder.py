"""P1 runner wiring tests: lag plant, override parsing."""
from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np
import pytest

from scripts.p1_ladder import PlantLagEnv, _overrides


class _FakeEnv:
    def __init__(self, a_max=0.0):
        self.limiter_ids = ("lim_0", "lim_1")
        self.dt = 0.05
        self.tau_deploy = 0.5
        self.sc = SimpleNamespace(finisher=SimpleNamespace(a_max=a_max))
        self.seen = []

    def reset(self):
        return "obs"

    def step(self, actions):
        self.seen.append({k: np.asarray(v, float).copy() for k, v in actions.items()})
        return "step"


def test_plant_lag_first_order_and_reset():
    env = _FakeEnv()
    lag = PlantLagEnv(env, 0.1)                      # tau_a = 0.05 = dt
    alpha = 1.0 - math.exp(-1.0)
    cmd = {"lim_0": np.array([1.0, 0.0, 0.0, 0.7]), "lim_1": np.zeros(4)}
    lag.step(cmd)
    first = env.seen[-1]["lim_0"]
    assert np.allclose(first[:3], [alpha, 0.0, 0.0])
    assert first[3] == pytest.approx(0.7)            # pressure 채널 불변
    lag.step(cmd)
    second = env.seen[-1]["lim_0"][0]
    assert second == pytest.approx(alpha + alpha * (1.0 - alpha))
    lag.reset()
    lag.step(cmd)
    assert env.seen[-1]["lim_0"][0] == pytest.approx(alpha)   # 상태 초기화
    assert np.allclose(env.seen[-1]["lim_1"], 0.0)


def test_plant_lag_refuses_mobile_finisher():
    with pytest.raises(SystemExit):
        PlantLagEnv(_FakeEnv(a_max=1.0), 0.1)


def test_override_parsing_restores_inf():
    assert _overrides({"overrides": {"sense_range": "inf", "route_gain": 0.8}}) == {
        "sense_range": float("inf"), "route_gain": 0.8}
