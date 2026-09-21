# 107 — W5 MARL 진입 판정 (r1, 봉인)

- **판정일**: 2026-09-22 (W5 milestone 조기 종결)
- **상태**: **PASS — MAPPO hyperparameter pilot 착수 허용.**
- **정본 산출물**: `artifacts/r2b/b2_scripted/w5_decision.json`
- **재현 명령**: `python -m shepherd.scripts.b2_w5_decision`
- **범위**: B0 v3의 A2-nominal 조건에서 clean net capture frontier를 측정할 수
  있는지와, 그 문제에 MAPPO 설정 탐색을 시작할 연구 투자 근거가 있는지만 판정한다.

> **PASS의 뜻**: 현 B0 v3에서 rule baseline의 clean-net `chi50`을 계획한 범위에서
> 추정할 수 있고, scripted controller가 회수하지 못한 제어 문제가 남아 있다.
> `RULE_COOP − SOLO > 0`은 필요조건이 아니다.

> **PASS가 뜻하지 않는 것**: 학습 성공, 학습 정책의 경계 확장, 협력 필요성, c5 규칙의
> 우월성, Q1 신규성, 실제 기체 타당성을 인정하지 않는다. 본 학습은 W6 training
> contract를 별도로 봉인한 뒤에만 시작한다.

## 1. 판정 규칙의 계보

2026-09-18 초안은 B2 primary를 열기 전에 다음 투자 문턱을 제안했다.

1. 기준 arm은 `RULE_COOP`, 성공은 전체 에피소드 분모의 `N`만 사용한다.
2. `(eta, lambda) × seed`마다 chi 오름차순의 `P(N)`에 비증가 PAV를 적용하고
   `p=0.5` crossing을 구한다.
3. 3 seed 중 2 seed 이상 crossing이 유한하면 해당 행을 `row-estimable`로 둔다.
4. 14행 중 12행 이상이면서 각 lambda slice에서 5/7행 이상이면 PASS다.
5. primary arm에서 crossing censoring이 발생할 때만 B0 v3의 격자 확장 규칙을
   적용한다. 효과 크기를 보고 확장하지 않는다.

초안은 결과 전에 작성됐지만 당시 **미추적 파일**이었다. 따라서 VCS 시각으로
선등록을 증명할 수 없으며, 이 문턱을 confirmatory preregistration이라고 부르지 않는다.
본 문서는 그 초안을 결과 판독 규칙으로 채택한 **신규 연구 투자 판정**이다. 후속 학습
결과를 본 뒤 이 문턱을 다시 바꾸지 않는다.

## 2. 입력과 유효성

| 입력 | 정본·결과 | 판정에서의 역할 |
|---|---|---|
| B2 primary | 100,800 ep, 실행 `fd4eb19`, 수확 `121d92d` | frontier와 scripted 진단 |
| 완료 점검 | `b2_check --expect-commit fd4eb19`, **5/5 PASS** | 데이터 유효성 gate |
| primary readout | `638db52`, pairing·identity PASS | `P(N)`과 outcome 분할 |
| 궤적 재생 | 로컬 2/3, 동일 랩 서버 **3/3 PASS** (`a5355a7` 기록) | swept engagement 의미 확인 |
| forced-fire | 436 probe, `a5355a7`, intervention 전 동일성 PASS | gate/attainability 진단만 |
| Amendment A1 | docs/108, `49b358c` | `H_illegal`을 실효 swept resolver와 일치 |

저장소의 `viz/illegal_replay.json`은 로컬의 2/3 재생 기록을 보존한다. 서버 3/3은
`a5355a7` 커밋 기록과 docs/108에 등재돼 있으며, 별도의 서버 replay JSON은 없다.
이 한계를 숨기지 않되, 같은 실행 환경의 3/3 재생과 A1 정정으로 의미 오류 선행조건은
충족한 것으로 판정한다.

forced-fire는 primary와 pooling하지 않았다. R2b의 `C_POSITIVE`도 다른 B0 hash의
search-based attainment benchmark이므로 현세계 PASS 수치에 합치지 않는다.

## 3. 기계 판정 결과

`shepherd/scripts/b2_w5_decision.py`는 원 primary shard에 대해 완료·계보 검사를 다시
수행하고, R2a와 같은 equal-weight PAV 및 50% 선형보간을 적용한다.

| 항목 | 문턱 | 관측 | 판정 |
|---|---:|---:|---|
| RULE_COOP row-estimable | >=12/14 | **14/14** | PASS |
| lambda slice 0 | >=5/7 | **7/7** | PASS |
| lambda slice 2 | >=5/7 | **7/7** | PASS |
| seed coverage | 행마다 >=2/3 | **전 행 3/3** | PASS |
| RULE_COOP censoring | 없어야 함 | **0** | 확장 불필요 |

참고로 SOLO도 14/14행, 두 slice 7/7, 전 행 3/3으로 추정 가능하며 censoring은
없다. 이 값은 W5 PASS 근거를 대체하지 않는 대조 진단이다.

