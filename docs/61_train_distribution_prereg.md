# 61 — THREAT_V3_TRAIN 분포 사전등록 r1 (리뷰 5 반영 · Hyunjun 비준 대기)

**2026-08-07 · 학습 결과를 보기 전에 쓴다. docs/60 §1 의 TRAIN/IID/OOD 층을
동결하는 문서다. r0 = 초안 · r1 = 리뷰 5 (docs/62) 동결 전 수정 3개 반영.
지위 = 비준 대기 — 비준 후 확정, 학습 개시 후 불변경.**

★ **명칭 (r1)**: 이 분포는 실제 위협 빈도 추정이 아니라 **balanced
experimental design distribution** 이다 — 각 위협 regime 을 동일하게
시험·학습하기 위한 설계분포. "최소 가정" 이라 부르지 않는다 (9셀 균등도
가정이다). 셀별 성능이 전부 공개되므로 (§6) 가중 재해석은 독자의 몫.

★ **nominal 관계 (r1)**: 범위는 nominal (0.5/30) 중심 설계가 맞다 — 이를
숨기지 않는다. 주장하는 것은 **V6 결과 비의존** 하나뿐 (git 이력이 지지:
범위 선언 커밋과 V6 결과 커밋의 선후 관계로 검증 가능).

관통 규율 3개:
1. **V6 결과 비의존** — 범위·셀 경계는 설계 불확실성 근거로만 정한다. V6 는
   "계약이 의도대로 동작하는가" sanity 였고, 그 수치로 범위를 조정하면
   데이터 의존이다 (r4 지시).
2. **NOMINAL 로 학습 금지** — nominal 은 manipulation-check 대표점이다.
3. 독립 uniform box 단독 금지 — **stratification 으로 coverage 보장 후
   셀 내 jitter** (r3 예약 이행).

---

## 1. 분포 구조 — 3×3 stratification

에피소드마다: **셀 draw (9셀 균등) → 셀 내 축별 uniform jitter.** 결정론 =
SHA-256 (namespace `"v3_train"`, `derive_spawn_u` 규약 동형 — 축별 인덱스
분리, 셀 draw 는 별도 인덱스).

```
층 A: 횡 반응성 (route_gain · sense_range)     weak / medium / strong
층 B: 종축 속도 프로파일                        cruise / sprint / sprint+slowdown
```

- 균등 9셀인 이유: 특정 조합(예: 고감지×무반응×이른 sprint)의 확률을 우리가
  모델링할 근거가 없다 — 균등이 최소 가정이고, 셀별 성능이 따로 보고되므로
  (§6) 가중은 사후 재해석 없이 독자가 다시 줄 수 있다.
- tie-break 는 **랜덤화하지 않는다** (r4 — 비정상성 금지. 변형은 OOD 로만).

## 2. 셀 정의 (전부 외부 앵커 없는 선언값 — 설계 불확실성 대역)

### 층 A — 횡 반응성

| 층 | route_gain | sense_range [m] | 비고 |
|---|---|---|---|
| weak | U[0.2, 0.4] | U[15, 25] | 하한 0.2: TRAIN 전 위협이 반응형 (0 이면 channel 부재 = v2 회귀) |
| medium | U[0.4, 0.6] | U[25, 35] | **nominal (0.5, 30) 포함 셀** |
| strong | U[0.6, 0.8] | U[35, 45] | ★ Hyunjun 예시 box(0.2–0.6 / 15–40) 상단 밖 확장 — 비준 대상 |

sense 하한 15 m: 교전 반경(1.125 m)의 ~13배 — "감지 > 교전" 의무 유지.

### 층 B — 종축 속도 프로파일

| 층 | 정의 |
|---|---|
| cruise | sprint·slowdown off (등속 순항 — v2 거동이 TRAIN 안에 nested) |
| sprint | sprint_range U[40, 80] m · sprint_frac U[0.8, 1.0] |
| sprint+slowdown | sprint 동일 + slowdown near = sprint_range (구간 연속), far = near + U[20, 40] m, slowdown_frac U[0.4, 0.8] |

### 공통 (모든 셀)

| 축 | 값 | 지위 |
|---|---|---|
| 능력 a_att, att_speed | 기존 THREAT_BRACKET (11,78)/(8,30) + CAPABILITY_RATIOS | 기 선언 유지 — TRAIN 분포와 **곱** |
| 스폰 r_range · azimuth | (250, 350) m · ±π/4 | docs/60 비준값 유지 |
| R_standby | **U[8, 16] m** (jitter — 방어측 초기화 축, 위협 아님) | 비준 대상 (Hyunjun 예시대역. 구속 = r_nk 6 밖) |
| jink_amp · homing 등 A2 상속값 | nominal 고정 (0.6 / 4.0 / …) | ★ (r1) **fixed inherited nuisance parameters** 로 명시 — defender 가 이 주기성/gain 을 암기할 수 있는 알려진 한계. TRAIN 에서 흔들지 않는 이유 = 귀속 보존. 완화 장치 = IID/OOD/A4 + sensitivity 등재 (OOD-JINK 후보) |

