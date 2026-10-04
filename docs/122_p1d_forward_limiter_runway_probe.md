# 122 — P1d 전진 교전 limiter 활주로 probe (P1c 설계 결함 보완)

- **일자**: 2026-10-04 · **상위**: docs/121 (P1c) · docs/117 수순 · daily 2026-10-04b §5 합의 순서
- **상태**: **보류 (미봉인)** — 2026-10-04 사용자 결정으로 FS1 (docs/123) 동시학습 우선. manifest 초안 `artifacts/p1d_runway/manifest.json` 은 실행하지 않음. fwd 규칙 (`arc_geometry`) 은 scripted 기준선으로만 유지

## 1. 왜 다시 재는가

P1c (`STANDOFF_DOES_NOT_OPEN`) 의 개입 arm c5 는 **자산 중심 r_d = 9 m 호 위
bearing-only 골키퍼**라 늘어난 접근거리를 구조적으로 쓸 수 없었다 (P1c 노트
`fdffae7`). 따라서 "P2_NULL·b5 null 의 원인은 짧은 조형 활주로" 가설은 **미시험**.
P1d 는 같은 세계 변형에서 **활주로를 쓸 수 있는** scripted limiter 로 그 가설을 잰다.

## 2. 설계

- **세계**: P1c 와 동일 (k∈{1,2,4}, `adversary_start_x`·`episode_len` 만 ×k, layout
  고정). `_build_scaled` 재사용. B0 v3·P1c 와 pooling 금지.
- **arms**: hold / c5 / **fwd**. fwd = c5 kw + `rho = 0.5`:
  slot 반경 = `max(r_d, rho·R_h)` (R_h = 공격자–자산 수평거리). 즉 **자산–공격자
  중점에 screen** 을 치고, R_h ≤ 18 m 부터는 c5 와 bit-identical. slot 각간격은
  `dphi·r_d/r` 로 줄여 **slot 간 호 길이를 c5 와 같게** 유지한다 (≈ 4.7 m — c5 대형을
  그대로 전진). 봉인 전 smoke 궤적에서 각간격 고정판은 r≈40 m 에서 대형이 ±28 m 로
  벌어져 screen 이 아니게 됨을 확인하고 수정 (`arc_geometry`). 그러므로
  **D = fwd − c5 는 전진 단계의 효과만 분리**한다 (종말 단계 동일).
- **rho = 0.5 근거**: 중점 = 자유도 없는 기하학적 대칭점. 결과로 튜닝하지 않는다.
  sweep 은 하지 않는다 (단일축 규율). 운동학 확인: 공격자 ≈ 22 m/s, limiter
  a_max ≈ 7 m/s² → k=4 에서 limiter 가 ≈ 2 s 후 R≈24 m 부근에서 screen 형성
  (손계산), k=1 에서는 사실상 c5.
- **공격자**: P1c 와 동일 {route 0.5, 0.8} × sense ∞.
- **seed**: namespace `p1d_runway_v1`, seed0 = **251000** (사다리 다음 칸).
- **예산**: 3 k × 3 arm × 2 공격자 × 280 = 5,040 ep (scripted, 서버 2-shard).

## 3. 사전 등록 판정

- **INVALID**: lineage · completion · budget · paired draws · power (hold step
  k1→k4 증가) · **mechanism: fwd 의 k=4 평균 excursion ≥ 18 m (= 2·r_d)**.
  excursion = episode 별 max_t(limiter 평균 수평 반경). **P1b·P1c 교훈 — 개입 arm 이
  조작 변수를 실제로 쓰는지 fail-closed 로 검사.**
- **분류** (두 공격자 pooled, 560 ep/arm/scale): D(k) = N_fwd − N_c5.
  - D(4) − D(1) ≥ +28 (+5%p) 이고 H_illegal(fwd,4) − H_illegal(c5,4) < +28 →
    `RUNWAY_OPENS_SHAPING`
  - D(4) − D(1) ≥ +28 이나 위 H_illegal 차 ≥ +28 → `RUNWAY_GAIN_UNSAFE`
  - 그 외 → `RUNWAY_DOES_NOT_OPEN` (시험 규칙·rho·범위·스케일링 모형 한정)
- 보고 전용: fwd − hold, D(2), 공격자별, excursion, step.

## 4. 처분

- OPENS → B0 v4 (진입 게이트 세계) 결재 재개 + limiter 학습 질문을 **새 계약으로**
  재개 (자동 재개 아님). 합의 순서 ④ (limiter 학습) 의 진입 근거.
- DOES_NOT_OPEN → 이 규칙군에 대한 짧은 활주로 설명 기각. limiter 질문은 docs/104
  §3 세계의 G0 카드로 이관, Track B F1-E D2 전면.
- 봉인 전 smoke 는 **mechanism (excursion·궤적) 만** 확인 — 결과 bin 은 출력하지 않는다.
