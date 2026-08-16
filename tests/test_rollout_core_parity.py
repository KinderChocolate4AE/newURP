"""R-004 회귀 게이트 — 두 롤아웃 core 의 semantic outcome parity (Session 4 Stage 1).

WHY (감사 Session 1 §J-1, Session 2 X-008)
------------------------------------------
리포에는 실행 core 가 **둘** 있고 과학 결과가 그 둘에 나뉘어 실려 있다.

    mission_rollout.run_episode     헤드라인 곡선 (curve_sweep -> paper_figs)
    recoverability_probe._Driver    E1d/E1e/E3/E4/lead-time/뷰어 전부

그런데 `run_episode` 를 import 하는 테스트 파일과 `_Driver` 를 import 하는 테스트
파일이 **서로소**였다 -- 둘이 일치한다는 것을 강제하는 테스트가 하나도 없었다.
Session 2 가 25 판 실측으로 일치를 확인했지만 그건 일회성 관측이고 회귀가 아니다.

★ finding 의 성격 (R-001 과 다름): "두 core 가 불일치한다" 가 아니라
  **"일치를 지속적으로 강제하는 테스트가 없다"** 이다. 따라서 이 게이트는
  patch 전에도 GREEN 인 것이 정상이며, GREEN 이라고 finding 이 폐기되지 않는다.
  성공 조건은 셋뿐이다:
    ① 현 HEAD 에서 mismatch 0 임을 확인
    ② 미래 divergence 를 잡을 구조인가
    ③ **커버리지 없는 class 를 검증했다고 거짓말하지 않는다**

정규화 projection (literal equality 금지)
-----------------------------------------
두 core 의 라벨 어휘가 다르다. `_Driver` 는 접촉 집합을 세지 않으므로
`CAPTURE_WITH_CONTACT` 를 **구조적으로 낼 수 없다**. 그러므로 literal 비교를
요구하는 것은 테스트 설계 오류다. 비교는 semantic class 로 한다.

    NET_CAPTURE          ┐
    CAPTURE_WITH_CONTACT ├──> CAPTURED
    HARD_KILL  / PENETRATED / SPENT_FAIL / TRUNCATED  ──> 그대로

★ 커버리지는 assertion 계약의 일부다 (Stage 1 교훈)
---------------------------------------------------
    An equivalence test that never visits a discriminating semantic class
    establishes no parity for that class.

그래서 class 별 parity 를 **따로** 파라미터화하고, 자연 rollout 이 방문하지 못한
class 는 `skip` 으로 남긴다 -- "0 건이라 통과" 와 "검증했다" 를 리포트에서
구분하기 위해서다. 조용히 통과시키지 않는다.

현재 커버리지 (2026-08-17 실측):
    CAPTURED · HARD_KILL · PENETRATED   T1 자연 rollout
    SPENT_FAIL                          legacy 계약(miss_terminates=True) + x_fire
    TRUNCATED                           짧은 지평선(episode_len=8)
    CAPTURE_WITH_CONTACT                **rollout 레벨 미관측** -- 아래 참조

CWC 는 왜 rollout fixture 가 없는가 (정직 기록)
----------------------------------------------
CWC = 포획 성공 ∧ 접촉 발생 이다. 탐색 결과 두 조건이 같은 세계에서 동시에
성립하는 싼 조합을 찾지 못했다: 접촉이 쉬운 팔(ring/intercept, 접촉 8/8)에서는
포획이 아예 안 나고, 포획이 나는 팔(T1 hold)에서는 접촉이 0/10 이다.
`physics.kill_radius` 를 키우면 접촉 resolver 반경도 같이 커져 전부 HARD_KILL 이
된다. 새 science scenario 를 발명하거나 private state 를 조작하는 대신,
**어휘 계약 자체를 구조적으로 고정**하고(`test_r004_projection_contract`)
rollout 커버리지는 UNOBSERVED 로 명시한다.

torch-free.
"""
from __future__ import annotations

import collections

import pytest

from shepherd.agents.attacker_ladder import AttackerSpec
from shepherd.env_sys import (ModeSystemEnv, RewardSpec, SystemSpec,
                              ratified_system)
from shepherd.m4_env import build_m4_env
from shepherd.params import as_config
from shepherd.scripts.mission_rollout import LABELS, run_episode
from shepherd.scripts.recoverability_probe import _Driver
from shepherd.spawn_rand import SpawnSpec
from shepherd.train.make_env import make_train_env

