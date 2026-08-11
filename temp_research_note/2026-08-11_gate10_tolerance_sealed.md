# 2026-08-11 — 게이트 10 iso-Π 판정 기준 선봉인 (docs/78 · r3.4, 런 0 회 상태)

## 판정

**iso-Π reduction validation 의 허용오차·paired 통계량이 봉인됨** — 어제 발견한
"게이트 10 tolerance 미봉인" 해소. iso-Π 런 0 회 · Phase III 셀 0 개 상태의 선언이므로
계약 정의 작업이다 (골대 이동 아님).

## 봉인 내용 (docs/78)

- **Tier 1 (완전 상사·버그 검출)**: 상사변환 2 종 (길이 ×2 / 시간 ×2), 상태별
  `|Δv_shot| ≤ 1e-6`, predicate 는 게이트 9 boundary 규칙 승계. CRN 은 무차원 형태로
  뽑아 스케일 (숨은 차원 상수 검출이 목적).
- **Tier 2 (reduction)**: conditioning 7 종 one-at-a-time 교란 (docs/73 판정 5 순서),
  검사점 chi {0.4, 0.8, 1.6} × kappa 0.5 × mu 0.4 × N 4 (전부 Z_master 값) × 20 ep
  CRN paired. 통계량 = informative (union) 상태의 `D_Q = |Q^base − Q^pert|`,
  Q ∈ {V_0, U_cheap, L1, LN}. **bar = 게이트 2·3 비준 bar 재사용: median ≤ 0.02 ·
  p95 ≤ 0.05** (실측 잡음 바닥의 3~10 배 — 과엄격 함정 없음). 공허 가드: informative
  < 50 이면 INCONCLUSIVE.
- **자기보정 공식 (δ = f(런타임 잡음)) 은 기각** — 잡음 크면 bar 풀리는 구멍.
  숫자 동결 + 유도만 논문 공식으로 제시.
- **실패 경로 사전 선언**: FAIL → collapse claim REJECT + 범인 group 을 scoped
  conditioning 한정으로 보고 (그 자체로 결과) → 축 승격 필요 시 Phase III-B.

## 배선

- `docs/78_gate10_isopi_prereg.md` 신규 → `pivot_manifest.PROTOCOL_FILES` 추가,
  REVISION r3.4 (LOCK_DATE 2026-08-11), manifest 생성:
  **protocol_hash `5126f7e325025b73`** → `artifacts/pivot_lock_2026-08-11.json`
- docs/74 §0.1 r3.4 행 · docs/77 §0 상태표 갱신. 계약 테스트 14/14 PASS.

## 감사 체인 완결 (같은 날 완료)

- 커밋 `1e1a3a9` + 태그 `PIVOT_LOCK_R34_2026-08-11` ✅
- **OSF 외부 timestamp ✅ — https://osf.io/39gxw/** (r3.3 + r3.4 manifest 업로드 +
  read-only registration, CC0). 지도 셀 0 개 · pilot 본실행 열람 전 시점 확보.
  이후 revision 은 새 파일로 추가 업로드 (덮어쓰기 금지).

## 남은 것 (사용자 트랙)

- 서버: coarse pilot 본실행 4 샤드 + MARL 9 런 결과 처리 → 통합 파일 수령 예정
- 조교 답신 발송 (mu 어순 · "임의로" 보정 2건 — 8/10 note)
- KSAS 초록 트랙에서 Grossmann 3편 정독 (tolerance 와 무관, 프레임용)
