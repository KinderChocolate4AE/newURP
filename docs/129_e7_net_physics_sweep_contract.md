# 129 — E7: ①축 net 물리 sweep (ρ vs ceiling 머니 커브)

- **일자**: 2026-10-08 · **상태**: **E7-a 봉인·판독 완료 (`P_RHO1_SUPPORTED`, 노트 10-08b)
  + E7-b addendum 봉인 (§6, 2026-10-08 — 학습 전; 사용자 scope 결재 + P-ρ2 등록 10-08c
  반영)**. manifest = `scripts/fs1_e7_manifest.py` (E7-a `build_e7a` v1.1 + E7-b `build_e7b`;
  pin dry-run 전제 유지).
- **결정 근거**: 행동 측 처방 전부 소진 — E3 (`BAND_EMPTY`) · E3b p1 (`FLOOR`) · p2
  (`E3B2_NULL`) · arm C-① (`ARMC1_NULL` — 감지 ✓·robust발사→포획 ≈1:1·창 생성 ✗) · arm D
  (`ARMD_NULL` — 발사 빈도 복원·타이밍 ✗). 창 생성의 남은 손잡이 = 세계 (net 물리) 자체.
  판정 수치 = 보장-포획 하한 의미론 유지 (정직성 자산).

## 1. 사전 등록 (E7-a 와 함께 봉인)

- **ρ 정의 (A.1 그대로)**: ρ(변형) = (net 도달점 콘 단면 반경) / (회피 종점 구 반경
  ½·a_att·τ_deploy²). 현행 ≈ 1.5/0.92 ≈ 1.6. 변형별 ρ 는 **해석적으로 선계산해 manifest
  에 기록** (프로브 결과 전).
- **예측 P-ρ1 (기능형)**: 창 크기 (1.5a 프로토콜의 ep 당 robust step 중앙값) 는 격자에서
  **ρ 단조 증가** — 역전 cell 발견 시 ρ 단독 지배 기각.
- **예측 P-ρ2 (경계형)**: E6/K1 손증명 (사용자 레인, ≤10/31) 이 유도하는 ρ 경계와 E7-a
  창 지도의 등고선이 겹친다 — K1 경계값은 **E7-b 학습 착수 전** 등록 (늦으면 E7-b 가
  경계 미등록 상태로 진행됨을 명시 보고).
- **양성 주장 조건부 선언**: E7 의 어떤 열림도 "본 예산 (1e7) 전용 착취자 조건부" 로만
  표기 — 세계 천장 아님.

## 2. E7-a — 프로브 격자 (학습 없음, 1.5a 프로토콜 재사용)

| 요소 | 내용 |
|---|---|
| cell | **m0.35_n1 고정** (E3 에서 μν 평면 평탄 — ①축 분리) |
| 손잡이 격자 | **τ_deploy {1.0×, 0.7×, 0.5×} × θ_cone {1.0×, 1.5×} × 조준 {cv (현행 등속 외삽), ma (기동-인지 1단)}** = **12 변형** (정정 2026-10-08: 초판 "18" 은 3×2×2 산술 오기. 기준 변형 1.0×/1.0×/cv 포함 — 1.5a 재현 anchor). range·③축 (P0a 권고)·FRPN 종말유도 = 불포함 (후방 명시) |
| 조준 ma 정의 | net_center = p_att + v_att·τ + **회피 기대 보정** (구현 = main, viability 기구 재사용; 선언: 보정은 witness 구 중심 이동 없이 조준점만 — 판정 의미론 불변) |
| 프로브 | 변형당 1.5a 점유율 (SEED0 268000, 4 적응 공격자 × 24 ep, 발사 금지) — 창 중앙값·max run·margin (P0 과 동일 지표). server4 CPU |
| 산출 | **ρ vs 창 중앙값 지도** (머니 커브 1차 버전) + P-ρ1 단조성 판정 |
| E7-b 진입 기준 (선언) | 창 중앙값 ≥ **4 step** (P0a 와 동일 문턱 가족) 인 변형만 학습 후보로 승격. 0개면 격자 확장 재상신 (학습 없이) |

- 공정성 주의: 프로브의 공격자는 **구세계에서 학습된** 적응 공격자 (신세계 비공진화) —
  E7-a 창 지도는 낙관 편향 가능. 따라서 E7-a 는 **후보 선별용**이고, 양성 판정은 E7-b
  (신세계 전용 착취자 감사) 만. manifest 에 명기.

## 3. E7-b — 학습·감사 (형식만; 수치는 addendum)

- 승격 변형 × seed 3: 방어 = **arm C-① 레시피** (증류 fire head — "창이 생기면 맞춘다"
  ≈1:1 전환이 증명된 머리; 창 생성을 세계가 주는지가 질문이므로) · 신세계 재학습 + 신세계
  전용 judge exploiter (감사 필수). arm D 스택은 불포함 (ARMD_NULL — 재도입은 별도 심사).
