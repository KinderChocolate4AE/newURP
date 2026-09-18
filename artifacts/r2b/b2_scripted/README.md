# artifacts/r2b/b2_scripted

- `manifest.json` — B2 봉인 manifest (docs/102). 실행기·판독기의 유일한 격자 정의원.
  - **계보 정정 (2026-09-18, manifest 무수정):** 기록된 `code_commit: ac7cf2a` 는
    **dirty tree 의 HEAD** 였다 (B2 스크립트 untracked + mission_rollout 미커밋).
    설계 필드는 현행 코드 재생성과 bit-identical 확인 (차이 = code_commit ·
    그것을 포함해 계산되는 manifest_hash 뿐). 정본 실행 snapshot 과 검증 절차는
    `temp_research_note/2026-09-18b_b2_lineage_fixed_*.md` 참조. manifest 는
    재생성하지 않는다 — 이 기록이 정정이다.
- **판독 전 필수:** `python -m shepherd.scripts.b2_check` PASS (shard 완주 ·
  code_commit/code_dirty/world_hash 균일 · scenario 커버리지 · arm pairing).
  실행기는 dirty tree 에서 `--run` 을 거부한다 (2026-09-18 guard).
- `primary/` — 정본 실행 산출물 (`b2_run --run`). **아직 없음 = 미실행.**
- `forced_fire/` — 별도 계정 진단 (`b2_forced_fire --run`). primary 이후에만.
- `smoke_primary/` — **배선 시험용 fixture** (60 ep, 경계밴드 5 cell). 정본 아님.
  각 shard 에 `fixture` 키가 박혀 있다. 과학 판독에 쓰지 말 것.
- `readout.json` / `forced_fire_readout.json` — 판독기 산출 (정본 dir 를 읽었을 때만).

구현 기록: `temp_research_note/2026-09-14c_b2_implementation_note.md`