### ★ 지평선 재산술 (오류 18 규율 — TRAIN 최악 모서리)

```
최악 도달 = 350 / 8 = 43.75 s
slowdown 최악 = 40 m 구간을 0.4×8 m/s 로 통과: 40/3.2 − 40/8 = +7.5 s
전개·lock 여유 = +1.25 s
합계 52.5 s -> ★ episode_len_train = 1100 (55 s)  [nominal 의 1000 에서 상향
— nominal 게이트(P90)와 별도 값임을 명시. TRUNCATED 발생 시 해석 금지 +
재사전등록 규율 동일]
```

## 3. IID held-out

- TRAIN 과 **동일 분포·비중첩 draw**: seed namespace 분리
  (`"v3_train"` vs `"v3_iid"`) + episode 인덱스 대역 분리 (train 0..N,
  iid 10000..10000+M).
- 용도 = 분포 내 일반화. 학습 중 어떤 형태로도 노출 금지 (early stopping
  포함 — early stop 용 검증 세트는 train namespace 안에서 따로 뗀다).

## 4. OOD (구조 변형 — 평가 전용, 학습 금지)

| arm | 정의 | 검정하는 것 |
|---|---|---|
| OOD-Z | −z tie-break variant (r4 예약분) | "+z 암기" exploit 여부 — 유지되면 3D geometry 학습 증거 |
| OOD-CPA | route 를 CPA 예측 회피로 교체 (docs/60 §3.2 escalation 설계) | routing rule 구조 의존성 |
| OOD-TIMING | sprint_range U[90, 130] (분포 밖 이른 sprint) | 속도 전략 타이밍 의존성 |
| OOD-CORNER | route_gain 1.0 · sense 60 (box 밖 모서리) | 반응성 외삽 |

- A4 (self-play/optimizer) 는 OOD 가 아니라 별도 falsifier 층 (docs/60 §1).
- OOD 에서의 성능 하락은 실패가 아니라 **보고 대상** — 판정식은 §6.
- ★ (r1) OOD 의 지위: **반례를 찾는 장치이지 일반화 인증서가 아니다.**
  허용 문장 = "사전등록된 4종의 structural/parametric OOD perturbation
  에서 성능 유지 여부를 시험한다". "암기가 아님을 증명" 표현 금지.
  **OOD-CPA 가 headline 의 핵심 falsifier 다** — angular-gap 에서만 gain 이
  있고 CPA 에서 사라지면 결론은 "angular-gap reactive attacker 에서
  cooperative shaping 을 학습했다" 로 제한된다.
- ★ (r1) scope limitation 명시: 본 계약의 위협은 **수평 섹터 last-mile**
  이다 (스폰 수평 ±45° + z 지터 ±5 m). 수직 접근(다이브)은 범위 밖 —
  3D shepherding 일반 주장을 하려면 elevation OOD 가 별도로 필요하다.

## 5. 배선 계획 + 게이트 (결과 보기 전 선언)

- 배선 = `scale_v2.py` 에 `draw_threat_v3(seed, episode, layer)` —
  `m4_config.draw_threat` 패턴 동형 (SHA-256, layer ∈ {train, iid}).
  AttackerSpec/StandbySpec 필드로만 구성 (새 코드 경로 없음).

```
P92  분포 배선 게이트:
     (i)   결정론 — 동일 (seed, episode, layer) -> 동일 draw (bit)
     (ii)  coverage — n=900 draw 에서 9셀 각 100±귀무 이항 CI (균등 검증)
     (iii) 경계 준수 — 전 draw 가 선언 범위 안 (표본 전수)
     (iv)  NESTING — layer 미지정 시 기존 경로와 bit 동일
P93  TRAIN 침투 보존 표본검사: train draw 50판 · defender 제거 ->
     50/50 PENETRATED · TRUNCATED 0 (P90 동형 — 분포 모서리의 자멸 배제.
     episode_len_train=1100 의 첫 검증을 겸함)

P94  ★ (r1, 리뷰 5 수정 1 — 학습 전 필수) natural-state route paired
     ablation: V3-FULL NOMINAL · ep 0..49 · 동일 seed paired
     {route ON (nominal)} vs {route OFF (route_gain=0, 그 외 전부 동일)}.
     defender = hold (자연 발생 상태 — teleport 개입 없음).
     보고 (수락대역 없음): route 활성률 · attacker 행동/궤적 발산 (첫 발산
     스텝·max) · v_shot_soft 차이 · fire_step 변화 · label 변화 수.
     판정 (결과 보기 전 고정): green = paired 판의 ≥ 50% 에서 궤적 max
     발산 ≥ 1 m (1 m·50% 는 앵커 없는 선언값 — 300 m 스케일 대비 보수적
     최소 크기). ★ green 전에는 "학습 가능한 shepherding channel" 명칭
     금지 (허용 = "구현·검증된 causal channel", docs/62 §2).
     red 여도 학습 금지 아님 — 단 기전 서사가 "shaping" 에서 "속도/기하
     적응" 으로 강등된 채 진행 여부를 재결정한다.

P95  ★ (r1, 리뷰 5 수정 2) realized-reactivity audit: 분포 배선 후 셀별
     n=30 draw 에서 realized/requested route authority + 궤적 response
     크기를 측정. 판정: 동일 속도 regime 안에서 weak < medium < strong
     순서 유지. 깨지면 해당 셀 라벨이 잘못된 것 — 셀 경계 재사전등록
     (성능 아닌 기하 관측이므로 학습 전 수행이 안전).
```

