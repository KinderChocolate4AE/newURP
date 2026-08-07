# 63 — scripted baseline (bearing-aware 재배치) 사전 동결 r2 — 비준·동결

**2026-08-08 · docs/61 §6 (리뷰 5 수정 3) 가 예약한 문서. headline comparator
의 설계를 **MARL/tuning 결과를 보기 전에** 동결한다 ("결과를 본 뒤 만든
baseline" 방지). docs/69 TRAIN FINAL FREEZE (hash efeffcbf) 후 작성 — 본
설계는 P95′ 진단 수치를 사용하지 않는다.
r0 → r1 = 조건부 승인의 필수 수정 4건 이행: ① "strongest nonlearned"
명칭 삭제 → bounded wording (§0) ② 튜닝/headline 평가 표본 완전 분리
(§3.1 신설) ③ parameter-free permutation 최소비용 slot assignment (§2)
④ F1/F3 capability parity — actor 관측 코드 확인 + commit 권한 차이 명시
(§1·§2). r1 → r2 = 최종 조건부 승인의 수정 1건 이행: **sole primary headline
set = IID 10000..10299 (n=300)** — TRAIN 20000 대역 제거, headline
판정 데이터셋 단일화 (§3.1). **r2 = 비준·동결 — 구현·튜닝 인가.****

★ **baseline 지위 (r1 고정 문구 — 논문 그대로 사용)**:

> The scripted comparator is not claimed to be globally optimal or the
> strongest possible nonlearning controller. It is the best controller
> selected within a preregistered, observation-matched bearing-aware arc
> family and fixed tuning budget. The family and selection budget were
> frozen before either scripted tuning outcomes or MARL outcomes were
> observed.

---

## 0. 지위와 비교 구조

- headline (docs/61 §6, lexicographic): Δ_net = p_net^MARL − p_net^scripted
  의 paired bootstrap 95% CI lower > 0 이 1차. hold 와도 무조건 비교·공개.
- 명칭 (r1): "strongest nonlearned baseline" **사용 금지** — 정확한 지위는
  "best preregistered scripted baseline within the frozen bearing-aware
  arc family and tuning budget". 논문 표기 = `scripted bearing-aware
  baseline` + methodology 에 "best of the preregistered 3×3 grid".
- 본 문서가 동결하는 것 = **F1~F9** (관측·rule family·튜닝 예산·선택 기준·
  접근 규칙). 튜닝 **실행**·최종 파라미터 선택은 비준 후, MARL 결과 전.
- 원칙: scripted 는 MARL 과 **같은 world contract** (ratified F-계약 +
  TRAIN 분포 hash efeffcbf) 위에서 돌고, A4c manifest parity 로 "controller
  만 다르고 world 동일" 을 인증한다 (docs/65).

## 1. F1 — runtime 관측 (controller 가 매 스텝 쓸 수 있는 것)

**MARL 정책 관측의 부분집합만** 허용 (privileged 금지, F9):

```
자산 위치 (원점, 상수) · 자기(limiter) 위치·속도 · 공격자 위치·속도
· threat_obs 2축 (a_att, att_speed — MARL 도 받는 관측)
· 아군 limiter 위치 (관측 벡터에 포함된 편대 상태)
```

**금지 (F9)**: 위협 은닉 파라미터 (route_gain·sense_range·sprint/slowdown
설정) · 미래 상태 · 관측 벡터 밖의 어떤 env 내부량. bearing 은 에피소드
시작 시 기지 (docs/61 §4 스코프 — MARL 과 동일 가정).

**F1 코드 확인 (r1 — 비준 전 검증 완료)**: 관측은 전 에이전트가 공유하는
global 벡터다 (env.py:204-214 `_obs_vector` — limiter 전기 상태 + finisher
+ attacker + FSM + v_shot 3량; CTDE actor/critic 분리 관측이 아님). 따라서
① 아군 limiter 위치는 **actor 관측에 실재** — scripted 사용 적법.
② `v_shot_soft/worst/p_feasible` 도 actor 관측에 실려 있어 **privileged
가 아니다** (docs/48 §10.2 동형). 그럼에도 limiter controller 의 v_shot
소비는 **family 제한** 으로 금지한다 (근거 = 기하 재배치 family 의 정의;
privileged 논거 아님 — 오독 방지 재서술). scripted finisher 의 clean
임계 교차 사용은 기존 기저선과 동일 (변경 없음).

## 2. F2/F3 — rule family (구조를 이것으로 제한)

**bearing-aware arc redeployment** — 기존 프리미티브 재사용 (신규 유도
법칙 발명 금지, docs/48 §3.1 한 곳 원칙):

1. **slot 계산**: 공격자 현재 bearing φ_att(t) (자산 기준 수평각) 중심으로
   slot 4개를 반경 R_d 호(arc)에 등간격 Δφ 로 생성:
   `s_k = 자산 + R_d·(cos, sin)(φ_att + (k − 1.5)·Δφ)`, z = 0
   (z=0 은 **scope limitation 으로 명시** — 수평 섹터 last-mile 스코프
   (docs/61 §4)·standby z=0 과 정합. MARL 이 3D 배치로 이기는 경우
   mechanism attribution 에서 vertical 기여를 별도 확인한다).
2. **slot 배정 (r1 — parameter-free assignment)**: limiter→slot 매핑은
   고정 인덱스가 아니라 **매 스텝 24개 permutation 전수에서 현재 이동거리
   제곱합 최소** `π* = argmin_π Σ_i |p_i − s_π(i)|²` 를 고른다 (동률 =
   사전순 첫 permutation, 결정론). oracle·예측·신규 hyperparameter 없음 —
   초기 인덱스 artifact (교차 이동) 제거를 위한 structural correction.
3. **slot 추종**: 기존 PD (`scripted.limiter_kp/kd` 선언값 8.0/4.0 재사용,
   재튜닝 금지) 로 slot 호밍, `a_lim_max` 클립 (능력 계약 그대로).
4. **갱신 규칙**: slot·배정은 매 스텝 φ_att(t) 로 재계산 (reactive) — 예측
   lead 없음 (lead 모델은 family 밖. 확장은 새 사전등록).
5. **commit 비트 = 0 고정** (`_zero_commit` 규약). ★ **capability parity
   명시 (r1)**: headline MARL 은 limiter commit 이 live 다
   (`limiter_commit=True`, M4 계약) — 즉 scripted 와 행동권한이 다르다.
   따라서 (i) intercept+commit 참조선 (docs/47) 을 headline 표에 항상
   병기 공개하고, (ii) 다음 scope 문구를 고정한다: *"the headline scripted
   comparator intentionally isolates nondestructive formation control;
   destructive-commit reference lines are reported separately."* 2차 지표
   (1−penetration) 에서 MARL 의 hard-kill fallback 이득 가능성은 이 병기로
   드러난다. 논문 표현 규율 (r2): ~~"MARL beats an equally capable
   scripted policy"~~ 금지 — 정확한 비교 = *"MARL vs a preregistered
   nondestructive bearing-aware formation controller"*.
6. finisher = 기존 scripted `clean` 발사 (변경 없음). 역할 분리 없음.

family 밖 (금지): 궤적 예측·CPA 계산 · v_shot 소비 · 위협 draw 의존 분기 ·
스텝별 규칙 전환 · z-축 배치 (수평 arc 한정 — 스코프 docs/61 §4 동형).

## 3. F4/F5 — hyperparameter 와 튜닝 예산 (전부 여기서 고정)

| 축 | 값 후보 (grid 전체 사전 선언) |
|---|---|
| R_d (배치 반경, m) | {6, 9, 12} — NK 반경 6 이상, standby 대역 [8,16] 부근. R_d=6 은 NK 경계와 일치하는 **declared geometric boundary candidate** 이지 "NK 경계가 물리적 최적" 이라는 주장이 아니다 (r1) |
| Δφ (slot 간격, rad) | {π/12, π/8, π/6} |
| (그 외 없음) | kp/kd·a_max·finisher 는 선언값 고정 — 자유도 2축뿐 |

- **튜닝 예산 (F5)**: 3×3 = 9 조합 × **one preregistered tuning
  namespace, 100 paired episode draws** (같은 에피소드 집합 paired CRN;
  "1 seed" 표현 대신 — 통계 단위는 고정 namespace 의 100 draws 다).
  총 900 롤아웃. 재시도·확장·seed 추가 없음.
- 튜닝 에피소드 대역: `train` layer, episode 5000..5099 (**학습 대역
  0..N·early-stop 검증 대역과 분리** — 대역 선언 자체가 F5 의 일부).

### 3.1 ★ 튜닝 표본 ≠ headline 평가 표본 (r1 신설 · r2 단일화 — 원문 고정)

> Episodes train/5000..5099 are used exclusively for scripted
> hyperparameter selection and never contribute to headline inference.
>
> **The sole primary headline evaluation set is the held-out IID layer:
> iid episodes 10000..10299 (n=300).**
>
> After scripted parameters and MARL training are frozen, hold,
> scripted, and MARL are evaluated on exactly these paired IID draws.
>
> All three preregistered lexicographic headline criteria are computed
> on this same IID set. TRAIN tuning outcomes, any secondary TRAIN
> evaluation, and all OOD evaluations cannot alter the headline
> decision.
>
> OOD arms remain preregistered falsification analyses and are reported
> separately.

- 구조 (selection → freeze → held-out evaluation 완결):
  TRAIN = MARL 학습 (0..N) + scripted 튜닝 (5000..5099) → 전부 freeze →
  **IID 10000..10299 에서 hold/scripted/MARL 세 팔 paired CRN → headline
  판정 (docs/61 lexicographic 1~3 전부 이 set 에서)** → OOD/A4 는
  falsification 별도 보고.
- IID 가 맞는 이유: scripted 는 TRAIN 에서 튜닝됐고 MARL 은 TRAIN 에서
  학습했다 — 둘 다 보지 않은 held-out namespace 에서 재는 것이 대칭적이고,
  train layer 내 대역 분리(20000..)와 달리 **학습 대역 확장과의 구조적
  비중첩이 namespace 로 보장**된다.
- n=300 은 **preregistered fixed evaluation budget** (기존 평가 규모 유지)
  이다 — v3 effect size 에 대한 power 보장 주장이 아니다 (r2 wording).
- max-선택된 조합의 튜닝 대역 성능(9조합 표)은 공개하되 headline 수치로
  재사용 금지.

## 4. F6/F7 — 데이터·선택 기준

- **F6**: 튜닝은 TRAIN layer 만. **IID/OOD 는 설계·튜닝·선택 어디에도
  절대 사용 금지** (docs/61 §6). offline 튜닝 지표는 TRAIN 롤아웃의 라벨
  집계만 (F9 분리: offline metric ≠ runtime 관측).
- **F7 (selection criterion, 사전 고정)**: 9 조합 중
  `p_net (NET_CAPTURE + CAPTURE_WITH_CONTACT 비율)` 최대.
  tie-break (순서 고정): ① total defense (1 − penetration) ② 낮은
  limiter 소모 ③ 작은 R_d. headline endpoint 와 정렬된 기준 하나만 쓴다.

## 5. F8 — 최종 동결

선택된 (R_d, Δφ) 와 튜닝 결과 전체(9 조합 표)를 결과 문서로 공개하고,
구현 커밋 hash 를 이 문서 r2 에 기입해 동결한다. **MARL 결과가 나온 뒤
baseline 의 어떤 요소도 변경 금지** (docs/62 §2 소급 규율 동형). scripted
runner 는 A4c manifest parity 를 통과해야 한다 (world contract 동일 인증).

## 6. 최종 비준표 (2026-08-08 Hyunjun — r2 로 동결)

```
[v] headline comparator 필요성                          승인
[v] "strongest nonlearned" 명칭                         기각 -> bounded wording (r1 이행)
[v] F1 관측 (actor 관측 부분집합)                        조건부 -> 코드 확인 완료 (공유 global 관측, r1 §1)
[v] rule family (reactive arc)                          승인
[v] slot assignment                                     수정 권고 -> permutation 최소비용 반영 (r1 §2)
[v] z=0 수평 arc                                        조건부 -> scope limitation 명시 (r1 §2)
[v] PD 선언값 고정                                       승인
[v] commit=0                                            조건부 -> capability parity 명시 (r1 §2; MARL commit live 확인)
[v] 3×3 grid + 900 롤아웃 + TRAIN only                  승인 (R_d=6 boundary 문구 추가)
[v] p_net 선택 + 단순 tie-break 유지                     승인 (LCB 등 신규 자유도 금지)
[v] 튜닝/평가 표본 분리                                  필수 -> §3.1 신설 (headline 대역 20000..20299 선언)
[v] F8 동결 + A4c parity                                승인
```

```
[v] primary headline dataset 단일화 (IID 10000..10299)   r2 이행 -> PASS
```

**최종 비준 완료 (전항 PASS) — 구현·튜닝 개시 인가.**
headline 평가 문구 (고정):

> Hyperparameter selection episodes are disjoint from all headline
> evaluation episodes. The selected scripted controller is frozen before
> evaluation and is subsequently evaluated under exactly the same paired
> world draws as MARL.

*비고: R_d·Δφ 후보값은 외부 앵커 없는 설계 선언값이다 (NK 반경·standby
대역이라는 기하 제약에서만 유도). 결과를 보고 grid 를 넓히는 것은 소급
튜닝이므로 금지 — 9 조합이 전부 나쁘면 그 사실을 그대로 보고한다.*