- 게이트 형식: ceil ≥ (해당 변형 문턱; addendum 에서 ceil_ref 재측정 후 +24 가족) seed 2/3
  → `E7_OPENS(variant)` → **ρ vs ceiling_s 실측 커브 + E6/K1 경계 겹쳐 그리기 = Fig (머니)**.
- 보고: m0.35_s2 단서 추적 — NET 점유율 vs 감사 관통률 상관을 변형 전반에서 로그 (보고
  전용).

## 4. 규율

결과 전 봉인 (E7-a 본 문서 + manifest / E7-b addendum) · 판정 평가 = server4 · 신세계
변형별 계보 분리 (구세계 수치와 pooling 금지; 기준 변형 anchor 비교만) · 어휘 (세계 천장
금지·"이 예산 착취자 조건부" 필수 병기) · 격리본 불사용 · JAX git 은 newURP-jax 만.

## 5. 레인 분담 (v0 — E7-a 시점; 현황은 §6 이후 노트 참조)

- main: ma 조준 구현 + 프로브 스크립트 (P0/1.5a 재사용) + manifest + 판독.
- JAX: ρ 손잡이 플러밍 사전 설계 (완료 — newURP-jax `103165d`).
- 사용자: K1 손증명 (완료 — P-ρ2 등록 10-08c, ρ* 2.813).

## 6. E7-b addendum (봉인 2026-10-08 — E7-a 판독 후·학습 전; 사용자 scope 결재 반영)

- **승격·승인 변형 5** (E7-a `P_RHO1_SUPPORTED`, 노트 10-08b; 사용자 결재 = cv 사다리
  4점 + ma 대조 1점): **t0.7_h1.0_cv (ρ 3.93) · t0.7_h1.5_cv (6.00) · t0.5_h1.0_cv (7.69)
  · t0.5_h1.5_cv (11.77) + t0.5_h1.0_ma (7.69)** × seed {0,1,2} = 15 run. cell = m0.35_n1.
- **생산**: 변형 세계 재학습 — arm C-① 레시피 (r4p + 증류 fire head, docs/127 라벨 불변;
  arm D 스택 불포함). **변형별 BC 신규 생성** (구세계 BC 재사용 금지 — JAX 메모 ⑤).
  예산 1.1e8 + 신세계 전용 judge exploiter 1e7 (jseed 277000대, 감사 곡선 로그).
- **세계 변형 구현 전제 (canonical 선행, JAX 미러)**: ① τ = **`physics.tau_deploy` config
  단일 소스 override** (0.30·scale → scenario 경유 env.tau_deploy 와 FSM dep 타이머 동시
  전파 — JAX risk① 구조적 해소) ② θ = judge cone_half_angle·scale ③ ma = 조준점 식
  (nc += ½·â·τ², â = 속도 유한차분 a_att_max clip) 을 터렛 추적 (env_sys) + net_center
  (env) 2개 지점에 동일 적용. **기본값 (1.0/1.0/cv) = 현행 bit-exact 테스트 필수** +
  JAX parity (기준 변형 golden + 비기본 1변형 f64 spot-check).
- **정본 평가** (server4): 240판 paired, 변형 시드 = **276000 + variant_idx×1000** (학습
  사용 금지), defenders = **learned_det (판정)** + learned_sto (보고) + fin12_fb·kfirst50
  (**scripted 전이 참조** — 같은 judge exploiter 상대 paired; exploiter 는 학습 방어
  상대로 훈련됐으므로 참조 전용 라벨, 게이트 아님).
- **게이트**: 변형별 **ceil_det ≥ 29/240** (ceil_ref 5 + 24 — 기존 문턱 가족. 정직 플래그:
  신세계 ceil_ref 재측정 생략, scripted 전이 참조로 보완 보고), seed 2/3 →
  `E7_OPENS(variant)`; 전무 → `E7B_NULL`. 무효 = budget/completion/paired/manifest/BC-계보
  위반 변형 제외·보고.
- **사전 등록 P-ρ3 (머니 커브 본체)**: cv 사다리 4점의 seed-중앙 ceil_det 가 ρ 단조 —
  Spearman ≥ 0.7 → `P_RHO3_SUPPORTED`. ma 1점은 cv 동일 ρ (t0.5_h1.0) 와 쌍대 비교 보고.
- **P-ρ2 overlay (등록 10-08c 인용, 판독 시 수행)**: ρ* = **2.813** (V̄ 23.01, 4dt) /
  2.427 (3.5dt 하한). E7-a rows.npz 에서 **shell-통과 encounter 조건부 창 중앙값** 재계산
  (등록 모집단 정합) 후 머니 커브에 ρ* 선 + N = N∞(1 − ρ₀/ρ) 형상 (ρ₀ 1.238 연속 개방,
  1/ρ 선형) 겹쳐 그리기. 등록값 변경 불가.
- 보고 추가: 변형 전반 NET 점유율 vs 감사 관통률 상관 (m0.35_s2 단서 추적) · C-② 로그
  유지 · fired-ep/robust 전환율 (arm C-①/D 와 같은 문턱 가족 참조만).

