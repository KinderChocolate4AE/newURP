"""R1 provenance stamp — 결과 파일이 "어느 세계에서 나왔는가" 를 스스로 말하게 한다.

docs/81 §R1: 계약 manifest 기계는 **이미 존재**했다 (`m4_env.contract_manifest`,
`build_m4_env` 가 매 빌드마다 `M4Stack.contract` 로 붙인다) — **저장만 안 하고 있었다.**
그 결과 "파일명 보고 route_gain 추정" · "한 contract 문자열에 400/480/800 3세대" 가
가능했다. 본 모듈은 그 manifest 를 결과에 싣는 **한 줄짜리 경로**다.

두 층위를 구분한다 (이 구분이 본 모듈의 전부다):

- **`contract_hash`** — `M4Stack.contract["hash"]`. **시나리오마다 다르다.** (χ, η) 의
  실현값이 `extra_cfg` 로 들어가기 때문이다 (기계 확인 2026-09-13: 7 시나리오 → 7 해시).
- **`world_hash`** — 그 manifest 에서 **시나리오 실현값을 걷어낸** 사영. 같은 캠페인의 모든
  레코드가 공유해야 하는 값이며, "이 결과들이 같은 세계에서 나왔는가" 는 **이것**으로 묻는다.

`world_hash` 가 의미를 가지는 근거는 `SCENARIO_VARYING` 이 **실제로 유일한 변동 축**이라는
사실이고, 그것은 선언이 아니라 `tests/test_provenance_r1.py` 가 강제한다. 새 캠페인이 다른
축을 흔들기 시작하면 그 테스트가 먼저 깨진다 — 조용히 섞이지 않는다.

**behavior 0 변화**: 본 모듈은 읽기 전용이다. 물리·판정·난수에 닿지 않는다 (R1 규율).
torch-free.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: manifest 안에서 **시나리오마다 달라지는 것이 정상인** leaf 경로 = 좌표 (χ, η, λ) 의
#: 실현값. 이 목록 **밖의** 축이 흔들리면 그것은 다른 세계이며 pooling 대상이 아니다.
#: 목록은 손으로 적은 게 아니라 `test_provenance_r1.py::test_t3` 가 격자 전역에서
#: 실측해 강제한다 — 초안에서 λ 두 축이 빠져 있었고 그 테스트가 잡았다 (2026-09-13).
SCENARIO_VARYING = (
    # (χ, η) — docs/92 의 구성변수 (τ, ρ, v, a) 가 여기로 내려온다
    "extra_cfg.physics.a_att_max",
    "extra_cfg.physics.a_lim_max",
    "extra_cfg.physics.att_speed",
    "extra_cfg.train.limits.adversary_v_max",
    "extra_cfg.train.limits.limiter_v_max",
    # λ — 원뿔 기하 slice
    "extra_cfg.viability.cone.half_angle",
    "extra_cfg.viability.cone.range_max",
)


def git_commit(short: bool = True) -> str:
    """현재 HEAD. 15 개 스크립트가 각자 굴리던 것의 단일 정의원.

    실패해도 예외를 던지지 않는다 — provenance 가 없다고 실험이 죽으면 안 되고,
    `"unknown"` 은 그 자체로 읽을 수 있는 신호다.
    """
    cmd = ["git", "rev-parse"] + (["--short"] if short else []) + ["HEAD"]
    try:
        out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        return out.stdout.strip() or "unknown"
    except Exception:                                      # pragma: no cover
        return "unknown"


def _prune(m: dict, paths=SCENARIO_VARYING) -> dict:
    """manifest 에서 선언된 leaf 경로들을 제거한 사본 (원본 불변).

    두 표기를 모두 받는다: `extra_cfg` 는 **점 찍힌 flat 키**를 쓰고
    (`{"physics.a_att_max": ...}`), 나머지 블록은 중첩 dict 다. 경로 문자열은
    `manifest_mismatch` 가 내는 형식과 같으므로 테스트 실패 메시지를 그대로 옮겨
    붙일 수 있다.
    """
    out = json.loads(json.dumps(m, sort_keys=True, default=str))
    out.pop("hash", None)
    for p in paths:
        node, rest = p.split(".", 1)
        cur = out.get(node)
        if not isinstance(cur, dict):
            continue
        if rest in cur:                      # flat dotted key (extra_cfg 관례)
            cur.pop(rest)
            continue
        *mid, leaf = rest.split(".")         # 중첩 dict
        for k in mid:
            cur = cur.get(k) if isinstance(cur, dict) else None
        if isinstance(cur, dict):
            cur.pop(leaf, None)
    return out


def world_hash(contract: dict, paths=SCENARIO_VARYING) -> str:
    """시나리오 실현값을 걷어낸 계약의 해시 — 캠페인 전체가 공유해야 하는 값."""
    return hashlib.sha256(
        json.dumps(_prune(contract, paths), sort_keys=True,
                   default=str).encode()).hexdigest()[:16]


def stamp(stack=None, **extra) -> dict:
    """결과 파일에 실을 provenance 블록.

        out = {"records": recs, **provenance.stamp(st)}

    `stack` 은 `build_m4_env` 의 반환값 (`M4Stack`). 없으면 코드 provenance 만 낸다
    (계약이 없는 해석 전용 산출물 — 판독기 등).
    """
    p = {"code_commit": git_commit(), "provenance_schema": 1}
    if stack is not None:
        c = stack.contract if hasattr(stack, "contract") else stack
        p.update(contract_hash=c["hash"], contract_schema=c["schema"],
                 world_hash=world_hash(c))
    p.update(extra)
    return p


def campaign_world_hash(stacks) -> str:
    """여러 stack 이 **같은 세계**인지 확인하고 그 world_hash 를 돌려준다.

    다르면 그 자리에서 터진다 — 서로 다른 세계의 결과가 한 파일에 섞이는 것이
    docs/81 이 막으려는 바로 그 사고다.
    """
    hs = {world_hash(s.contract if hasattr(s, "contract") else s) for s in stacks}
    if len(hs) != 1:
        raise AssertionError(f"world_hash 불일치 — 다른 세계가 섞였다: {sorted(hs)}")
    return hs.pop()
