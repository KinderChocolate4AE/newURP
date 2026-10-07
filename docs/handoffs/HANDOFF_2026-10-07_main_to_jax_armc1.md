# HANDOFF — main → JAX 세션: arm C-① 착수 지시 (2026-10-07)

사용자 ③ 게이트 사슬 결재 완료 (docs/126 §6) — arm C-① 착수. **계약 = `docs/127` (봉인,
먼저 정독).** 배경: `E3B2_NULL` (노트 10-07b) + P0a `AXIS3_NULL` / P0b AUC 0.887 (노트
10-07e). 질문 = "fire 채널을 판정기-증류로 지도학습하면 1~2 step 창을 맞추는가".

## 작업 (JAX 레인, worktree `newURP-jax` 전용 — canonical read-only)

1. **라벨링**: rollout 전 궤적 매 tick judge robust (worst≥1 ∧ ¬boxed) 라벨 (parity 판정기
   seal v2 `14b9d56f20b1cfb9` 경로). 라벨 = 기존 isotropic 계보 (P0 turn-limited 계보 사용
   금지). held-out 분할 = rollout 단위 (Q-C1a AUC 측정용).
2. **학습**: cell {m0.35_n1, m1.4_n1} × seed {0,1,2}, 이동 = r4′ (`--stack r4p`) + fire 채널
   증류 loss. 동시 vs 교대-동결 등 구현 선택 = 너의 재량 — 단 라벨 정의·예산 (phase 2 와
   동일 1.1e8)·주장 한계 불변. **C-② 로그 공짜 탑재**: per-limiter counterfactual (limiter
   i 제거 시 p_feasible/robust 변화) — 보상 아님, 로그만.
3. **judge exploiter**: 완성 방어 (동결) 상대 신규 학습 cell×seed 당 1 (phase 2 예산 동일).
   학습 곡선 (0.05→0.99 서명 여부) 보고.
4. **보고**: held-out AUC (Q-C1a) · train-side 관통률 · pin 커밋 hash. **pin 확정 보고 →
   main 이 manifest build + dry-run 후 정본 평가 발사** (server4, seed0 272000+cell_idx·1000
   — 학습·라벨링에 이 시드대 사용 금지).

## 함정 (기존 규율 그대로)

양성 주장 금지 (판정은 main 정본 평가만) · 격리본 불사용 · 대형 ckpt 는 teams-only strip
후 전송 (2.4G→78M 전례) · 전송 중단 시 원격 tar 잔존 프로세스 확인 (10-07 mv nested 사건)
· server5/6 `.venv-jax` · git 은 newURP-jax 에서만.
