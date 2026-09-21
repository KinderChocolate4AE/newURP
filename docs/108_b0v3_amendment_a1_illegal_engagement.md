# 108 — B0 v3 amendment A1: illegal engagement 정의 정정 (2026-09-22)

- **지위**: 정의–문서 일치 정정 (docs/88↔87 관례의 별도 amendment 문서).
  **구현 0 변경 · 결과 0 변경 · 봉인 hash 무변경** — B0 v3 기계 정본
  (`artifacts/b0/b0_v3_world_contract.json`, `b0_hash 5e7b5b486b9d8a4a`)은
  재개봉하지 않는다. 이것은 v4 사유(조항·격자·판정 규칙 변경)가 아니라,
  봉인 문안이 **실효 판정자를 누락 기술**한 것의 등재다.
- **근거 (결과 이전의 기록)**: [docs/103 §4.1 / §11.3 U-11](103_simulator_world_manual.md)
  — B2 primary 실행·판독 **전에 작성된** 계약 이탈 플래그: 계약 문안의 접촉
  술어는 이동 전 point-contact (`‖p_att − p_lim‖ ≤ kill_radius`)만 적었으나,
  실효 판정자는 swept 선분 resolver (`_seg_min_dist(pre, post) ≤ r_contact`)이며,
  이 이탈이 docs/94 · docs/102 에 amendment 로 미등재 상태였다.
  정직 한계: docs/103 은 당시 **미추적 파일**이라 커밋 시각 증빙이 없다 —
  본 정정과 함께 최초 커밋하여 이후의 lineage 를 고정한다. 문서 내부 기준
  시점(2026-09-14 r2)과 U-11 의 실측(60+100 ep, B2 이전 표본)이 선행성의 근거다.

## A1 정정 문안

`H_illegal` (illegal engagement) 의 사건 정의:

> **PRE/PENDING 중 point-contact 또는 enabled swept contact resolver가
> kinetic engagement opportunity를 검출한 사건.**

- `partition_bin` (mission_rollout)의 3-소스 판정(계약 술어 + env resolver
  engagement event + hard_kill 안전망)은 이 정의의 구현이며, B2 primary 는
  처음부터 이 정의로 측정됐다 — **결과 소급 재해석이 아니라 문안을 실효
  판정자에 맞춘 것**이다.
- 재현성: paired 재생 감사 (`9968bfd`·`fbe3f65`, 로컬 2/3 → **서버 3/3 PASS**,
  `artifacts/r2b/b2_scripted/viz/`)가 swept 검출의 결정론적 재현을 확인.

## 어휘 규율

- "불법 **충돌**" 표기 금지 — 사건은 거리 표본 충돌이 아니라 swept 궤적 검사의
  **비인가 kinetic engagement** 다.
- B2 결과 표준 서술: "협력 규칙(c5 arc)은 포획 성능을 높이지 못하면서
  (Δp_N +0.0020, paired 95% CI ≈ [−0.0012, +0.0053]) **비인가 kinetic
  engagement 를 5.63% 발생**시킨다 (SOLO 구조적 0%)."

## 영향 범위

- B2 readout (`638db52`) 수치 무변경. docs/102 봉인(arm/cell/CRN/metrics/readout)
  무변경 — 94·102 머리에 본 문서 포인터만 추가 (94 의 "사후 편집은
  오탈자·상호참조 수준" 허용 범위).
- W5 연동: docs/107 봉인의 선행조건이던 **정의 정정(본 문서) + 서버 재생
  3/3** 이 이로써 충족. 판정 자체는 docs/107 에서.
