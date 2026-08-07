# 61 — THREAT_V3_TRAIN 분포 사전등록 r2 (★비준·동결)

**2026-08-07 · 학습 결과를 보기 전에 쓴다. r0 = 초안 · r1 = 리뷰 5 수정 3개
· r2 = Hyunjun 최종 4수정 반영 후 **비준·동결** (§8 비준표). 학습 개시 후
불변경 — 조정은 새 사전등록으로만.**

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

- (r2 수정 1) 9셀 균등은 실제 위협 빈도에 대한 추정이 **아니라**, 사전
  정의한 각 regime 에 동일한 실험 가중치를 부여하는 **balanced design
  choice** 다. 셀별 결과를 전부 공개하므로 (§6) 다른 위협 가중에 대한
  재집계가 가능하다. ("최소 가정" 표현 삭제 — §0 재명명과 모순이었음)
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
| R_standby | **U[8, 16] m** | 비준 (r2) — ★ **위협 파라미터가 아니라 defender initialization uncertainty.** 에피소드 분포 = P_threat(θ_A) × P_init(θ_D) 로 분리 표기하고, "threat distribution" 에 포함시켜 부르지 않는다 |
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

P95  ★ (r2 수정 3 — paired CRN 재정식화) realized-reactivity audit:
     base episode n=30 각각에서 능력(a_att·att_speed)·속도 프로파일 draw·
     spawn·azimuth·standby·jink 위상을 **전부 고정**하고 reaction stratum
     draw (route_gain·sense_range) 만 weak/medium/strong 으로 교체한
     paired 3중 비교 (속도 regime 별 반복).
     ★ primary metric (하나로 고정):
       R_route = (1/T_active) Σ_{t∈active} |a_route,realized(t)|
       (realized = 클립 후 총가속의 route 방향 사영 — P89 기록 필드)
     보조(진단 전용): realized/requested 비 (saturation 진단 — strong 에서
       역전될 수 있어 primary 로 쓰지 않는다) · route-OFF paired 궤적 발산.
     판정: paired base 30판의 R_route 평균과 중앙값이 **둘 다**
       weak < medium < strong. tie/역전 처리: 인접 층 차이가 0 이하
       (평균 또는 중앙값 어느 쪽이든) 이면 해당 층 경계 미확정 → 셀 경계
       재사전등록 (성능 아닌 기하 관측이므로 학습 전 수행이 안전).
```

### 5.1 ★ P94 결과 (2026-08-07 — `results/threat_v3_p94.json`, 판정식 커밋 f5c75b6 은 결과 전)

```
발산 >= 1 m: 46/50 (판정 기준 >= 25/50 의 1.8배) · 발산 > 0: 50/50
route 활성률 평균 0.13 · label 변화 7/50 · fire 시각 변화 5/50
label 변화의 방향성 관찰: HARD_KILL->PENETRATED 4 · CAPTURED->PENETRATED 2
  · HARD_KILL->CAPTURED 1 -- route ON 이 방어측 무력화를 회피하는 방향
