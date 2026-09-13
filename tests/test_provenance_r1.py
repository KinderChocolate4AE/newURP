"""R1 provenance 보증 — `world_hash` 가 의미를 가지는 근거를 기계로 강제한다.

`shepherd/provenance.world_hash` 는 "같은 캠페인의 모든 레코드는 같은 세계에서 나왔다"
를 한 값으로 말하는 것이 목적이다. 그 주장이 성립하려면 **`SCENARIO_VARYING` 이 실제로
유일한 변동 축**이어야 한다. 그건 선언으로 되는 게 아니라 여기서 검증된다 — 새 캠페인이
다른 축을 흔들기 시작하면 T3 가 먼저 깨진다 (조용한 pooling 방지).

torch-free · 서버 불요 (env 빌드 몇 개).
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shepherd.m4_env import build_m4_env, manifest_mismatch      # noqa: E402
from shepherd.provenance import (                                # noqa: E402
    SCENARIO_VARYING, campaign_world_hash, git_commit, stamp, world_hash)
from shepherd.scripts.r2b_c_runner import SEED0, scenario_kwargs  # noqa: E402
from shepherd.scripts.r2b_phase1 import _cells, _slices           # noqa: E402

# 격자 전역에서 뽑은 시나리오 (셀·slice 가 서로 다르도록)
SCENARIOS = (0, 3, 1200, 1600, 2001, 2790, 3609)


@pytest.fixture(scope="module")
def stacks():
    cells, sls = _cells(), _slices()
    return {s: build_m4_env(SEED0, s, **scenario_kwargs(s, cells, sls)[5])
            for s in SCENARIOS}


def test_t1_contract_hash_is_per_scenario(stacks):
    """전제 확인: contract_hash 는 시나리오마다 다르다 (χ, η 실현값 때문)."""
    hs = {s: st.contract["hash"] for s, st in stacks.items()}
    assert len(set(hs.values())) == len(hs), f"해시가 겹친다 — 좌표가 안 움직였다: {hs}"


def test_t2_world_hash_is_campaign_invariant(stacks):
    """핵심: 시나리오 실현값을 걷어내면 **하나의** 세계만 남는다."""
    assert len({world_hash(st.contract) for st in stacks.values()}) == 1
    assert campaign_world_hash(list(stacks.values()))          # 터지지 않아야 한다


def test_t3_scenario_varying_is_the_only_axis(stacks):
    """`SCENARIO_VARYING` 밖의 축이 흔들리면 world_hash 는 거짓말이 된다.

    이 테스트가 R1 보증의 실체다 — 깨지면 `SCENARIO_VARYING` 을 고칠 게 아니라
    **왜 새 축이 움직이는지**를 먼저 물어야 한다.
    """
    ref = stacks[SCENARIOS[0]].contract
    seen = set()
    for s in SCENARIOS[1:]:
        seen |= set(manifest_mismatch(ref, stacks[s].contract))
    assert seen <= set(SCENARIO_VARYING), (
        f"선언되지 않은 변동 축: {sorted(seen - set(SCENARIO_VARYING))}")


def test_t4_world_hash_reacts_to_a_real_world_change(stacks):
    """음성 대조: 세계를 실제로 바꾸면 world_hash 도 바뀌어야 한다 (무딘 해시 방지)."""
    import copy
    c = copy.deepcopy(stacks[SCENARIOS[0]].contract)
    base = world_hash(c)
    c["judge"] = str(c["judge"]) + "_MUTATED"
    assert world_hash(c) != base
    c2 = copy.deepcopy(stacks[SCENARIOS[0]].contract)
    c2["attacker"]["route_gain"] = float(c2["attacker"]["route_gain"]) + 0.1
    assert world_hash(c2) != base, "적대자 스펙 변화가 world_hash 에 안 잡힌다"


def test_t5_campaign_world_hash_rejects_mixed_worlds(stacks):
    """다른 세계가 섞이면 조용히 지나가지 않고 터진다."""
    import copy
    a = stacks[SCENARIOS[0]].contract
    b = copy.deepcopy(a)
    b["n_segments"] = int(b["n_segments"]) + 1
    with pytest.raises(AssertionError):
        campaign_world_hash([a, b])


def test_t6_stamp_shape_and_readonly(stacks):
    """stamp 는 결과에 실을 수 있는 평범한 dict 이고 stack 을 건드리지 않는다."""
    st = stacks[SCENARIOS[0]]
    before = dict(st.contract)
    p = stamp(st, note="unit")
    assert p["contract_hash"] == st.contract["hash"]
    assert p["world_hash"] == world_hash(st.contract)
    assert p["provenance_schema"] == 1 and p["note"] == "unit"
    assert isinstance(p["code_commit"], str) and p["code_commit"]
    assert st.contract == before, "stamp 가 contract 를 변형했다"

    bare = stamp()                      # 계약 없는 해석 산출물 (판독기 등)
    assert "contract_hash" not in bare and bare["code_commit"] == git_commit()
