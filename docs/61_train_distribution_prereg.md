# 61 — THREAT_V3_TRAIN_DISTRIBUTION 사전등록 초안 r0 (Hyunjun 비준 대기)

**2026-08-07 · 학습 결과를 보기 전에 쓴다. docs/60 §1 의 TRAIN/IID/OOD 층을
동결하는 문서다. 지위 = 초안 — 비준 후 확정, 학습 개시 후 불변경.**

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
| jink_amp · homing 등 A2 상속값 | nominal 고정 (0.6 / 4.0 / …) | TRAIN 에서 흔들지 않음 — 축을 늘릴수록 귀속 약화. OOD 로만 변형 |

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
```

## 6. 평가 프로토콜 (학습 결과 전 동결)

- **비교 구조 (headline)**: `hold` vs `scripted(재배치 휴리스틱, 추후 선언)`
  vs `MARL` — **같은 TRAIN/IID/OOD 분포 위, paired CRN** (동일 seed·draw).
  특정 nominal 점 비교를 headline 으로 쓰지 않는다.
- **지표 (per arm × per 분포층)**:
```
E[J]        NET_CAPTURE율 · neutralized율 · penetration율 (평균)
Q_0.1       9셀 × regime(SHAPING/FREE) 분할별 penetration 의 최악 셀
            (평균 뒤에 숨은 corner 실패 노출)
CVaR_0.1    limiter 소모 수 분포의 상위 10% 평균 (손실 위험)
보조         wasted_fire · TRUNCATED (0 이어야 — 아니면 horizon 재등록)
```
- 판정 규율: "MARL 이 이겼다" 는 **E[J] 개선 ∧ 최악 셀 비열화** 를 함께
  보일 때만. 한쪽만 성립하면 그대로 분리 보고 (리뷰 3·4 의 두-줄 분리 규율).
- 유도(shepherding) 주장: P88 통과는 필요조건일 뿐 — 유도 성공 주장은
  V3-FULL 위 static vs active limiter 대조 + (필요 시) route 인과 paired
  ablation 후에만.

## 7. 비준 체크리스트 (Hyunjun)

```
[ ] 3×3 stratification 구조 + 9셀 균등 (§1)
[ ] 층 A 셀 경계 — 특히 strong 층의 예시-box 밖 확장 (0.8 / 45 m) (§2)
[ ] 층 B cruise 층 포함 (TRAIN 안에 비반응 종축 = v2 거동 nested) (§2)
[ ] R_standby jitter U[8,16] (§2)
[ ] A2 상속값(jink 등) TRAIN 고정 (변형은 OOD 로만) (§2)
[ ] episode_len_train = 1100 (§2 산술)
[ ] IID seed/에피소드 분리 규약 (§3)
[ ] OOD 4 arm 정의 (§4)
[ ] 평가 판정식 — E[J] ∧ 최악 셀 비열화 동시 조건 (§6)
[ ] scripted 재배치 휴리스틱 arm 의 설계는 별도 문서로 (§6 — 미정 명시)
```
