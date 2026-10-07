# HANDOFF — main → JAX 세션: arm D 착수 지시 (2026-10-07)

arm C-① 정본 = **`ARMC1_NULL`** (노트 10-07h) — 단 기전 분해 성공: 감지 ✓·전환 ≈1:1·
**창 생성 ✗** (착취자가 동결 결정성을 읽음). 감사 99% 지속 → arm D 투입 조건 성립.
**계약 = `docs/128` (봉인, 정독 후 착수).**

## 작업 (worktree `newURP-jax` 전용)

1. **방어 생산**: arm C-① 레시피 (r4p + 증류 fire head, 라벨 불변) + **방어 obs 프레임
   스택 k=4**. 대안 구현 (k≠4, GRU 등) 을 쓰려면 1개 고정하고 보고 (사후 변경 금지).
   cell {m0.35_n1, m1.4_n1} × seed {0,1,2} × 1.1e8.
2. **exploiter**: **확률 (sto) 동결 방어 상대** 1e7, jseed 275000대. **감사 학습 곡선
   로그 필수** (D-i 게이트 = 최종 관통률 ≤ 0.90; 0.05→0.99 서명 형태 보고).
3. C-② 로그 유지 (게이트 아님).
4. **보고**: pin 커밋 + 산출 경로 + train-side wr/NET 점유 + 감사 곡선 요지 → main 이
   manifest build/dry-run → strip·전송 → server4 정본 평가 (seed0 274000대 — 학습 사용
   금지).

## 함정 (불변)

양성 주장 금지 (판정 = main) · 격리본 불사용 · 대형 ckpt strip (이번엔 pools/pool_snaps
마지막 1개 truncate 까지 — armc1 전례 1.3G→70M) · 전송 후 개수 검증 · git 은 newURP-jax 만.