#: run_episode 어휘 -> _Driver 어휘. 두 core 비교의 유일한 정본.
PROJECTION = {
    "NET_CAPTURE": "CAPTURED",
    "CAPTURE_WITH_CONTACT": "CAPTURED",
    "HARD_KILL": "HARD_KILL",
    "PENETRATED": "PENETRATED",
    "SPENT_FAIL": "SPENT_FAIL",
    "TRUNCATED": "TRUNCATED",
}
DRIVER_LABELS = tuple(sorted(set(PROJECTION.values())))

SLOW_LIMITER = {"train.limits.limiter_v_max": 21.0}


# ------------------------------------------------------------------ worlds ---
def _t1_world(ep: int):
    """비준 계약 + T1 -- curve_sweep / E-series 와 **동일 세계**."""
    st = build_m4_env(
        0, ep, system=ratified_system(),
        reward=RewardSpec(w_kill=0.5, enabled=True),
        attacker=AttackerSpec(level="A2", jink_amp=0.6, seed=0,
                              route_gain=0.5, sense_range=30.0),
        spawn=SpawnSpec())
    return st.env, st.scn, st.lay


def _legacy_world(over=None):
    """동결 params + legacy 계약 (miss_terminates=True) -- SPENT_FAIL 이 살아 있다."""
    def _f(ep: int):
        inner, scn, lay = make_train_env(as_config(over or SLOW_LIMITER))
        env = ModeSystemEnv(inner, lay, scn, SystemSpec(enabled=True),
                            RewardSpec(w_kill=0.5, enabled=True))
        return env, scn, lay
    return _f


_SHORT = dict(SLOW_LIMITER, **{"train.episode_len": 8})

#: (arm 이름, world 팩토리, n, limiter_mode, baseline_commit, fire_mode)
#: 자연 2x2 (T1) + 희소 class 를 겨냥한 fixture 둘.
#: ★ hold x commit=True 는 curve_sweep 정정 8 에 따라 hold x commit=False 와
#:   **동일**하다 (hold 행동의 idx3 이 0 이라 커밋 비트가 서지 않는다). 퇴화 cell
#:   임을 알고 넣는다 -- 그 문서화된 동치를 회귀로 고정하는 값이 있다.
ARMS = (
    ("T1 hold/nocommit",       _t1_world,              6, "hold",      False, "clean"),
    ("T1 hold/commit",         _t1_world,              6, "hold",      True,  "clean"),
    ("T1 intercept/nocommit",  _t1_world,              6, "intercept", False, "clean"),
    ("T1 intercept/commit",    _t1_world,              6, "intercept", True,  "clean"),
    ("legacy intercept/xfire", _legacy_world(),        6, "intercept", False, "x_fire"),
    ("legacy short-horizon",   _legacy_world(_SHORT),  5, "hold",      False, "clean"),
)


def _one(mk, ep, mode, commit, fire):
    """같은 (world, seed) 를 두 core 에 각각 굴려 (run_episode 라벨, _Driver 라벨)."""
    env, scn, lay = mk(ep)
    r = run_episode(env, scn, lay, seed=ep, limiter_mode=mode,
                    fire_mode=fire, baseline_commit=commit)

    env2, scn2, lay2 = mk(ep)
    d = _Driver(env2, scn2, lay2, ep)
    d.fire_mode = fire
    for _ in range(int(lay2.episode_len)):
        d.step(limiter_mode=mode, baseline_commit=commit)
        if d.done:
            break
    return r.label, d.label


@pytest.fixture(scope="module")
def sweep():
    """전 arm 을 한 번만 굴려 parity 검정과 커버리지 리포트가 공유한다."""
    rows = []
    for name, mk, n, mode, commit, fire in ARMS:
        for ep in range(n):
            run_label, drv_label = _one(mk, ep, mode, commit, fire)
            rows.append({"arm": name, "episode": ep,
                         "run": run_label, "drv": drv_label,
                         "projected": PROJECTION.get(run_label)})
    return rows