**최종 판정: `PASS`.** 현재 격자는 학습 정책과 rule baseline의 clean-net frontier를
비교할 수 있는 측정 지지대를 제공한다.

## 4. 함께 봉인하는 진단 해석

### 4.1 scripted controller

- `P_N`: SOLO 0.5310, RULE_COOP 0.5331, `Delta p_N = +0.0020`.
- CRN 50,400쌍 중 SOLO-only N 3,472, RULE-only N 3,575로 순차이는 103쌍인
  반면 discordant pair는 7,047쌍이다.
- cell × seed 부호는 양 28, 음 14, 혼합 14이며 일관된 우세 영역이나 chi축
  단조 pattern이 없다.
- RULE_COOP은 비인가 kinetic engagement를 2,840/50,400 = **5.63%** 발생시켰다.
  SOLO는 구조적으로 0이다. Amendment A1에 따라 이를 “불법 충돌”이라 부르지 않는다.

따라서 c5 arc는 attacker 궤적을 크게 바꾸지만 clean capture를 순증가시키지 못하고,
비인가 kinetic engagement를 추가한다. c5의 성능을 인정하는 결과가 아니다.

### 4.2 forced-fire

- 선택·강제 발사: 436/436
- intervention 전 재생 동일성: 전 표본 참
- 강제 발사 후 net capture: **0/436**, recovery rate 0.0
- 결과: `F_other` 392, `H_illegal` 29, `H_fb` 15

docs/102 §5.5의 세 번째 갈래를 적용한다. 경계 band의 no-FIRE 실패는 FIRE gate
censoring이 핵심 원인이 아니다. band 중점에서 발사를 강제해도 attacker가 post-FIRE에
빠져나가므로, 남은 병목은 이 대리세계 안의 **attainability/controller** 축이다.

### 4.3 W5가 허용하는 결론

세 증거는 한 방향을 가리킨다.

1. clean-net frontier는 전 행에서 측정 가능하다.
2. 고정 c5 규칙은 그 기회를 회수하지 못하고 doctrine 비용을 만든다.
3. FIRE gate 제거만으로 실패가 회복되지 않는다.

따라서 다음 질문은 “발사를 더 허용하면 잡는가”가 아니라, **관측된 상태에서 limiter와
capturer를 폐루프로 제어하여 post-FIRE capture condition을 만들고 유지할 수 있는가**다.
이 질문을 시험하기 위한 MAPPO 설정 탐색을 승인한다.

## 5. 허용 행동과 남은 gate

### 지금 허용

- Gym/CTDE 배선 검증 및 MAPPO hyperparameter pilot
- pilot 범위 안에서 learning rate, entropy, clip, GAE lambda, reward scale의 저비용 탐색
- 학습·평가 seed namespace 분리와 로그/체크포인트 검증

### W6 training contract 전까지 금지

- 본 3-seed 학습 campaign
- pilot 결과를 본 뒤 평가 격자·성공 정의·primary metric 변경
- `P_U`·`H_fb`·forced-fire 결과를 clean-net 학습 성공에 합산
- “협력이 필요하다”, “경계를 확장했다”, “실제 체계에 유효하다”는 주장

W6 계약은 pilot 판독 후, 본 학습 optimizer update 전에 봉인한다. hyperparameter 선택,
평가 checkpoint, seed, 예산, 중단 규칙, `H_illegal` reward/credit 처리와 arm 간 공통
초기조건을 포함해야 한다.

## 6. W6 이연 항목 — BC 계약 수정

기존 mixed-role c5 trajectory 전체를 positive behavior-cloning 교사로 사용하지 않는다.
c5는 clean-net 순이득이 없고 5.63%의 비인가 kinetic engagement를 포함한다.

W6에서 다음 기본안을 검토·봉인한다.

- **capturer/fire head만 사전학습**한다.
- limiter는 **neutral/hold 초기화**에서 시작해 joint RL로 학습한다.
- `H_illegal` 에피소드는 positive demonstration에서 제외한다.
- 제외된 에피소드를 negative/safety 데이터로 재사용하려면 그 목적과 loss를 별도로
  선언한다. 단순 positive BC에 섞지 않는다.
- 모든 학습 arm의 초기조건 비교 가능성을 유지하도록 동일 데이터·반복수·중단 규칙을
  적용한다.

이 문단은 training contract 자체가 아니다. docs/89 §4의 common mixed-role BC 조항을
그대로 실행하지 말라는 **W6 수정 요구**이며, 최종 선택은 W6 문서에서 봉인한다.

## 7. 판정 한계

- B0 v3은 reduced-order 3DOF 대리세계다. 외부 타당성을 만들지 않는다.
- A2-nominal 조건부 결과이며 적응형 상대 전체에 대한 강건성을 뜻하지 않는다.
- Amendment A1은 문서–구현 일치 정정이지 새로운 물리 검증이 아니다.
- forced-fire 0/436은 이 intervention과 boundary-band 표본에 한정된다. 모든 가능한
  발사 정책이 실패한다는 불가능성 증명이 아니다.
- PASS는 연구비·시간을 학습 pilot에 투입할 근거이며 논문 결론이 아니다.
