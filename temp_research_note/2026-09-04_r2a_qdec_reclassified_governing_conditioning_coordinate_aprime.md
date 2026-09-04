# 2026-09-04 — R2a: dt/τ 는 수치 검증수가 아니라 경계를 지배하는 결정-cadence 좌표였다 (q_dec 승격, A′ 재봉인)

> 기록 지시일 = 260904 (사용자). 작업 세션 = 2026-09-05 (Stage 0 → 봉인 → Stage 1 게이트 → 본 발견까지 동일 세션). 정본 산출물 = `artifacts/r2a/` seal 체인.

## 발견 (pre-confirmatory sensitivity diagnostic — 결과 열람 전 포착)

Stage 1 본 run 직전의 dt/2 진단 (R-ref, 경계 2셀, n=50 paired CRN) 에서:

- 라벨 불일치 27/50 · 30/50, dt/2 에서 두 셀 모두 p → 1.000.
- 기전 (probe 로 분류): 적분기 발산 아님 — 같은 dt/τ 에서 Tier A pathwise 가 8e-15 로 정확. 원인은 **clean 판정 → 발사 명령의 1 control-step 지연**. coarse cadence 는 지연(≤ dt)이 경계 근방의 짧은 clean 창 끝을 넘겨 wasted fire 를 만들고, fine cadence 는 같은 물리 시각의 사격이 창 안에 든다 (fire_step 14@dt wasted vs 26@dt/2 captured, 발사 시각 ≈ 동일).
- 경계는 소멸이 아니라 이동: dt/2 에서 χ50 ≈ 0.55 → ≈ 0.70 (χ≥0.85 는 p=0/36). **Δχ50 ≈ +0.15 > 3·δχ** — 사소한 수치 해상도가 아니라 governing 좌표.

## 판정 (사용자, A′) — "물리 conditioning π" 로 단정하지 않는다

현 구현에서 dt 는 적분 step ∧ 상태 갱신 ∧ clean 판정 ∧ 발사 적용 cadence 를 겸하므로, 이번 실험만으로는 "순수 발사지연 물리" 와 "고정 cadence 에서의 수치 이산화" 를 분리하지 못한다. 따라서:

**q_dec ≡ T_decision/τ (현 구현 T_decision = dt), q_dec = 1/6** — *normalized decision/update cadence* 로 명명하고 **registered governing conditioning coordinate** 로 승격. "dt/τ = 수치 검증수" 지위는 철회.

R2a 의 질문은 그대로 성립한다: Stage 0 도, 5개 구현 전부도 q_dec = 1/6 (pathwise 로 실증). 내부 타당성 무사 — 단 **외적/물리적 scope 가 한 단계 좁아졌다**: 이 캠페인의 경계는 "특정 폐루프 decision cadence 를 가진 시스템의 경계" 이지 continuous-time universal boundary 가 아니다. 실제 요격 시스템에도 sensing/decision/actuation cadence 가 있으므로 연구 대상으로 정당.

## 반영 (전부 커밋됨)

1. dt_τ "수치 검증수" 지위 철회, q_dec 승격 (ledger `_pins` 키 교체 + Q_DEC 선언 블록).
2. seal 체인 supersede (구 hash 는 supersedes_v3 로 lineage 보존):

| 대상 | A′ hash | 직전 (v3) |
|---|---|---|
| Stage 0 | `9d134d5c1a11c1ba` | `4c26cf1a2a4d9ab8` |
| R2a-L | `a253505b1280804e` | `da36d96eb5bceddc` |
| R2a-P | `05f3e5c18d147b9f` | `3aa3adef77420d12` |
| protocol | `1496a4769876b438` | `93c201cfba2785d2` |

3. runner 의 dt_check PASS gate 삭제 → **전 구현·전 에피소드 q_dec = 1/6 runtime assert** 로 교체.
4. 결론 어휘·C046: "… conditional on the sealed A2-reactive evasion vector **and normalized decision cadence q_dec = 1/6**".
5. dt/2 결과는 gate 실패가 아니라 **pre-confirmatory sensitivity diagnostic** 으로 공개 (`stage1_dt_check.json` + `stage1_dt_review.json`).
6. 게이트 수치 전부 불변 (a_min 6 · τ_B 0.45 · H +0.057 · pathwise 8e-15 · atol 1e-6 · cells 6). 테스트 24/24.

## 후속 아이디어 (기전 — R2a 에서 claim 하지 않음, B-트랙)

- **phase-alignment 가설**: 유효 지연은 상수 dt 가 아니라 clean 성립 시각 t_c 의 양자화 지연 δ_dec = ⌈t_c/T_dec⌉·T_dec − t_c ∈ [0, T_dec). 경계 근방에서 clean 창 폭이 T_dec 와 같은 order 가 되면서 q_dec 가 경계를 크게 움직인다. → 창 폭 분포·δ_dec 분포를 직접 재면 좋은 후속 결과.
- **decision-decoupled probe** (reviewer 대응용, Stage 1 blocker 아님): decision cadence 0.05 s 고정 + 적분만 substep 0.025 s. 결과가 coarse 적분과 같으면 "dt/2 차이는 적분이 아니라 decision cadence 발" 의 강한 증거.

## 상태

kill screen (scenario 샤딩 8개, 전역 HARD_KILL sentinel, q_dec assert) 실행 준비 완료. 선행 = repo-R1 provenance pass + H-4 랩서버 (사용자). Stage 1 은 결과를 그대로 받아보는 단계 — 설계 동결.