# ------------------------------------------------------- 구조적 어휘 계약 ---
def test_r004_projection_contract():
    """projection 이 `LABELS` 전체를 덮고, 상 image 가 `_Driver` 어휘와 정확히 같다.

    rollout 없이도 성립하는 계약이라 **항상 실행된다** -- CWC 가 자연 rollout 에서
    관측되지 않아도 어휘 주장 자체는 여기서 고정된다.
    """
    assert set(PROJECTION) == set(LABELS), \
        "projection 이 mission_rollout.LABELS 를 전부 덮지 않는다"
    # 두 포획 라벨은 같은 semantic class 로 접힌다 -- 이것이 CWC 관련 핵심 주장
    assert PROJECTION["NET_CAPTURE"] == PROJECTION["CAPTURE_WITH_CONTACT"] == "CAPTURED"
    # 접힘은 포획 축에서만 일어난다 (나머지는 항등)
    for lab in ("HARD_KILL", "PENETRATED", "SPENT_FAIL", "TRUNCATED"):
        assert PROJECTION[lab] == lab, f"{lab} 이 항등이 아니다"
    # _Driver 가 낼 수 있는 라벨 집합과 일치 (recoverability_probe._Driver.step)
    assert set(DRIVER_LABELS) == {"CAPTURED", "HARD_KILL", "PENETRATED",
                                  "SPENT_FAIL", "TRUNCATED"}
    assert len(LABELS) == 6 and len(DRIVER_LABELS) == 5, \
        "어휘 크기가 바뀌었다 -- projection 을 재검토할 것"


# ------------------------------------------------------------ parity 본체 ---
def test_r004_cores_agree_under_projection(sweep):
    """★ 본 게이트 — 전 arm 에서 정규화 outcome 이 일치한다 (mismatch 0)."""
    bad = [r for r in sweep if r["projected"] != r["drv"]]
    assert not bad, "두 롤아웃 core 가 갈라졌다:\n" + "\n".join(
        f"  {r['arm']} ep{r['episode']}: run_episode {r['run']} "
        f"-> {r['projected']} != _Driver {r['drv']}" for r in bad)
    assert len(sweep) == sum(a[2] for a in ARMS), "일부 arm 이 실행되지 않았다"


def test_r004_every_arm_produced_episodes(sweep):
    """arm 하나가 통째로 비면 그 arm 의 parity 는 검증된 적이 없는 것이다."""
    per_arm = collections.Counter(r["arm"] for r in sweep)
    missing = [a[0] for a in ARMS if per_arm[a[0]] == 0]
    assert not missing, f"실행되지 않은 arm: {missing}"


# --------------------------------------------------- class 별 커버리지 ---
@pytest.mark.parametrize("cls", DRIVER_LABELS)
def test_r004_parity_within_class(sweep, cls):
    """class 별 parity. **관측되지 않은 class 는 skip 으로 남긴다.**

    "0 건이므로 통과" 와 "그 class 의 parity 를 검증했다" 는 다른 사실이다.
    리포트에서 그 둘이 구분되지 않으면 커버리지 부재가 성공으로 읽힌다.
    """
    sel = [r for r in sweep if r["drv"] == cls or r["projected"] == cls]
    if not sel:
        pytest.skip(f"UNOBSERVED: '{cls}' 는 등록된 arm 의 자연 rollout 에서 "
                    "한 번도 나오지 않았다 -- 이 class 의 parity 는 미검증이다")
    bad = [r for r in sel if r["projected"] != r["drv"]]
    assert not bad, f"class {cls} 에서 불일치 {len(bad)}/{len(sel)}: {bad[:3]}"


def test_r004_coverage_is_reported(sweep, capsys):
    """관측 커버리지를 리포트로 남긴다 (assertion 이 아니라 기록).

    다만 **완전히 공회전한 게이트**는 실패로 만든다 -- class 를 하나도 못 봤다면
    parity 검정 자체가 무의미하다.
    """
    obs = collections.Counter(r["drv"] for r in sweep)
    lines = [f"  {c:<12} n={obs.get(c, 0)}" for c in DRIVER_LABELS]
    unobs = [c for c in DRIVER_LABELS if not obs.get(c)]
    with capsys.disabled():
        print("\n[R-004] semantic class 커버리지 (n=%d, arms=%d)"
              % (len(sweep), len(ARMS)))
        print("\n".join(lines))
        for c in unobs:
            print(f"  NOT OBSERVED: {c}")
        # CWC 는 _Driver 가 구조적으로 못 내는 라벨이므로 run 쪽만 따로 본다
        n_cwc = sum(1 for r in sweep if r["run"] == "CAPTURE_WITH_CONTACT")
        print(f"  run-side CAPTURE_WITH_CONTACT n={n_cwc}"
              + ("   <- UNOBSERVED (어휘 계약은 projection_contract 가 고정)"
                 if not n_cwc else ""))
    assert len(DRIVER_LABELS) - len(unobs) >= 3, (
        f"관측된 class 가 {len(DRIVER_LABELS) - len(unobs)} 개뿐 — "
        "게이트가 거의 공회전했다")


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q", "-s"]))
