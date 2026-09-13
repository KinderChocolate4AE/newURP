"""Sealed-replay parity — refactor 가 실행 의미를 움직였는지 잡는 안전망 (R2/R3 hygiene).

**비교 구조가 핵심이다.** `100-X` 는 재구현을 **또 다른 재구현**과 대조해서 버그를 놓쳤다.
여기서는 항상 **봉인된 실행 산출물**과 대조한다.

두 층으로 나눈 이유 (2026-09-14 실측):

    tick 스트림 해시는 **머신 간 이식되지 않는다.**

서버(Linux)가 만든 `telemetry_hash` 를 이 머신(Windows)에서 재현하면 tick 0 의 `p_att`
부터 **1 ULP** 다르다 (`3.082989901527214` vs `3.0829899015272137`) — 스텝을 밟기 전
초기 상태부터다. docs/95 §6.8 이 "bit-parity 는 머신별 재확인이다" 라고 적어둔 것과
정합하며, 따라서 해시는 **교차-머신 앵커로 쓸 수 없다.**

  **층 1 (machine-independent)**: 종말 결과 `(label, fire_step, steps)` · `plan_hash` ·
    world 해시 ← **커밋된 shard** 와 직접 대조. 머신이 달라도 성립해야 한다.
  **층 2 (same-machine, bit-level)**: 전체 tick 스트림 해시 ← **refactor 전에 이 머신에서
    떠서 커밋한 baseline** 과 대조. 플랫폼이 다르면 skip.

baseline 갱신:  python -m tests.test_sealed_replay_parity --capture
(refactor **전에만** 뜬다. 실패했다고 다시 뜨면 안전망이 무의미해진다.)
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import platform
import sys

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shepherd.m4_env import build_m4_env                               # noqa: E402
from shepherd.scripts.r2b_c_runner import SEED0, scenario_kwargs       # noqa: E402
from shepherd.scripts.r2b_geom_probe import _logged_replay             # noqa: E402
from shepherd.scripts.r2b_phase1 import _cells, _slices                # noqa: E402

PROBE = ROOT / "artifacts/r2b/geom_probe"
BASELINE = ROOT / "artifacts/r2b/replay_parity_baseline.json"
#: 대표 3 판 (s 오름차순 앞쪽 — 결정론적, 선택 자유도 없음)
PICKS = (0, 1, 3)


def _plat():
    return f"{platform.system()}-{platform.machine()}-py{sys.version_info[:2]}"


def _sealed():
    out = {}
    for f in sorted(PROBE.glob("shard*.json")):
        for r in json.loads(f.read_text(encoding="utf-8"))["records"]:
            if r["s"] in PICKS:
                out[r["s"]] = r
    return out


def _replay(s, rec):
    cells, sls = _cells(), _slices()
    kw = scenario_kwargs(s, cells, sls)[5]
    plan = np.asarray(rec["plan"], float)
    r, ticks, _ = _logged_replay(build_m4_env(SEED0, s, **kw), s, plan)
    h = hashlib.sha256(json.dumps(ticks, sort_keys=True).encode()).hexdigest()[:16]
    return r, h


# ── 층 1: machine-independent — 커밋된 봉인 산출물과 직접 대조 ──────────────────
@pytest.mark.parametrize("s", PICKS)
def test_outcome_matches_sealed_artifact(s):
    sealed = _sealed()
    if s not in sealed:
        pytest.skip(f"s={s} 가 봉인 산출물에 없다")
    rec = sealed[s]
    assert (hashlib.sha256(np.asarray(rec["plan"], float).tobytes()).hexdigest()[:16]
            == rec["plan_hash"]), "plan 입력 자체가 봉인된 것과 다르다"
    r, _ = _replay(s, rec)
    assert (r.label, r.fire_step, r.steps) == (rec["label"], rec["fire_step"],
                                               rec["steps"]), (
        f"s={s}: 종말 결과 drift — refactor 가 실행 의미를 바꿨다")


def test_world_hashes_unchanged():
    sealed = _sealed()
    assert sealed, "봉인 산출물을 찾지 못했다"
    assert {r["b0_v3_hash"] for r in sealed.values()} == {"5e7b5b486b9d8a4a"}
    assert {r["r2b_b0_hash"] for r in sealed.values()} == {"cba024d7ee3d9f61"}


# ── 층 2: same-machine bit-level — refactor 전 baseline 과 대조 ────────────────
def test_tick_stream_bit_identical_to_local_baseline():
    """전체 tick 스트림 해시 — env·attacker·viability·RNG 의미 변화를 전부 덮는다."""
    if not BASELINE.exists():
        pytest.skip("baseline 없음 — `--capture` 로 refactor 전에 떠야 한다")
    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    if base.get("platform") != _plat():
        pytest.skip(f"baseline 플랫폼 {base.get('platform')} != {_plat()} "
                    "(tick 해시는 머신 간 이식되지 않는다)")
    sealed = _sealed()
    bad = []
    for s_str, want in base["telemetry_hash"].items():
        s = int(s_str)
        if s not in sealed:
            continue
        _, got = _replay(s, sealed[s])
        if got != want:
            bad.append((s, want, got))
    assert not bad, f"tick 스트림 drift: {bad} — behavior-preserving 위반"


def _capture():
    sealed = _sealed()
    out = {"platform": _plat(), "picks": list(PICKS), "telemetry_hash": {},
           "note": "same-machine bit-level baseline; NOT portable across machines"}
    for s in PICKS:
        if s not in sealed:
            continue
        r, h = _replay(s, sealed[s])
        out["telemetry_hash"][str(s)] = h
        print(f"  s={s}: {r.label} fire={r.fire_step} steps={r.steps}  hash {h}")
    BASELINE.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {BASELINE}  ({_plat()})")


if __name__ == "__main__":
    if "--capture" in sys.argv:
        _capture()