```

**판정 = GREEN.** (r2 수정 2 — 명칭 한 단계 제한) 허용 문장:

> *Natural V3-FULL trajectories 에서 angular-gap response 는 50/50
> episode 의 공격자 궤적을 변화시켰고, 7/50 에서는 mission label 까지
> 바꿨다. 따라서 P88 에서 확인된 defender-geometry → attacker-response
> channel 은 artificial teleport states 에 국한되지 않는다.*

명칭 사다리 (r2 확정):
```
P88          directionally controllable causal channel
P94          naturally expressed, mission-relevant shepherding causal channel
MARL 결과 후  learned shepherding
```
**"학습 가능한(learnable)" 은 보류** — P94 는 환경의 controllable causal
mechanism 을 보인 것이지, reward→credit→policy gradient 가 그것을 이용할
수 있는지는 별개다 (COMA/legacy reward 의존은 알려진 별도 blocker 후보).
주의: label 변화 다수가 route ON 의 방어 회피 방향인 것은 **공격자의
reactive competence** 증거이지 "defender 가 원하는 방향으로 shepherd 했다"
는 결과가 아니다 — 후자는 active limiter policy 의 몫.

- **비교 구조 (headline)**: `hold` vs `scripted(bearing-aware 재배치)` vs
  `MARL` — **같은 TRAIN/IID/OOD 분포 위, paired CRN**. nominal 점 비교를
  headline 으로 쓰지 않는다.
- ★ **scripted baseline 동결 (리뷰 5 수정 3)**: bearing-aware scripted
  redeployment controller 의 **관측 집합·규칙 family·튜닝 예산·파라미터
  탐색 예산**을 **docs/63 으로 학습 결과 전에 동결**한다. 실행은 나중이어도
  되나 설계 고정이 먼저다 — "결과를 본 뒤 만든 baseline" 방지.
- ★ **primary endpoint (r2 수정 4 — lexicographic, 전 단계 CI 판정)**:
```
comparator  headline "MARL 개선" 은 사전등록된 strongest nonlearned
            baseline = scripted (docs/63) 대비. hold 와도 무조건 비교하고
            scripted 가 hold 보다 나빠도 둘 다 전체 공개 (comparator
            사후 선택 봉쇄)
1차   Δ_net = p_net^MARL − p_net^scripted 의 paired bootstrap 95% CI
      lower bound > 0  (점추정 개선 불인정)
2차   total defense (=1−penetration) 열화의 95% CI upper ≤ +5 %p
3차   최악 셀 penetration 열화의 95% CI upper ≤ +5 %p (9셀 × regime)
보조   CVaR_0.1 limiter 소모 · wasted_fire · TRUNCATED(=0 강제)
```
  - margin 5 %p = 외부 앵커 없는 연구설계 margin (결과 후 불변경).
  - ★ **9셀 전체 결과 벡터는 headline 판정과 무관하게 의무 공개** —
    "최악 셀 비열화" 는 2위 취약 셀의 악화를 숨길 수 있으므로 (리뷰 5
    §6-iii), 셀 벡터 공개가 그 보완이다.
  - OOD-CORNER (route_gain 1.0) 보고 시 requested/realized authority 병기
    (shared budget 때문에 "더 강한 실제 reaction" 이 아닐 수 있음 — r2).
- 판정 규율: lexicographic 1~3 을 모두 보일 때만 "개선" — 일부만 성립하면
  그 단계까지 분리 보고 (리뷰 3·4 의 두-줄 규율).
- 유도(shepherding) 주장: P88 + **P94 green** 이 필요조건. 충분조건은
  V3-FULL 위 static vs active limiter 대조 후에만.

## 7. 비준표 (2026-08-07 Hyunjun — r2 로 동결)

```
[v] 구조 전체 (5층·3×3·9셀 균등)          비준 ("수정 후 비준" — 4수정 이행)
[v] strong 층 0.8/45 확장                 비준
[v] cruise 층 포함                        강한 비준 (sprint-암기 방지)
[v] R_standby U[8,16]                     비준 + P_init 분리 표기 (r2 반영)
[v] A2 상속값 fixed nuisance              비준 (OOD-JINK 는 등록만 — CPA/A4 우선)
[v] episode_len_train = 1100              조건부 — ★P93 green 후 확정
[v] IID namespace                         비준
[v] OOD 4종 (CPA = 핵심 falsifier)        비준 (CORNER 는 authority 병기 조건)
[v] P94 판정값 (1 m·50%)                  비준 (실행 완료 — GREEN, §5.1)
[v] P95                                    r2 재정식화 조건부 비준 (paired CRN·R_route)
[v] noninferiority margin 5 %p            비준 (결과 후 불변경 조건)
[v] scripted baseline docs/63 선동결      필수·비준
```

r2 4수정 이행: ① §1 "최소 가정" 삭제 ② P94 명칭 사다리 (learnable 보류)
③ P95 paired CRN + primary R_route ④ 1차 endpoint CI 판정 + comparator 고정.

**잔여 blocker (학습 전)**: P95 실행 (분포 배선 P92 후) · docs/63 동결.
P92/P93 은 correctness/sanity gate — green 이면 통과.