### 5.1 ★ P94 결과 (2026-08-07 — `results/threat_v3_p94.json`, 판정식 커밋 f5c75b6 은 결과 전)

```
발산 >= 1 m: 46/50 (판정 기준 >= 25/50 의 1.8배) · 발산 > 0: 50/50
route 활성률 평균 0.13 · label 변화 7/50 · fire 시각 변화 5/50
label 변화의 방향성 관찰: HARD_KILL->PENETRATED 4 · CAPTURED->PENETRATED 2
  · HARD_KILL->CAPTURED 1 -- route ON 이 방어측 무력화를 회피하는 방향
```

**판정 = GREEN.** 자연 발생 상태에서 route 는 궤적 수준(전판)·임무
수준(14%)의 측정 가능한 인과효과를 갖는다. → docs/62 §2 의 명칭 제한 해제:
**"학습 가능한 shepherding channel"** 사용 가능 (단 "학습이 실제로 이용했다"
는 여전히 MARL 결과 + static/active 대조의 몫). 리뷰 5 최위험 가정이 이
표본에서 지지됐다.

- **비교 구조 (headline)**: `hold` vs `scripted(bearing-aware 재배치)` vs
  `MARL` — **같은 TRAIN/IID/OOD 분포 위, paired CRN**. nominal 점 비교를
  headline 으로 쓰지 않는다.
- ★ **scripted baseline 동결 (리뷰 5 수정 3)**: bearing-aware scripted
  redeployment controller 의 **관측 집합·규칙 family·튜닝 예산·파라미터
  탐색 예산**을 **docs/63 으로 학습 결과 전에 동결**한다. 실행은 나중이어도
  되나 설계 고정이 먼저다 — "결과를 본 뒤 만든 baseline" 방지.
- ★ **primary endpoint (lexicographic — E[J] 모호성 제거)**:
```
1차   NET_CAPTURE 율 개선 (논문 스파인 = 비손실 포획)
2차   total defense (= 1 − penetration) 비열화
3차   최악 셀 penetration 비열화 (9셀 × regime 분할)
보조   CVaR_0.1 limiter 소모 · wasted_fire · TRUNCATED(=0 강제)
```
  - 비열화 판정 = raw 점추정이 아니라 **사전 고정 margin + CI**:
    비열화 margin = 5 %p (앵커 없는 선언값 — 비준 대상), 95% CI (paired
    bootstrap, seed resample) 상한이 margin 안일 때만 비열화 인정.
  - ★ **9셀 전체 결과 벡터는 headline 판정과 무관하게 의무 공개** —
    "최악 셀 비열화" 는 2위 취약 셀의 악화를 숨길 수 있으므로 (리뷰 5
    §6-iii), 셀 벡터 공개가 그 보완이다.
- 판정 규율: lexicographic 1~3 을 모두 보일 때만 "개선" — 일부만 성립하면
  그 단계까지 분리 보고 (리뷰 3·4 의 두-줄 규율).
- 유도(shepherding) 주장: P88 + **P94 green** 이 필요조건. 충분조건은
  V3-FULL 위 static vs active limiter 대조 후에만.

## 7. 비준 체크리스트 (Hyunjun — r1)

```
[ ] balanced design distribution 명명 + nominal-중심 인정 문구 (§0)
[ ] 3×3 stratification 구조 + 9셀 균등 (§1)
[ ] 층 A 셀 경계 — 특히 strong 층의 예시-box 밖 확장 (0.8 / 45 m) (§2)
[ ] 층 B cruise 층 포함 (§2)
[ ] R_standby jitter U[8,16] (§2)
[ ] A2 상속값 = fixed inherited nuisance parameters (§2)
[ ] episode_len_train = 1100 (§2 산술)
[ ] IID 분리 규약 (§3) · OOD 4 arm + 지위 문구 (§4)
[ ] P94 판정값 (발산 1 m · 판 비율 50%) — 앵커 없는 선언 (§5)
[ ] P95 realized-reactivity 순서 판정 (§5)
[ ] lexicographic primary endpoint + 비열화 margin 5 %p·95% CI (§6)
[ ] scripted baseline 동결 문서 = docs/63 (학습 결과 전) (§6)
```
