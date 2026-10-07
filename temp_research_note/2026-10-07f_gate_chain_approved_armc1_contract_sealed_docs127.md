# 2026-10-07f — ③ 게이트 사슬 결재 (3차) · arm C-① 계약 봉인 (docs/127) · JAX 지시 발행

- 사용자 3차 결재: **③ 게이트 사슬 승인 + arm C-① 착수 지시**. docs/126 §6 갱신 (①②③ 전부
  승인·처리 완료 상태로 종결).
- **docs/127 봉인** (기준 선언 = main, docs/126 §4 위임): Q-C1a capability 기준 = held-out
  AUC ≥ 0.9 (`C1_DISTILL_OK`, 주장 상한 = "증류로 창 감지 가능") · Q-C1b 정본 기준 =
  ceil_det ≥ 29/240 (E3b p2 동일 문턱 가족), seed 2/3, cell 별 (`ARMC1_OPENS`/`ARMC1_NULL`)
  · 평가 시드대 272000 (학습 사용 금지) · C-② = 로그 전용 · oracle-gated 상한 defender =
  보고 전용 · 발사 tick 명중률 보고 추가.
- JAX 세션 지시문 = `docs/handoffs/HANDOFF_2026-10-07_main_to_jax_armc1.md`. pin 확정 보고
  후 main 이 `scripts/fs1_armc1_manifest.py` build + dry-run → 정본 평가 발사 (server4).
- 다음 trigger: JAX pin 보고 → manifest/평가 → 판독 → `ARMC1_OPENS` 시 E7 계약 직행 /
  `ARMC1_NULL` ∨ 감사 97%+ 지속 시 arm D 심사.
