# B2 계보 정정 — snapshot 1ceba52 확정, dirty-guard·완료 점검기 추가 (2026-09-18)

**판정: B2 primary 는 이제 재현 가능한 snapshot 에서만 돈다. manifest 는 무수정.**

## 무엇이 문제였나

- `artifacts/r2b/b2_scripted/manifest.json` 의 `code_commit: ac7cf2a` 는 **dirty
  tree 의 HEAD** 였다: B2 스크립트 4종(`b2_manifest/run/readout/forced_fire.py`)과
  `tests/test_b2_contract.py` 가 untracked, `mission_rollout.py` 의 B2 배선
  (partition_bin · kinetic_fallback)이 미커밋. 즉 `ac7cf2a` 를 checkout 해도 그
  실행은 재현되지 않았다. smoke shard 의 `code_commit: ac7cf2a` 도 같은 상태.
- 실행기는 커밋 번호를 기록만 하고 dirty 를 막지 않았다.
- 판독기는 manifest hash 만 대조 — shard 완주·코드 균일성 점검이 없었다.

## 정정 내용 (설계값 0 변경)

1. **설계 불변 검증**: `b2_manifest.build()` 를 scratchpad 로 재생성해 봉인본과
   전 필드 대조 → **설계 필드 bit-identical, diff = `code_commit`(ac7cf2a→37b75be
   당시 HEAD)와 그것을 hash 입력에 포함해 재계산되는 `manifest_hash` 뿐.**
   봉인 manifest (`2f887776be47f538`)는 재생성하지 않았다 — README 에 정정 병기.
2. **snapshot 커밋 `1ceba52`**: B2 실행 코드 전부 + mission_rollout 배선 +
   계약 테스트 + 봉인 manifest/README 를 최초 커밋. 이것이 B2 실행 코드의 정본.
   후속 `d2ab3f3`(Track B mode-switch) · `a3bbb7d`(잔류 미추적분)로
   shepherd/·tests/ **clean 상태 도달** (`git_dirty() == []`).
3. **dirty guard**: `provenance.git_dirty()` 신설 (fail-closed — git 실패 = dirty).
   `b2_run --run` · `b2_forced_fire --run` 이 dirty tree 에서 거부 (실증: 거부
   메시지로 잔류 미추적분이 드러나 3 커밋으로 정리됨). shard blob 에
   `code_dirty` 스탬프 추가.
4. **완료 점검기 `b2_check.py`** (판독 전 필수, 읽기 전용): shard 집합/.done/
   finished · code_commit 균일(+`--expect-commit`) · code_dirty=False ·
   world_hash 단일 · scenario 커버리지 [0, 50400) 정확 · arm pairing
   (ARM_ORDER 쌍·CRN·manifest unit 일치) · 총 레코드 100,800.
   smoke_primary fixture 에 돌려 FAIL 5축 검출 확인 (음성 대조).

## 검증

- `tests/test_b2_contract.py` **16 passed** (+ B0 v3 계약 12 = 사용자 확인 28).
- 정본 실행 절차 (다음 사건): clean HEAD 에서 `b2_run --smoke` +
  `b2_forced_fire --smoke` 재통과 (GO smoke, docs/102 §7) → W4 서버 primary
  (`--run --shard K --n-shards N`) → `b2_check [--expect-commit <run HEAD>]`
  PASS → `b2_readout` → W5 stop rule (별도 봉인 규칙).

## 원칙 확인

- manifest 조용한 재생성 금지 — 지킴 (README 정정 기록 방식).
- docs/102 봉인(arm/cell/CRN/forced-fire/metrics/readout) 무변경. b2_check 는
  측정·판정을 하지 않는다 (stop rule 아님).
