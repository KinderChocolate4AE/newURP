# 128 — arm D: 이력 조건화 + 확률 정책 (동결 내성 / 창 생성 복원)

- **일자**: 2026-10-07 · **상태**: **봉인** (게이트 사슬 기승인 (docs/126 §6 3차 결재) 의
  조건부 단계 — 투입 조건 "arm C 후에도 감사 ~97%+ 관통" 충족 (`ARMC1_NULL`, 감사 6/6
  99%, 노트 10-07h). 기준 선언 = main; manifest = `scripts/fs1_armd_manifest.py` (평가 전
  build), pin dry-run 전제 유지)
- **결정 근거**: arm C-① 이 병목을 분리 — 감지 ✓ (AUC 5/6 ≥ 0.9), robust 발사→포획 전환
  ≈ 1:1, **창 생성 ✗** (전용 착취자가 동결 방어의 결정성을 읽고 robust 창 미진입; fired-ep
  2~16/240, m1.4 0). sto > det 전 slot (phase 2 + arm C-①) = 예측불가성 잔여 가치.

## 1. 사전 등록 질문·기준

- **Q-D**: 방어의 이력 조건화 (**프레임 스택 우선**, docs/126 §4) + 확률 정책 평가가
  공진화 착취자의 동결-결정성 착취를 꺾어 (i) 감사 서명을 완화하고 (ii) 창 생성을
  복원하는가.
- **판정 defender = learned_sto (사전 선언 — 판정-모델 변경 명시)**: 기전이 예측불가성
  이므로 결정화 (det) 판정은 기전 자체를 제거한다. det 는 보고로 유지. 이 승격은 본
  계약 한정 (이전 판정들과 pooling 금지; det↔sto 비교는 같은 run 안 보고만).
- **게이트 (3단)**:
  - **D-i 감사 완화**: 전용 exploiter (sto 방어 상대 1e7) 최종 관통률 ≤ **0.90**,
    seed 2/3, cell 별 → `AUDIT_SOFTENED(cell)`.
  - **D-ii 천장**: ceil_sto ≥ **29/240** (동일 문턱 가족), seed 2/3 → `ARMD_OPENS(cell)`.
  - 종합: D-ii 성립 cell 있으면 `ARMD_OPENS`, 없고 D-i 만 성립이면 `ARMD_AUDIT_ONLY`
    (기전 전진·천장 미달), 둘 다 없으면 `ARMD_NULL`. 무효 = budget/completion/paired/
    manifest 위반 cell 제외·보고.
- **보고**: fired-ep 수·robust-fire 전환율·창 발생률 (arm C-① 과 같은 문턱 가족 참조
  비교만) · exploiter 학습 곡선 (0.05→0.99 서명 형태) · det 전 지표.

## 2. 생산 (JAX 레인)

| 요소 | 내용 |
|---|---|
| 방어 | arm C-① 레시피 유지 (r4p + 증류 fire head, docs/127 라벨 불변) + **방어 obs 프레임 스택 k=4** (이력 조건화 1안; k 변경·GRU 등 대안은 JAX 레인 재량이되 선택 1개 고정·보고) |
| cell/seed/예산 | m0.35_n1 · m1.4_n1 × seed {0,1,2} × 1.1e8 (동일) |
| exploiter | **확률 (sto) 동결 방어 상대** 신규 학습 1e7, jseed 275000대 — 감사 곡선 로그 필수 |
| C-② 로그 | 유지 (창-근처 조건화 재분석 대비, 게이트 아님) |

## 3. 정본 평가 (server4 고정)

240판 paired, seed0 = **274000 + cell_idx×1000** (학습·라벨링 사용 금지), `--stack r4p
--groups none --traj 2`, defenders = learned_sto (판정) + learned_det (보고), exploiter =
전용 judge exploiter. 판독 = `scripts/fs1_armd_readout.py` (D-i/D-ii).

## 4. 규율·다음

결과 전 봉인 (본 문서) · pooling 금지 · 어휘 (창발 금지 — 이력 조건화는 설계 처방;
"cooperation" 금지) · 격리본 불사용 · JAX git 은 newURP-jax 만. **판독 후**: `ARMD_OPENS`
→ E7 계약 (ρ vs ceiling, 열린 cell anchor 포함) / `ARMD_AUDIT_ONLY`·`ARMD_NULL` → E7
직행 (창 생성의 남은 손잡이 = ①축 net 물리; docs/126 §4). E7 계약 준비는 arm D 학습과
병행 가능 (발사는 판독 후).
