# 130 — E7-c: ②축 (협력) 이 경계를 미는가 — 전이 구간 2×2 (ρ 아래/위 × limiter 무장/무력)

- **일자**: 2026-10-08 · **상태**: **초안 (미봉인)** — 사용자 scope 결재 대기. **E7-b 결과 전에
  봉인해야 함** (변형 선정·예측이 E7-b 결과에 오염되지 않도록). manifest = `fs1_e7_manifest.py`
  의 `build_e7c` (봉인 시 추가).
- **결정 근거**: E7-a′ (노트 10-08d) = scripted limiter 의 즉시 witness 폐쇄 몫 ≈ 0 (전 ρ,
  공격자 조건부 — limiter 회피를 학습한 공격자가 다수) + 궤적 조형 경로 미측정. 연구 정체성
  기여 ③ ("협력 조형이 경계를 미는가") 의 증거 = 현재 0. 남은 검정 = 학습 limiter + 조건별로
  재적응한 착취자. 동시에 K1 경계 ρ* (가정 A5 = limiter 없음) 의 **학습 수준 검정**이 같은
  설계에서 공짜로 나온다 (무력 조건 = A5 세계).

## 1. 설계 — 2×2 × seed 3

| | **무장 (armed)** = arm C-① 레시피 그대로 | **무력 (inert)** = limiter 판정·kinetic 효과 0 |
|---|---|---|
| **P1: t0.85_h1.0_cv** (ρ = 1.923/0.85² ≈ **2.66 < ρ\***) | 협력이 있어야만 열릴 수 있는 칸 | ρ* 아래 + 협력 없음 → 닫혀야 함 (P-ρ2) |
| **P2: t1.0_h1.5_cv** (ρ **2.94 > ρ\***) | 참조 | 콘 단독으로 열려야 함 (P-ρ2) |

- ρ* = 2.813 (P-ρ2 등록, V̄ 23.01). 두 점은 ρ* 를 사이에 두고 −5.4% / +4.6% — 전이 구간의 양쪽.
  P2 는 E7-a 에서 창 3.0 step (비승격) — 학습 하에서의 첫 측정. P1 은 미프로브 (τ 0.85 는
  E7-a 격자 밖 — 선정 근거는 해석적 ρ 위치뿐, 실측 오염 없음).
- **무력 (inert) 정의**: `FS1Spec(limiter_inert=True)` → `physics.kill_radius = 0` (config
  단일 소스 → scenario.limiter.kill_radius → 판정 witness 폐쇄 (viability 는 kill_radius ≤ 0
  이면 limiter 무시) 와 kinetic 접촉 처리 (env/env_sys 접촉 술어) 동시 0). limiter 는 계속
  움직이고 관측도 그대로 (네트워크 구조 불변). 공격자는 limiter 가 무해한 세계에 재적응한다
  → **즉시 폐쇄 + 위협에 의한 궤적 조형 두 경로를 함께 제거한 대조군.**
- 생산: 4 조건 × seed {0,1,2} = **12 run**, 조건별 BC 신규, arm C-① 레시피 (r4p + 증류 fire
  head), 1.1e8. **조건별 전용 judge exploiter** (그 조건의 동결 방어 상대, 1e7, jseed
  279000대). server4 GPU 1장 (서버 룰) — **E7-b 생산 종료 후** 직렬 (~12h).

## 2. 지표 — net 포획만 센다

무장 조건의 kinetic 무력화 (K_FIRST/HARD_KILL) 는 무력 조건에 존재할 수 없으므로, 두 조건
비교에 섞으면 협력 효과가 아니라 "kinetic effector 유무" 를 잰다. → **모든 E7-c 게이트는
NET 포획 수 (NET_CAPTURE + CAPTURE_WITH_CONTACT, learned_det vs 조건별 ex_judge, 240판)** 로
정의. 전체 defended 는 보고.

## 3. 사전 등록 예측·게이트 (기존 문턱 가족: 29/240, +24, seed 2/3)

- **P-ρ2L (ρ* 의 학습 수준 검정, 무력 조건 = A5 세계)**: NET(inert, P2) ≥ 29 **그리고**
  NET(inert, P1) < 29 (각 seed 2/3) → `P_RHO2L_SUPPORTED` (콘 단독 경계가 학습 방어 + 전용
  착취자 하에서도 ρ* 사이에서 갈림). 둘 다 열리거나 둘 다 닫히면 `NOT_SUPPORTED` 로 방향 보고.
- **P-②d (협력이 경계를 민다 = 기여 ③)**: P1 (ρ* 아래) 에서 NET(armed) ≥ 29 **그리고**
  NET(armed) − NET(inert) ≥ +24 (같은 seed 쌍, 2/3) → `COOP_PUSHES_BOUNDARY`. P1 무장도
  닫히면 `COOP_NULL_BELOW` (학습 limiter 로도 경계 아래를 못 엶). P2 의 armed−inert 차이는
  보고 (고-ρ 에서 협력 무관/boxed 손해 방향 — E7-a′ H↑ 의 학습판).
- **기전 귀속 (보고, 126 보조 주장 1)**: 무장 조건의 `--coop-window` 창 tick 협력 몫 C·H
  (최소 신호 하한 1% — 미만이면 즉시 폐쇄 경로 `LOW_SIGNAL`). NET(armed) − NET(inert) 차이
  중 C 로 설명되지 않는 부분 = 궤적 조형 경로 후보 (정량 분해는 주장하지 않고 범위로 보고).
- 무효: budget/completion/paired/manifest/BC-계보 위반 run 제외·보고.

## 4. 정본 평가

server4 CPU, 240판 paired, 조건 시드 = **278000 + cond_idx×1000** (학습·라벨링 사용 금지),
`--tau-scale/--theta-scale/--aim` 변형 + `--limiter-inert` (구현 예정) + `--coop-window`,
defenders = learned_det (판정) + learned_sto (보고), 조건별 ex_judge.

## 5. 구현 전제 (봉인 후·생산 전)

- `FS1Spec.limiter_inert` (canonical 선행, JAX 미러): 기본 False = bit-exact. 테스트: (a) 기본
  no-op, (b) inert 에서 판정이 limiter 제거 판정과 동일, (c) inert 에서 kinetic 접촉 무력화가
  발생하지 않음. eval CLI `--limiter-inert`.
- JAX parity: 기준 golden 불변 + inert 1조건 f64 spot-check.

## 6. 해석 범위·어휘

- 두 점 × seed 3 은 경계 근처의 **국소 검정**이지 ρ 전역 협력 프로파일이 아님.
- 양성은 "1e7 착취자 조건부". "cooperation" 금지 → limiter-control opportunity. 창발 주장 금지
  (증류 머리 레시피).
- not_evidence_for: 세계 천장, 실물 대표성, E7-a/b·arm C-①/D 와의 pooling (같은 문턱 가족
  참조 비교만).

## 7. 결재 요청 (사용자)

① 2×2 × 3 seed = 12 run scope ② P1 = τ 0.85× (ρ 2.66) / P2 = θ 1.5× (ρ 2.94) 선정
③ 무력 정의 (kill_radius = 0) ④ NET-only 게이트. 승인 시 E7-b 결과 전 봉인.
