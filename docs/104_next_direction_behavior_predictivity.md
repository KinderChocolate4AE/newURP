# 104 — 후속 연구 방향: 작은 논문 소재에서 net–kinetic 전환까지

> **문서 상태:** r6 — 방향 설계 노트, 미봉인. r5 착수 경로 교정 + r6 F1-E 축소
> 세계와 §3 장기 확장 세계의 구분 명시 (G0 확정 계약 = docs/106 r3)
>
> **개정일:** 2026-09-18
>
> **핵심 교정:** r3.1은 논문 한 편의 출발점으로 너무 크다. 아래의 첫 연구 질문을 현재
> 운영 판단으로 삼고, 뒤의 §0–§14는 결과가 좋을 때 꺼낼 **확장 메뉴**로 읽는다.
> “한 달이면 초안이 나올 듯한 소재”는 주제 선정의 감각이지 4주 완성·투고 마감이 아니다.
>
> **문헌 판단 교정:** 같은 MAPPO/PFSP, net capture, weapon–target assignment를 쓴 논문이
> 있다는 이유만으로 연구를 버리지 않는다. 방법론은 적극 재사용한다. 우리와 동일한
> 질문·교전규칙·실패기제·평가지표까지 다루는지가 선행성과의 실질 비교 단위다.
> r2의 `FIRE-now 대 WAIT` 및 일반적인 “기회 생성”은 단독 신규성으로 주장하지 않는다.
>
> **문서 권한:** 본 문서는 후속 Q1 연구를 제안한다. `docs/89` r4, B0 v3
> (`5e7b5b486b9d8a4a`), `docs/102`의 봉인 계약을 수정하지 않는다. 현 학기 계약을 바꾸려면
> 별도 판올림과 재봉인이 필요하다.
>
> **문헌 판정 한계:** 아래 신규성은 2026-09-16 현재 공개 1차 자료를 대상으로 한
> bounded-scan provisional gap이다. “최초” 주장은 정식 systematic search와 지도교수 확인
> 전까지 금지한다.
>
> **실행 문서:** 첫 그림의 contract-lite, 코드 경계, 산출물과 판정 순서는
> [105 — net–kinetic 전환 연구의 착수 계획](105_mode_switch_execution_plan.md)에 둔다.

---

## 먼저 — 지금 쓸 소재와 출판 형태

**첫 논문 소재는 net–kinetic mode 전환의 비용 문제로 잡는다.** 처음부터 큰 물리·강건학습
패키지 전체를 연구 질문으로 삼지 않는다.

> **같은 자산보호·안전 기준에서, 상황에 따라 net 포획을 시도하거나 kinetic 요격으로
> 전환하는 정책은 고정된 net-first 또는 kinetic-first 방침보다 어느 조건에서 비용을
> 낮추는가? 이종 방어기의 조향이 그 전환 조건을 어떻게 바꾸는가?**

이 질문은 오래된 비용 최소화·순차 의사결정 주제를 우리의 **단발 net, kinetic fallback,
반응형 공격기, 이종 조향** 교전으로 가져오는 것이다. MAPPO/PFSP, 동적 할당, reach-avoid
등 이미 쓰인 방법을 채택·비교하면 된다. “전환 의사결정 자체가 처음”이라는 주장은 하지
않는다. 차별화는 **같은 성공·안전 문턱 아래 물리적으로 다른 두 효과기의 전환이 언제
득실을 바꾸는지**를 재현 가능한 교전 모형과 직접 대조군으로 보이는 데서 찾는다.

**첫 그림을 볼 최소 실험:** 공격기 1대, net shooter 1대, kinetic effector 1대, 기존
저수준 유도기, 비용비 몇 개와 고정 교전규칙 2개(net-first·kinetic-first), 관측 상태에 따른
간단한 전환 정책 1개로 시작한다. 보호 성공률과 안전 위반의 동일 문턱을 적용하고,
그 문턱을 **탐색 표본에서 충족한 것으로 관측된** 정책 사이에서 비용–성공 곡선과
전환 사례를 비교한다. 이 그림이
흥미롭다면 learned switch 또는 학습된 조향을 넣고, 반응형 공격기·비용비·효과기
불확실성을 차례로 확장한다. 한 달은 이 **소재가 빨리 첫 그림으로 시험될 듯한가**를
판단하는 감각이지 연구·원고·투고를 끝낼 기한이 아니다.

**첫 그림의 지위는 F1-E exploratory** (§5.1)다. 같은 문턱을 양쪽에 적용하되
§9의 동시 신뢰경계·minimum detectable effect·confirmation split을 아직 적용하지
않으므로 “feasible”, “최저비용”, “recourse gain”의 확정 판정이 아니다. 목적은
world와 전환 비교가 연구할 만한 신호를 내는지, 그리고 어느 가정이 그 신호를 만드는지
찾는 것이다. 숫자 요약에 앞서 전환 전후 상대 궤적과 first-hit event를 시각화한다.

현 B0 v3는 net-first·scripted fallback을 강제하므로 **명시적 mode 선택은 별도 world
version의 변경**이다. 이를 docs/89·102의 현 학기 B2/MAPPO 실험에 끼워 넣지 않는다.
첫 실험에서도 전환 가능 시점, 양쪽 효과기의 성공 판정, 비용과 합법성 조건을 먼저
고정해야 한다. 기존 `p_kill=1`과 FIRE-time frozen net predicate만으로는 “현실의
최저비용”이나 실제 발사형 net의 물리 최적화를 주장할 수 없다. 초기 결론은
**선언한 모형·비용비·후보 정책에서의 달성비용 비교**이며, 최적성 주장은 범위를 증명하거나
전수 탐색한 작은 하위 문제에 한정한다.

**현재의 협력 학습 연구는 이 논문의 기반이자 독립적인 결과다.** B0 v3, R2a 경계 지도,
R2b의 봉인 예산 탐색 witness, B2 scripted 계약과 docs/89의 CTDE-MAPPO 세 arm을
계획대로 진행한다. 그 질문은 “학습된 조향이 fixed rule보다 clean net capture 성립
경계를 넓히는가”다. R2b C의 Δp_CA_net +0.370은 **탐색의 달성도 witness**이지 학습
정책의 성능이 아니다. 이 결과를 mode-switch 논문의 학습 성공 증거로 앞당겨 쓰지
않는다. B2 stop rule 이전 학습 금지 등 봉인 조항도 유지한다.

**출판 형태:** 목표는 Q1급 C-UAS 저널 논문이다. 다만 첫 원고의 중심 그림은 조건부 비용
이득과 반례로 잡고, 논문을 쓰며 어떤 한계가 결론을 흔드는지 확인해 필요한 축을
추가한다. 별도 학회·프리프린트 선행이나 4주 완성은 필수 일정이 아니다.
예컨대 post-FIRE 반응이 전환 순위를
좌우하면 live net을, 기존 A-family에 과적합하면 PFSP를, 순위가 kinetic 성공률에 민감하면
kinetic effect calibration을 우선한다. strict recourse certificate, F2/F3, raid economics를
한 편의 필수 묶음으로 요구하지 않는다. 양성 결과를 만들기 위해 세계를 사후 변경하지
않고, 변경마다 새 버전과 적용 범위를 기록한다.

### 선행연구를 다루는 규칙

| 선행연구와 겹치는 것 | 처분 |
|---|---|
| MAPPO, PFSP, MPC, WTA 등 **방법** | 검증된 레시피로 채택하고 강한 baseline으로 둔다. 방법이 같다는 이유로 주제를 폐기하지 않는다. |
| net 포획, 협력 추격 등 **넓은 현상** | 우리 교전규칙·효과기·공격자 반응·outcome의 차이를 정확히 적고 직접 비교한다. |
| 같은 질문과 거의 같은 세계·지표·대조군 | 결과 재현·확장으로 의미가 있는지 먼저 판단한다. 우선권을 새것처럼 주장하지 않는다. |

[Gavin & Bronz](https://arxiv.org/html/2607.05939)의 MAPPO+PFSP는 배울 방법이다. 그 논문의
기체 하부 rigid net과 우리의 지연·단발 net 및 kinetic fallback은 같은 교전이 아니다.
[Zheng et al.](https://arxiv.org/html/2503.06412)은 실제 발사형 net의 협력 포획을 보여주므로
“미래 net을 고려한다”는 주장에는 강한 기준선이다. 그렇다고 우리의 반응형 공격자와
학습된 이종 조향 질문까지 자동으로 해결한 것은 아니다.
[최소비용 reach-avoid RL](https://arxiv.org/abs/2605.11975)도 회피할 논문이 아니라, 전환 연구가 커졌을 때 적용·비교할
방법이다.

**주제 선정 규칙:** 시작 시점에 한 문장 질문, 이미 있는 세계/코드, 두세 개의 직접 대조군,
성공과 실패를 모두 판독할 그림이 떠오르면 착수한다. 처음부터 “아직 아무도 건드리지 않은
여섯 요소의 교집합”이나 전체 물리 검증 패키지를 요구하지 않는다. 논문이 자라며 필요한
실험이 늘어나는 것은 허용하지만, 새 요구를 추가할 때마다 원래 질문을 더 잘 답하는지
판정한다.

---

## 0. 장기 확장 가설 — 첫 소재의 필수조건 아님

### 0.1 주 질문

> **적응형 공격기가 방어팀의 기동과 effector 준비 상태에 반응하는 교전에서,
> 저부수피해를 목표로 하지만 지연·단발·소모성인 fired net과, 별도 terminal effect를
> 내지만 플랫폼 손실·비용·교전규칙
> 제약을 갖는 kinetic effector 사이의 결정을 언제까지 미뤘다가 어느 mode로 commit해야,
> 사전 고정한 자산보호와 안전 기준을 만족하는 최저 달성비용 요격이 가능한가? 비발사 협력기의
> 기동은 그 선택권과 mode 전환경계를 얼마나 넓히는가?**

핵심은 “net이 싼가, kinetic이 싼가”라는 정적 선택이 아니다. 두 효과기는 성공에 유리한
상대 기하가 다르고, 방어팀과 공격기의 기동이 그 기하를 계속 바꾼다. net을 기다리는 동안
kinetic의 안전한 요격 창이 닫힐 수 있고, 너무 일찍 kinetic에 commit하면 더 낮은 비용의
clean capture 기회를 버린다. 따라서 연구 대상은 **서로 다른 물리적 launch set을 기동으로
보존하면서 공격기의 반응을 관측한 뒤 비가역 effector 결정을 내리는 recourse 문제**다.

### 0.2 권장 논문 spine

논문의 중심은 다음 세 문장으로 고정한다.

1. **Mode physics:** fired net과 kinetic intercept는 서로 다른 접근 궤적·시간지연·안전
   경계를 요구한다. 표적–방어자 기동에 따라 어느 mode가 유리한지가 뒤집히는
   **mode-rank reversal**이 실제 물리에서 생기는지가 첫 검증 대상이다.
2. **Deferred commitment:** 공격기의 반응을 뒤늦게 식별할 수 있을 때, 두 mode를 모두
   살려두는 기동은 동일한 정보·제어·fallback·계산 예산을 가진 사전 고정 doctrine보다
   넓은 **certified strict recourse region**과 낮은 달성비용을 가질 수 있다.
3. **Heterogeneous cooperation:** limiter의 경로 조형은 net 기회만 만드는 것이 아니라
   kinetic fallback의 마지막 안전시점도 보존한다. 학습은 이 물리적 선택가치를 회수하는
   수단이다.

이 세 문장은 모두 가설이다. 현 결과가 이미 지지하는 결론이 아니다.

### 0.3 논문에서 새롭다고 주장하지 않을 것

- RL이 장기 보상 또는 WAIT의 미래가치를 고려한다.
- 다수 pursuer가 표적을 포위·유도하여 capture opportunity를 만든다.
- MAPPO, PFSP, self-play, PSRO, opponent pool 또는 policy library를 사용한다.
- heterogeneous role 또는 high-level mode selector를 둔다.
- net launch envelope, dwell condition, projectile/net dynamics를 모델링한다.
- 여러 효과기 중 비용이 낮은 것을 고른다.
- collateral risk와 kill probability를 함께 최적화한다.
- fresh learned best response로 exploitability를 평가한다.

이 항목들은 선행연구가 이미 점유했다. 본 연구의 기여는 알고리즘 부품이 아니라 다음
인과 사슬이어야 한다.

```text
mode별 실제 물리와 교전규칙
  → 상태·기동에 따라 달라지는 net / kinetic launch-success set
  → 결정을 미룰 때만 남는 effector 선택권
  → adaptive attacker가 그 선택권을 닫거나 미끼로 이용하는 현상
  → limiter–shooter–kinetic team이 선택권을 보존하는 기동
  → 사전 고정한 보호·안전 문턱에서의 최소 달성비용 및 capability frontier
```

### 0.4 한 줄 contribution 후보

> **We identify physics-induced mode-rank reversals and certified strict recourse regions in a
> counter-UAS game, and quantify when heterogeneous shaping preserves the option to
> choose between a delayed consumable net and a safety-constrained kinetic interceptor
> after informative observations of an adaptive intruder.**

“optimal”은 저차원에서 정확해를 계산한 부분에만 쓴다. 고차원 학습 결과는 독립 selection
자료에서 후보를 고정한 뒤 “attained cost of the preregistered selected policy on the finite
evaluation suite”로 제한한다.

### 0.5 현 연구와 후속 Q1의 관계

현 `B2 → stop rule → 조건부 3-arm MAPPO`는 계속 수행할 가치가 있다. 그것은 다음을
확인하는 **foundation experiment**다.

- 현 축소차수 세계에서 학습이 가능한가.
- limiter 조향의 양성 신호가 실제 policy에 의해 회수되는가.
- 병렬 환경에서 우리 서버의 throughput과 안정성이 어느 정도인가.

그러나 B0 v3는 high-level mode 선택을 금지하고 net 실패 뒤 scripted PN fallback으로
강제 전환한다. 따라서 그 결과를 r3.1의 minimum-cost mode-switching 증거로 재해석하지 않는다.

---

## 1. 왜 r2를 폐기하는가

### 1.1 사용자 지적에 대한 판정

사용자 지적은 맞다. 할인 누적수익을 최적화하는 RL은 보상이 제대로 연결돼 있다면 현재
FIRE 보상과 WAIT 뒤의 미래 보상을 함께 반영한다. `Q_F(s)`와 `Q_W(s)`를 나누는 표기는
정책 진단에는 유용하지만 그 자체로 연구 신규성이 아니다.

용어만 바로잡으면, 미래가치의 시간 가중을 정하는 것은 보통 **학습률 `α`가 아니라 할인율
`γ`와 return/termination 설계**다. 학습률은 optimizer update의 크기다.

더 직접적으로 SD2AC는 실제 미사일 비행을 포함한 UCAV 환경에서 `hold fire / launch`를
학습한다. Catch Planner는 포획 시간과 terminal state를 함께 정하는 planning-with-decision
문제를 푼다. 따라서 “발사 시점까지 RL로 학습한다”도 단독 기여가 될 수 없다.

### 1.2 Zheng et al.에 대한 정정

Zheng et al.을 “현재 상태에서 언제 net을 쏠지만 판단한다”고 축소하면 안 된다. 원문은
다기체 circular formation으로 표적을 capture zone에 충분히 오래 유지하고, 네 corner node의
미래 flying envelope와 0.5 s dwell을 사용해 발사를 결정한다. 즉 **협력 formation이 기회를
만들고 미래 net 운동을 이용해 발사를 결정하는 폐루프 system**이다.

우리와 남는 차이는 “기회 생성 대 기회 판정”이 아니다. Zheng에는 확인한 범위에서 다음
질문이 없다.

- 서로 다른 두 효과기 중 하나를 뒤늦게 고르는 recourse
- kinetic option이 no-kill boundary에서 사라지는 switch deadline
- mode별 물리를 이용해 방어 정책을 역으로 유도하는 adaptive attacker
- 사전 고정한 보호·안전 문턱에서의 out-of-sample attained engagement cost
- non-shooting shaper가 두 effector option을 보존한 인과효과

### 1.3 r2 요소의 처분

| r2 요소 | r3.1 처분 | 이유 |
|---|---|---|
| `Q_F` 대 `Q_W` | 보조 진단으로만 유지 | RL의 일반 성질이며 SD2AC가 명시적 launch/hold를 다룸 |
| team-assisted stopping | 용어 폐기 | optimal stopping 자체가 신규성이 아님 |
| future opportunity creation | 일반 주장 폐기 | Zheng, Gavin & Bronz, tactical shaping 문헌이 점유 |
| PFSP adaptive opponent | 평가·훈련 도구 | Gavin, AgilePE 등이 점유 |
| response library | 구현 수단 | PSRO, NeuPL, Conflux-PSRO, HCSP 등이 점유 |
| exploitability | 필수 stress test | approximate fresh-BR 평가는 기존 방법 |
| behavior analysis | 결과 해석 층 | 예쁜 궤적은 contribution이 아님 |
| physical frontier | **승격** | mode별 launch set·recourse·cost를 분해할 때만 중심 가능 |
| heterogeneous net/kinetic | **승격** | role 이름이 아니라 서로 다른 물리와 소모·안전 제약이 실제로 작동해야 함 |

---

## 2. 문헌 경계: 무엇이 이미 점유됐는가

### 2.1 net capture 및 pursuit

| 문헌 | 이미 한 것 | 이 연구에 남긴 경계 |
|---|---|---|
| **Zheng et al. 2025** | vision, distributed estimation, circular formation, MPC, 실제 net gun, four-corner future envelope, dwell, 실기 포획 | net과 kinetic 사이의 adaptive recourse·비용 최적화는 다루지 않음 |
| **Gavin & Bronz 2026** | 3v1 homogeneous net-carrier, CTBR, MAPPO+PFSP, agile evader, blocking·encirclement·후속 포획기회 대기 | net이 기체 하부의 rigid disk라 FIRE·deploy·spent·ammo가 없음 |
| **Huh et al. 2026** | limited FOV, 6DOF, MAPPO, net-gun engagement envelope와 capturability reward | 확인한 모델은 geometric capture condition이며 dual-effector recourse가 아님 |
| **Liu et al. 2025** | spring–damper tethered net, multibody dynamics, vision, MAPPO | tethered multi-UAV net 단일 mechanism |
| **Han et al. 2026** | stow→deployment→collision→entanglement 전체 fired-net dynamics와 field validation | 주 분석 target은 정지 가정; adaptive target과 mode decision은 없음 |
| **Collision Cone JGCD 2020** | 다수 defense UAV가 운반하는 net과 intruder swarm의 collision-cone guidance | 발사형 소모 net과 heterogeneous effector recourse가 아님 |

따라서 `MARL + net`, `adaptive evader`, `herding`, `launch envelope`, `net dynamics` 중 어느
하나도 단독 novelty로 쓰지 않는다.

### 2.2 발사·탄약·이종 역할

- **SD2AC (2025)**는 missile dynamics와 stochastic `hold/launch` policy를 함께 둔다.
- **Selmonaj et al. (2023)**는 서로 다른 기동·무장을 가진 aircraft, 잔탄 관측,
  cannon/rocket action과 league/fictitious self-play를 결합한다.
- Kouzeghar et al., PRTDA, TSSAC 계열은 scout/pursuer 또는 decoy/detector/strike와 같은
  이종·순차 역할을 이미 다룬다.

따라서 “탄약을 본다”, “발사 결정을 배운다”, “역할이 다르다”도 부족하다. mode에 따라
**성공기하와 저수준 기동 자체가 달라지고**, 선택을 미룰 때의 recourse가 실제 mission
cost를 바꾼다는 것을 보여야 한다.

### 2.3 policy population과 adaptive evaluation

PSRO는 policy population의 approximate best response와 empirical meta-game을 반복한다.
NeuPL과 Simplex-NeuPL은 conditional population과 mixture에 대한 best response를 다룬다.
OPRE와 Conflux-PSRO는 opponent에 따른 strategic response 또는 state-level routing을
다룬다. VolleyBots는 frozen policy에 새 RL best response를 학습해 approximate
exploitability를 평가한다.

그러므로 다음은 method choice이지 contribution이 아니다.

- scripted attacker와 PFSP attacker를 섞는 것
- cooperation을 하나의 option으로 policy library에 넣는 것
- online router가 mode policy를 고르는 것
- fresh attacker를 학습해 취약점을 찾는 것

단일 stochastic/recurrent policy가 behavioral mixture를 내부적으로 표현할 수도 있다.
“여러 policy 파일이 단일 policy보다 본질적으로 우월하다”는 주장도 금지한다.

### 2.4 최소비용 effector 선택과 WTA

단순한 minimum-cost response selection은 이미 붐비는 영역이다.

- dynamic weapon–target assignment는 시간별 feasibility, ammunition, launch capacity와
  kill probability를 두고 자원을 배분한다.
- counter-UAS resource-allocation 연구는 physics-based missile simulation과 ILP/PPO를
  비교한다.
- sensor–weapon–target assignment는 다목적 Pareto optimization을 사용한다.
- effect-based WTA는 원하는 효과, overkill과 collateral damage를 함께 최적화한다.
- Arslan et al.의 naval air-defense planning은 함정 기동과 sensor/weapon scheduling을
  함께 최적화한다.
- Yao et al. (2026)은 두 종류 탄약의 상태·시간 순서·순차 결정을 Dueling DQN으로 다룬다.
- stochastic minimum-cost reach-avoid RL은 확률적 reach-avoid 문턱 아래 누적비용 최소화를
  직접 정식화한다.
- 최신 C-UAS decision architecture는 jamming, kinetic, combined response 후보의 success와
  collateral cost를 forward-evaluate한다.
- hard/soft defense 및 soft/hard damage mode의 비용·자원 frontier도 별도 문헌이 있다.

기존 WTA를 “고정된 `p_success`와 `cost` 표에서 가장 싼 weapon을 고른다”로 과도하게
일반화해서는 안 된다. 다만 이 프로젝트가 파고들 틈은 분명하다.

> **두 effector의 effectiveness가 사전에 주어진 표가 아니라, 동일한 adaptive target과
> defender guidance가 만들어내는 mode-specific trajectory의 결과이며, 선택을 미루는 동안
> launch set과 fallback deadline이 함께 변하는 continuous closed-loop engagement.**

### 2.5 provisional gap

제한 검색에서 다음 여섯 요소의 교집합을 직접 검증한 UAV/C-UAS 원문은 찾지 못했다.
그러나 이 조합 자체는 contribution이 아니라 **검색 경계**다.

1. 발사 후에도 표적이 반응하는 projectile net
2. 물리적으로 구별되는 kinetic interceptor
3. net 소모·kinetic attrition·no-kill rule을 포함한 hybrid state
4. mode commit을 미룬 뒤 관측에 따라 선택하는 recourse
5. non-shooting teammate가 두 mode의 launch set을 보존하는 기동
6. adaptive/fresh-response attacker 아래의 risk-constrained out-of-sample attained cost

따라서 headline novelty 후보는 다음처럼 더 좁힌다.

> **동일 표적–방어자 기동이 net과 kinetic의 성공 순위를 내생적으로 뒤집고, 그 분기에 관한
> 정보가 뒤늦게 도착하기 때문에 사전 doctrine으로는 얻을 수 없는 certified strict
> recourse region이
> 생긴다는 것을 source-locked physics에서 보이고 검증한다.**

이 문장의 허용 강도는 아직 “검증할 가설”까지다. mode-rank reversal과 strict region 중
하나라도 G2–G3에서 사라지면 신규성 spine을 철회한다.

---

## 3. 제안하는 임무 세계

### 3.1 주체와 효과기

권장 primary 구성은 다음과 같다.

- **Attacker 1대:** 보호 자산 침투를 목표로 하며 방어기 기동·FIRE·mode cue에 반응한다.
- **Limiter `n_L`대:** 직접 효과기를 쓰지 않고 표적 경로와 time-to-go를 바꾼다.
- **Net shooter 1대:** 이동형 platform, fired net 1발, 재장전 없음.
- **Kinetic interceptor 1대:** 별도 platform. 권장 시작점은 현 코드와 연결되는
  **sacrificial contact interceptor** 한 종류다. projectile gun과 ramming을 섞지 않는다.

kinetic mechanism은 G0에서 한 종류로 확정해야 한다. 이를 확정하지 않고 “kinetic”을
추상 label로 두면 비용·안전·성공기하를 검증할 수 없다.

### 3.2 mode와 비가역 전이

```text
TRACK / SHAPE / OBSERVE
    ├── NET_COMMIT ──> NET_DEPLOYING ──> NET_ACTIVE ──> CAPTURE
    │                                      └──────────> NET_SPENT
    │                                                       └──> KINETIC_COMMIT
    └── KINETIC_COMMIT ────────────────────────────> SAFE_KINETIC_NEUTRALIZATION

모든 경로 ──> PENETRATION / UNSAFE_CONTACT / TIMEOUT / UNAUTHORIZED_PLATFORM_LOSS
```

필수 규칙은 다음과 같다.

1. `NET_COMMIT`은 탄약 1발을 즉시 소모한다.
2. `NET_DEPLOYING`과 `NET_ACTIVE` 동안 모든 기체와 net을 계속 적분한다.
3. 표적은 FIRE를 관측할 수 있는지, 어느 지연으로 관측하는지 계약에 명시한다.
4. `NET_SPENT` 뒤 kinetic으로 전환할 수 있으나, 남은 시간·거리·교전규칙이 허용할 때만
   가능하다.
5. kinetic commit 뒤 net으로 돌아가는 경로는 primary에서 금지한다.
6. net과 kinetic의 동시 terminal commit은 primary에서 금지하여 switching effect를
   식별한다. 동시 발사는 upper-bound secondary arm으로만 둔다.
7. same-tick capture, contact, protected-zone penetration의 precedence를 봉인한다.
8. platform loss와 cartridge loss를 inventory state에 실제 반영한다.

### 3.3 사라지는 fallback

kinetic의 안전한 실행 가능 여유를 개념적으로 다음처럼 둔다.

\[
M_K(s)=T_{\mathrm{ROE}}(s)-T_{\mathrm{int}}^K(s),
\]

여기서 `T_ROE`는 표적이 kinetic 금지구역에 들어가기까지 남은 시간이고,
`T_int^K`는 현재 상태에서 kinetic interceptor가 안전한 접촉을 만들기까지 필요한 시간이다.
`M_K(s)≤0`이면 kinetic option은 닫힌다.

net mode에는 별도의 margin이 있다.

\[
M_N(s)=T_{\mathrm{pen}}(s)-
\left(T_{\mathrm{align}}^N(s)+\tau_{\mathrm{deploy}}+T_{\mathrm{capture}}^N(s)\right).
\]

두 식은 최종 모델이 아니라 reduced-model 설계 좌표다. 중요한 점은 limiter가 표적의 경로와
속도를 바꾸어 `M_N`과 `M_K`를 서로 다르게 움직일 수 있다는 것이다. 최저비용 policy는
net margin만 키워서는 안 된다. 공격기의 반응을 더 관측하는 동안 kinetic option이 닫히지
않게 해야 한다.

### 3.4 deferred commitment와 fallback을 구분한다

- **Deferred commitment:** FIRE 전에 기동·관측을 계속하며 net/kinetic 두 선택을 살려둔 뒤
  mode를 고른다. r3.1의 분석 중심이다.
- **Fallback:** net에 이미 commit한 뒤 miss/spent가 확인되면 kinetic으로 전환한다. 중요한
  시스템 결과지만 recourse보다 선택권이 작다.
- **Static doctrine:** episode 시작 또는 최초 탐지 때 net-only, kinetic-only, net-first를
  고정한다. primary 대조군이다.

“mode switching”이라는 말로 이 세 가지를 섞지 않는다.

### 3.5 단일 교전과 finite-raid cost

- **E1 single-intruder:** launch set, switch deadline, adaptive baiting과 인과기전을 식별하는
  main science subcase다. 여기서는 “minimum engagement cost”라고 부른다.
- **E2 sequential finite raid:** net cartridge와 kinetic platform inventory가 다음 침입자까지
  이어지는 평가다. 여기서는 “raid-level cumulative resource/attrition cost”와
  “raid-level cost exchange”까지만 허용한다.

E1에서 episode가 끝날 때 inventory가 초기화되면 net 1발의 희소성이 전술 결과 외에는
장기 비용을 만들지 않는다. 따라서 E2 없이 “sustainable economics”나 “inventory doctrine”을
주장하지 않는다. 2–5대 순차 raid만으로 lifecycle economics도 주장하지 않는다. 그 주장은
위협 도착과 horizon, reload, repair/replacement, sortie turnaround, replenishment가 검증된
별도 운용모델을 요구한다. Q1 system paper에는 E2를 선택적으로 권장하되 simultaneous
swarm까지 한 번에 넣지 않는다. E2는 threat 수·도착 간격·type 분포, 교전 사이 reset과
repositioning, 공격기가 방어 inventory를 관측하는지를 사전에 봉인한다.

---

## 4. 형식적 문제와 주 추정량

### 4.1 평가 scenario

평가 scenario cell을

\[
z=(c_z,\mathcal P_z(\lambda),\mathcal D_0,\mathcal D_\xi)
\in\Omega_{\mathrm{eval}},
\qquad
\lambda=(e,\vartheta).
\]

로 둔다. `c_z`는 방어자에게 공개되는 scenario context, `e`는 defender state·mode에 반응하는
frozen attacker policy/type, `ϑ`는 airframe·net·kinetic parameter다. cell마다 latent
configuration `λ`의 sealed prior `P_z(λ)`를 둔다. `D_0`와 `D_ξ`는 초기상태와 process·sensor·
attacker-policy randomization을 포함한 disturbance seed의 분포다. 공개 context `c_z`는
defender가 사용할 prior를 유일하게 정한다. 방어자에게 숨길 variation은 별도 비공개 cell
ID가 아니라 `λ` 안에 넣는다.

`P_prot(π,z)`와 모든 기대값은 `λ∼P_z(λ)`, `s_0∼D_0`, `ξ∼D_ξ`를 적분한다.
`Ω_eval`은 학습과 격리한 유한 공통 cell 집합이며 robust/minimum/frontier는 이 집합에
한정한다. N/K paired counterfactual에서는 같은 exogenous `(λ,ξ)`를 고정한다. 실제 response
trajectory와 branch는 joint action 뒤 생성되는 post-treatment 결과이므로 conditioning
label로 쓰지 않는다.

방어자가 시간 `t`까지 사용할 수 있는 정보를

\[
\mathcal F_t=\sigma(o_0,a_0,o_1,\ldots,a_{t-1},o_t)
\]

로 두고 belief `b_t=P_z(λ\mid\mathcal F_t,c_z)`를 policy state로 사용할 수 있다. attacker
policy ID와 실제 plant parameter는 센서로 식별 가능하다고 source-lock한 성분 외에는 직접
주지 않는다. history `h_t`와 양립 가능한 평가 cell은

\[
\Omega(h_t,c_z)
=\{z'\in\Omega_{\mathrm{eval}}:
c_{z'}=c_z,\ h_t\in\operatorname{supp}P_{z'}(H_t)\}
\]

로 두고 이를 `Ω(x_t^I)`로 줄여 쓴다. 후기 launch value는 모든 `Ω_eval`에 무조건
condition하지 않고 이 support의
posterior risk만 사용한다. primary가 Bayesian prior 대신 ambiguity set을 쓸 경우에는
posterior update와 risk functional을 별도 계약으로 전면 교체하며 두 해석을 섞지 않는다.
최초 탐지·초기 doctrine 선택 시점을 `t_0`로 두고 episode horizon/timeout `T_H`도 고정한다.

deferred commitment의 strict gain에는 두 조건이 필요하다.

1. `t_0` 이후 관측이 mode 선택에 관한 정보를 실제로 늘린다.
2. 가능한 `λ`가 서로 다른 reachable information state를 만들고, 그 상태 사이에서
   net과 kinetic의 constraint-feasible cost 순위가 달라진다.

후기 관측이 없거나 모든 branch에서 한 mode가 지배하면 recourse gain은 사라져야 한다. 이것을
양성 결과가 아니라 falsification control로 둔다.

### 4.2 보호·안전 제약

terminal outcome을 단순 사건의 합집합으로 세지 않는다. 다음 mutually exclusive first-hit
outcome을 정의한다.

\[
Y\in\{N_{\mathrm{safe}},K_{\mathrm{safe}},B,
K_{\mathrm{illegal}},C_{\mathrm{unsafe}},L_{\mathrm{unauth}},
O_{\mathrm{timeout}}\}.
\]

`N_safe`와 `K_safe`는 breach·illegal effect·unsafe collision보다 먼저 발생한 안전한 net
capture와 kinetic neutralization이다. `B`는 protected boundary 침범, `L_unauth`는
limiter/shooter crash 또는 허가되지 않은 interceptor loss다. `K_safe`에 계약상 수반되는
의도된 sacrificial interceptor loss는 `L_unauth`와 구분하되 resource cost에는 포함한다.
same-tick 사건의 우선순위와 terminal ordering은 world contract에서 봉인한다. 따라서 breach
뒤의 neutralization을 보호 성공으로 다시 세지 않는다.

방어 policy `π`에 대해

\[
P_{\mathrm{prot}}(\pi,z)
=P(Y\in\{N_{\mathrm{safe}},K_{\mathrm{safe}}\}\mid\pi,z),
\]

\[
P_{\mathrm{unsafe}}(\pi,z)
=P(Y\in\{K_{\mathrm{illegal}},C_{\mathrm{unsafe}},
L_{\mathrm{unauth}}\}\mid\pi,z)
\]

로 둔다. population-level primary feasibility는

\[
\min_{z\in\Omega_{\mathrm{eval}}}
P_{\mathrm{prot}}(\pi,z)\ge\alpha,
\qquad
\max_{z\in\Omega_{\mathrm{eval}}}
P_{\mathrm{unsafe}}(\pi,z)\le\beta
\]

다. 실패비용을 큰 숫자로 reward에 넣어 성공률과 맞바꾸지 않는다. 자산보호와 안전은 먼저
constraint로 통과시키고 그 안에서 비용을 비교한다.

유한 rollout에서 이 식의 point estimate만으로 feasible을 선언하지 않는다. sealed cell과
최종 policy 전체에 대해 사전 선택한 동시 신뢰절차로 `P_prot`의 LCB와 `P_unsafe`의 UCB를
구하고,

\[
\min_z L^{\mathrm{sim}}_{\mathrm{prot}}(\pi,z)\ge\alpha,
\qquad
\max_z U^{\mathrm{sim}}_{\mathrm{unsafe}}(\pi,z)\le\beta
\]

일 때만 **certified on the finite evaluation suite**라고 쓴다. 문턱을 가로지르는 cell은
infeasible로 단정하지 않고 **unresolved**로 둔다. 반대로 어떤 sealed cell에서
`U_prot^sim<α` 또는 `L_unsafe^sim>β`이면 **certified failed**다. 이는 연속 상태공간 전체의
보장이 아니다.

### 4.3 비용 계약

한 episode 또는 raid의 비용을

\[
C_{\boldsymbol c}
=c_N n_N+c_K^{\mathrm{op}} n_K
+c_{P,K}^{\mathrm{sac}}n_{K,\mathrm{sac}}
+\sum_{r\in\{L,S,K\}}c_{P,r}^{\mathrm{unauth}}n_{r,\mathrm{unauth}}
+c_A n_{\mathrm{activated}}+c_T T+c_E E_{\mathrm{maneuver}}
\]

로 둔다. 최소 계약은 다음과 같다.

- `n_N`: 발사한 net cartridge 수
- `n_K`: kinetic commit 수
- `n_{K,\mathrm{sac}}`: 허가된 sacrificial kinetic loss 수
- `n_{r,\mathrm{unauth}}`: limiter `L`, net shooter `S`, kinetic interceptor `K`별 비의도·비허가 손실 수
- `n_activated`: 비교하는 force package에서 실제 투입한 플랫폼 수
- `T`: 교전시간 또는 sortie 점유시간
- `E_maneuver`: 선택적 에너지 proxy

`c_K^op`는 kinetic launch·운용비만 포함한다. sacrificial interceptor에서
`n_{K,\mathrm{sac}}=n_K`가 결정적이면 kinetic 운용비와 허가된 kinetic replacement만
`(c_K^{op}+c_{P,K}^{sac})n_K`로 합칠 수 있다. unauthorized limiter/shooter/interceptor loss 항은
그 뒤에도 별도로 남긴다. 총 platform loss는
`n_{K,sac}+\sum_r n_{r,unauth}`로 따로 보고한다. 같은 자산을 쓰는 matched comparison에서는
`c_A n_activated`를 고정 sunk term으로 생략할 수 있다. 자산 수가 다른 baseline을 비교할
때는 activation/availability cost를 반드시 포함한다.

먼저 다음 outcome–resource vector의 비지배 Pareto set을 보고한다.

\[
y(\pi)=\left(
1-P_{\mathrm{prot}},\
P_{\mathrm{unsafe}},\
\mathbb E[n_N],\
\mathbb E[n_K],\
\mathbb E[n_{K,\mathrm{sac}}],\
\mathbb E[\sum_r n_{r,\mathrm{unauth}}],\
\mathbb E[n_{\mathrm{activated}}],\
\mathbb E[T]
\right).
\]

그 뒤 `c_N=1`로 정규화한 비용비 벡터

\[
\boldsymbol\rho=
\left(c_K^{\mathrm{op}},c_{P,K}^{\mathrm{sac}},
\boldsymbol c_P^{\mathrm{unauth}},c_A,c_T,c_E\right)/c_N
\]

의 범위를 sweep한다. 검증된 조달·운용 자료가 없으면 달러값으로 “최저비용”을 주장하지
않는다. 비용 가중치 하나를 임의로 고른 뒤 그 결과만 보고하지 않고, mode 순위가 바뀌는
break-even surface를 제시한다.

### 4.4 out-of-sample attained cost

policy 선택과 성능 확인을 분리한다. 개발·selection 자료 `D_dev,D_sel`에서 policy class
`Π`의 최종 후보 하나와 모든 tie-break를 고정하고,

\[
\pi_{\Pi}^{\mathrm{sel}}
=\operatorname{Select}(\Pi;D_{\mathrm{dev}},D_{\mathrm{sel}})
\]

로 둔다. untouched confirmation 자료 `D_conf`에서는 후보를 다시 고르지 않고

\[
\widehat C_{\Pi}^{\mathrm{att}}(\alpha,\beta;\boldsymbol\rho)
=\max_{z\in\Omega_{\mathrm{eval}}}
\widehat{\mathbb E}_{D_{\mathrm{conf}}}[C_{\boldsymbol c}
\mid\pi_{\Pi}^{\mathrm{sel}},z]
\]

를 추정한다. §4.2의 동시 신뢰경계를 통과할 때만 비용값을 보고한다. 통과한 policy가 없으면
비용을 외삽하지 않고 **no certified feasible candidate**라고 쓴다. 모든 후보가 certified
failed이면 declared candidate set에서의 failure, 하나라도 문턱을 가로지르면 **unresolved**다.
여러 최종 후보를 confirmation에서 다시 최소화해야 한다면 별도 selection split 또는 명시적
selection-adjusted simultaneous inference를 사용한다.

고차원 결과는 `attained cost of the preregistered selected policy`라고 부른다. 저차원 DP/HJ
또는 exhaustive solve가 완결된 경우에만 `optimal`과 별표를 허용한다. low-D oracle에서의
구조적 recourse value와 learned policy의 회수율을 별도 결과로 보고한다.

### 4.5 mode별 launch-success set

post-commit 결과는 mode 이름만으로 정해지지 않는다. mode `m∈{N,K}`의 matched continuation
policy class를 `Γ_m`, 봉인된 horizon을 `T_H`라 한다. 정보상태
`x^I=(s,b,c_z)`에서 oracle
launch-success set을

\[
\mathcal L_{m,\Gamma}^{\mathrm{oracle}}(\alpha,\beta)
=\left\{x^I:\exists\gamma\in\Gamma_m\
\begin{array}{l}
\min_{z\in\Omega(x^I)}
P_{\mathrm{prot}}(\gamma\mid x^I,\operatorname{COMMIT}(m),z)\ge\alpha,\\
\max_{z\in\Omega(x^I)}
P_{\mathrm{unsafe}}(\gamma\mid x^I,\operatorname{COMMIT}(m),z)\le\beta
\end{array}
\right\}
\]

로 둔다. 각 확률은 해당 history의 posterior `b_t`와 남은 disturbance를 적분한다.
**저차원 1차 경로는 유한 격자·유한 horizon·명시적 전이확률의 exact solve**다.
“exact”는 선언한 이산 toy 모형과 정책군 안에서 전수 계산했다는 뜻이며 연속 물리의
오차 인증이 아니다. 저차원에서 exact solve가 없으면 sound inner set `L_m^in`과 fixed-side
nonmembership를 판단할 sound outer set `L_m^out`을 따로 계산한다. high-D frozen continuation
controller `\hat\gamma_m`의 attained set은

\[
\widehat{\mathcal L}_{m,\hat\gamma_m}^{\mathrm{att}}
=\{x^I:\hat\gamma_m\text{가 §4.2 simultaneous bounds를 통과}\}
\]

로 표기한다. 한 controller의 실패는 `x^I\notin L_{m,\Gamma}^{oracle}`를 뜻하지 않는다.

- net set은 비행·전개·충돌·포획과 post-FIRE attacker response를 포함한다.
- kinetic set은 interceptor dynamics, effect model, no-kill rule을 포함한다.
- `L_N∩L_K`와 `(L_N∪L_K)^c`를 그릴 때 oracle/inner/outer/attained 중 어느 객체인지
  첨자로 명시한다.

pre-commit reach-avoid basin도 같은 층을 유지한다. oracle basin은 `Γ_pre`와
`L_{m,\Gamma}^{oracle}`에 대한 최적화로, selected policy basin은 frozen policy의 rollout
동시 신뢰경계로 계산한다. reach-avoid 성공은 §4.2의 first-hit ordering을 사용한다.
기구적으로 가능한 집합, certified inner/outer approximation, 유한 rollout의 attained set을
한 그림에서 같은 색으로 섞지 않는다.

### 4.6 fixed commitment와 recourse

`Π_fixed`와 `Π_rec`를 권한·정보·계산이 맞는 policy class로 정의한다.

- **Fixed doctrine `Π_fixed`:** `t_0`의 `\mathcal F_{t_0}`만으로 완전한 doctrine `d`를
  고른다. 이후 기동과 발사시점은 관측에 반응할 수 있지만, 최초 effector mode는 후기 branch
  증거로 바꾸지 못한다. 가장 강한 사전 contingency인
  `net-first → confirmed failure 시 kinetic`도 `d`의 한 후보로 포함한다.
- **Deferred recourse `Π_rec`:** `WAIT/SHAPE` 동안 두 최초 mode의 실행 가능성을 보존하고,
  world contract가 정한 deadline 전 admissible stopping time `τ`에서
  `\mathcal F_τ`-measurable selector
  `g_τ:\mathcal F_τ→{N,K}`로 최초 mode를 정한다.

두 class는 같은 observation, low-level controller family, post-commit fallback 권한,
parameter/inference budget, training/search budget을 쓴다. `Π_rec`는 모든 fixed doctrine을
정확히 모사하는 embedding을 포함하고, 차이는 **최초 commit 전 후기 정보로 mode를 바꿀
권한**뿐이다. 논리 구조는 다음과 같다.

~~~text
fixed:    ∃ d measurable at F_t0, ∃ π^d : chance constraints over latent λ
recourse: ∃ stopping time τ, ∃ F_τ-measurable g_τ, ∃ π : same constraints over latent λ
~~~

초기 정보상태 `x_0^I=(s_0,b_0)`에서 각 class의 policy 하나가 모든 sealed cell의 확률
제약을 만족하는
policy-class winning set을

\[
\mathcal B_q^{\mathrm{oracle},\alpha,\beta}
=\{x_0^I:\exists\pi\in\Pi_q\ \text{s.t. §4.2 constraints hold for every }z\},
\quad q\in\{\mathrm{fixed},\mathrm{rec}\}
\]

로 둔다. 이 객체는 low-D exact solve 또는 정책군 전체에 대한 certified bound가 있을 때만
주장한다. latent `λ`를 알고 branch마다 유리한 mode를 고른 statewise union은
`B_fixed^oracle`가 아니다. matched embedding이 성립하면

\[
\mathcal B_{\mathrm{fixed}}^{\mathrm{oracle}}
\subseteq
\mathcal B_{\mathrm{rec}}^{\mathrm{oracle}}
\]

이다. **기본 계산 경로는 작은 유한 상태·행동·관측·horizon의 정책군을
DP/전수열거로 푸는 것**이다. 제약 `P_prot≥α`와 `P_unsafe≤β`를 큰 비용벌점으로
바꾸지 않고 가능한 확률–비용 벡터를 보존해 판정한다. 전이표·관측확률·정책의
무작위화 허용 여부·경계 처리까지 계약한 유한 모형에서만 “exact”라고 쓴다.
연속 F1/F2 세계로의 보증은 이 결과에서 나오지 않는다. 이 finite exact 경로가
불가능해진 저차원 문제에 한해서 다음 sound relation을 검토한다.

\[
\mathcal B_{\mathrm{rec}}^{\mathrm{in}}
\subseteq \mathcal B_{\mathrm{rec}}^{\mathrm{oracle}},
\qquad
\mathcal B_{\mathrm{fixed}}^{\mathrm{oracle}}
\subseteq \mathcal B_{\mathrm{fixed}}^{\mathrm{out}}.
\]

이때 strict inclusion의 certified witness는

\[
\mathcal S_B^{\mathrm{cert}}
:=\mathcal B_{\mathrm{rec}}^{\mathrm{in}}
\setminus
\mathcal B_{\mathrm{fixed}}^{\mathrm{out}}
\]

으로 둔다. recourse inner set과 fixed outer set 사이의 차이만 fixed policy class 전체의
비가능성을 증명한다. search는 recourse feasibility witness를 찾을 수 있지만 fixed class의
nonmembership는 증명하지 못한다.

high-D에서는 class winning set 대신 frozen selected policy의 attained basin

\[
\widehat{\mathcal B}_{\pi_q^{\mathrm{sel}}}^{\mathrm{att}}
:=\{x_0^I:\pi_q^{\mathrm{sel}}\text{가 §4.2 simultaneous bounds를 통과}\}
\]

을 보고한다. `B_{\pi_{\mathrm{rec}}}^{att}\setminus
B_{\pi_{\mathrm{fixed}}}^{att}`는 **attained-policy basin difference**이며 strict
recourse-only region이라고 부르지 않는다. 한 fixed policy의 실패는 fixed class 전체의
불가능성이 아니다.

strict class inclusion에는 `t_0` 뒤 informative observation과 branch-dependent mode ranking이
모두 필요하다. 단순 포함관계는 generic recourse lemma다. headline은 source-locked net/kinetic
physics와 adaptive target–defender coupling 때문에 certified strict witness와
mode-rank reversal이 실제 C-UAS subcase에서 생긴다는 결과다.

### 4.7 primary estimands

#### A. Mode-rank reversal and structural recourse gain

같은 post-commit class `Γ_m`과 같은 `α,β` 문턱 아래, 실제 policy가 접근할 수 있는
reachable information state `x_t^I=(s_t,b_t,c_z)`에서

\[
J_m^{\mathrm{oracle}}(x_t^I)
=\inf_{\gamma\in\Gamma_m:\ \gamma\ \mathrm{feasible}}
\max_{z\in\Omega(x_t^I)}
\mathbb E[C_{\boldsymbol c}\mid x_t^I,\operatorname{COMMIT}(m),\gamma,z]
\]

를 정의한다. high-D attained value `J_{m,\hat\gamma_m}^{att}`는 infimum을 취하지 않고
selection 단계에서 freeze한 `\hat\gamma_m`을 confirmation에서 평가한다. 한 mode만 certified
feasible이면 그 mode가 우선하고, 둘 다 certified feasible이면

\[
\Delta_{NK}^{q}(x_t^I)
=J_N^{q}(x_t^I)-J_K^{q}(x_t^I),
\qquad q\in\{\mathrm{oracle},\mathrm{att}\}
\]

로 비용 순위를 정한다. `t_0` 뒤 reachable한 두 history가 서로 다른 `x_{\tau,1}^I,x_{\tau,2}^I`를
만들고 선호 mode가 `N→K` 또는 `K→N`으로 바뀌면 mode-rank reversal이다. empirical cost
reversal은 두 차이의 simultaneous interval이 서로 반대 부호에 완전히 놓일 때만 certified한다.
feasibility reversal은 한 mode의 certified feasible과 다른 mode의 certified failed가
information state 사이에서 서로 뒤바뀔 때만 센다. unresolved cell은 어느 쪽에도 넣지 않는다.
후기 관측을 policy가 구별할 수 없으면 hindsight-only reversal일 뿐 recourse evidence가 아니다.
N/K counterfactual은 §4.1의 같은 exogenous `(λ,ξ)`를 쓰고 post-commit realized branch에
조건화하지 않는다. oracle과 attained reversal의 사전 고정 측도 또는 비율을 각각
`G_R^oracle,G_R^att`로 쓴다.

\[
G_B^{\mathrm{cert}}
=\mu\!\left(\mathcal S_B^{\mathrm{cert}}\right).
\]

**기본 경로인 finite low-D exact solve**에서는 `S_B^cert` 대신
`B_rec^oracle\setminus B_fixed^oracle`의 측도를 `G_B^{exact,finite}`로 보고한다.
이는 선언한 이산 toy의 T2 결과다. sound inner/outer가 필요한 경우에만
`G_B^cert`를 쓴다. high-D에서는

\[
G_{\mathrm{att},r\setminus f}
=\mu\!\left(
\widehat{\mathcal B}_{\pi_{\mathrm{rec}}^{\mathrm{sel}}}^{\mathrm{att}}
\setminus
\widehat{\mathcal B}_{\pi_{\mathrm{fixed}}^{\mathrm{sel}}}^{\mathrm{att}}
\right)
\]

와 반대 방향 차이를 함께 보고하되 **attained-policy basin difference**라고 부른다.
`G_B^cert`와 합치지 않는다. oracle/certified fixed class가 infeasible이고 recourse만
feasible인 cell은 비용 차이를 무한대로 만들지 않고 structural extensive-margin gain으로
보고한다. selected fixed 후보만 실패한 경우는 attained status 차이일 뿐이다.

#### B. Cost value of deferred commitment

\[
\operatorname{VoDC}_{C}^{\mathrm{att}}(\alpha,\beta;\boldsymbol\rho)
=\widehat C_{\mathrm{fixed}}^{\mathrm{att}}
-\widehat C_{\mathrm{rec}}^{\mathrm{att}}.
\]

양쪽 최종 후보가 모두 같은 사전 문턱 `α,β`를 certified한 cell/support에서만 정의한다.
양수이면 같은 문턱 아래 결정을 미룰 수 있는 policy가 더 낮은 out-of-sample 달성비용을
보였다는 뜻이다. low-D exact matched classes의 `VoDC_C^oracle`과 고차원
`VoDC_C^att`를 분리하여, recourse의 구조적 가치와 학습 회수율을 섞지 않는다.

#### C. Value of Cooperation

\[
\operatorname{VoC}_{C}^{\mathrm{att}}(\alpha,\beta;\boldsymbol\rho)
=\widehat C_{\mathrm{matched\ no\mbox{-}coord,rec}}^{\mathrm{att}}
-\widehat C_{\mathrm{team,rec}}^{\mathrm{att}}.
\]

같은 limiter·shooter·kinetic 자산을 두고 coordination channel 또는 joint conditioning만
개입한 matched comparison에서만 cooperation이라고 부른다. 양쪽이 같은 문턱을 certified한
경우에만 비용 차이를 계산한다. shooter-only는 인과 해석을 돕는 secondary control이다. team
policy class가 idle/null teammate action으로 단독 전략을 모사할 수 있는지도 별도로 기록한다.

#### D. Closure-induced change

scripted, held-out, common fresh-response closure에서 `G_R^att`,
`G_att,r\setminus f`, `VoDC_C^att`, 각 policy의 robust cost와 feasibility를 각각 보고한다.
그 차이는 **closure-induced change**이며 방향을 미리 “erosion”으로 정하지 않는다.
feasibility status가 바뀌면 비용 차이는 계산하지 않고
`certified → unresolved/infeasible` 전이를 보고한다. learned attacker는 exact best response가
아니므로 “declared-budget fresh-response stress”라고 쓴다.

### 4.8 secondary estimands

- first-hit `P(N_safe)`, `P(K_safe)`, `P(K_illegal)`, `P(B)`, `P(C_unsafe)`,
  `P(L_unauth)`를 별도 보고
- net wasted-shot rate, authorized kinetic sacrifice, role별 unauthorized platform loss
- 최초 mode commit 시점과 `M_K` 분포
- `P(N_safe | NET_COMMIT)` 및 `P(K_safe | KINETIC_COMMIT)`
- search/planner attainment 대비 learned recovery gap
- E2에서 threat 1대당 raid-level resource/attrition cost와 raid 종료 시 남은 inventory
- cost ratio에 따른 net/kinetic/hybrid mode share

조건부 성공률의 분모가 policy별로 달라진다는 사실을 항상 함께 보고한다.

---

## 5. 현재 B0 v3로는 답할 수 없는 이유

| 장기 저널 주장에 필요한 현상 | B0 v3 상태 | 필요한 변경 |
|---|---|---|
| 정책이 net/kinetic mode 선택 | net-first가 고정되고 NET_FAIL 뒤 PN takeover | high-level mode action과 authorization guard |
| fired net의 실제 post-FIRE 운동 | FIRE tick의 기하 predicate를 동결하고 나중에 보고 | projectile/deployment/active/contact rollout |
| attacker의 post-FIRE 반응 | raw net-capture eligibility는 FIRE 때 정해짐; 이후 기동은 competing penetration/contact 순서에는 영향을 줄 수 있음 | net flight 동안의 기동이 capture/miss 자체에도 작용하도록 closed-loop 적분 |
| kinetic의 물리 성공확률 | 0.75 m contact와 `p_kill=1.0` 규약 | 한 kinetic mechanism의 calibrated dynamics/effect model |
| 비용·inventory | cartridge/platform persistent resource state 없음 | shot, platform loss, reload/repair state |
| 안전 전환경계 | 6 m veto는 있으나 mode policy가 고를 수 없음 | explicit ROE margin과 unsafe outcome |
| mobile net shooter | current finisher는 stationary | mobile shooter plant 또는 scope 축소 |
| 현실 관측 | 공통 65-D 무잡음·무지연 참값 | mode cue·latency·partial observation 계약 |
| raid economics | attacker 1대, episode reset | 순차 threat와 persistent inventory |

가장 큰 문제는 양쪽 mechanism의 **물리 parity 부재**다. net은 기하 술어이고 kinetic은
완전성공 Bernoulli 규약인 상태에서 나온 mode preference는 simulator가 입력한 편향일 수 있다.
따라서 학습 전에 source-lock과 validation gate를 통과해야 한다.

### 5.1 B0 v4에서 저널 주장을 위해 구현할 것

1. 이동형 net shooter와 별도 kinetic interceptor
2. net `ready → deploying → active → spent` 동역학
3. post-FIRE attacker action과 collision/entanglement 판정
4. kinetic intercept time-to-go, impact condition, platform attrition
5. explicit `WAIT/SHAPE`, `NET_COMMIT`, `KINETIC_COMMIT`
6. no-kill region과 same-tick precedence
7. cartridge·platform inventory와 mode switching cost
8. attacker가 관측하는 FIRE/mode cue와 그 지연
9. 비용 vector, `α`, `β`, cost-ratio sweep
10. dt refinement 및 mode별 unit/regression tests

**첫 그림의 contract-lite = F1-E (exploratory subset of F1).** §5.1 전부가 첫 그림의
선행조건은 아니다. ① 이동형 net shooter와 별도 kinetic interceptor, ②
`ready → deploying → active → spent`의 최소 시간 전이, ③ 매 tick 갱신되는 attacker
상태와 net 위치·개구를 사용한 post-FIRE 접촉/실패 판정, ④ kinetic time-to-go·impact
및 허가된 플랫폼 소모, ⑤ `WAIT/SHAPE·NET_COMMIT·KINETIC_COMMIT`, ⑥ no-kill
guard·same-tick first-hit 순서가 필수다. ⑦은 단일 교전의 shot/platform 소모 카운터,
⑨는 무차원 비용비와 동일 보호·안전 문턱으로 **최소 구현**한다. ⑩은 상태전이·사건순서
단위 검사와 거친 dt 반감 확인만 우선한다. ⑧의 지연·오분류 cue, 재장전·raid inventory,
고충실도 전개/얽힘 물리, 광범위 dt 검증은 G1 이후 판단한다.

③은 생략할 수 없다. FIRE 시점의 `pending_capture`를 타이머로 늦게 보고하는 방식이면
§5.2의 F0와 같은 질문이다. F1-E도 발사 이후 표적 기동이 net의 실제
접촉/미접촉을 바꿀 수 있어야 한다. 다만 그 모델의 물리적 타당성과 효과기 parity는
아직 G1을 통과하지 않았으므로 F1-E 그림을 §5.2의 F1 mechanism-existence 결과로
승격하지 않는다. 기존 B0 v3 파일·계약·B2 runner를 수정하지 않고 별도 모듈에서
실험한다. 새 상수의 단일 provenance 원장은 `shepherd/params.py`의
`mode_switch.*` 항목으로 삼고, 실행 산출물은 그 resolved 값을 기록한다 (docs/105 §3).

F1-E 축소 세계는 **§0–§3의 장기 확장 세계와 다르다**: limiter가 없고, attacker는
방어기 위치·속도에만 반응하며(FIRE/mode/net phase cue 미제공 — §3.2의 "표적의 FIRE
관측 계약" 항목은 F1-E에 적용되지 않는다), net은 이동 원판 대리모형, kinetic은 근접
접촉 사건으로 효과를 판정하는 소모성 요격기다. 두 세계를 혼동해 F1-E 결과를 §3
세계의 주장으로 확대하지 않는다. F1-E의 확정 계약은 docs/106 r3가 정본이다.

F1-E는 **§9 확인 실험의 사전등록·동시추론 의무에서 명시적으로 제외**한다.
탐색 중 파라미터·정책을 고칠 수 있으나 모든 버전과 실패 사례를 남기고, 같은 자료에서
고른 정책의 차이를 확인 결과로 재사용하지 않는다. G1/F1 또는 §9 단계로 올릴 때
world·후보·축·seed를 새로 봉인하고 독립 평가를 시작한다. 상세 계약은 docs/105 §3–§5.

### 5.2 현실성 계층

| 층 | 내용 | 허용 주장 |
|---|---|---|
| **F0** | 현 B0 v3 point-mass + frozen predicate | 구현·학습 pipeline 탐색만 |
| **F1-E** | F1의 contract-lite live-net/explicit-mode 구조, G1 이전 탐색용 | 소재 판정·궤적/사건 디버그만; §9 확인 주장 불가 |
| **F1** | point-mass/response model + live net + explicit kinetic + inventory | mechanism existence와 cheap sweep |
| **F2** | airframe-consistent 6DOF/CTBR, latency/noise, calibrated effector models | primary simulation claim |
| **F3** | bench/HIL 또는 제한 비행에서 net delay/shape와 kinetic kinematics/effect를 분리 검증 | 검증한 성분에 한정한 외부 타당성 고리 |

F0 결과를 F1–F2의 cost frontier에 pooling하지 않는다. F1은 학습 throughput용, F2는 frozen
policy transfer와 preregistered-cell retraining을 분리해 보고한다.

### 5.3 net source-lock

Zheng의 corner-envelope와 dwell은 launch-condition anchor이고, Han의 deployment–collision–
entanglement sequence는 post-FIRE physics anchor다. Liu의 spring–damper/MBD 모델은 tethered-net
대안이다. projectile net과 tethered carried net을 한 plant에서 섞지 않는다.

최소 외부 고리는 다음 중 하나다.

- 실제 net rig의 launch-to-first-contact time과 aperture time history
- 공개 원문의 geometry를 재현한 validation case
- 사전 규칙으로 고른 경계 양쪽 cell과 blinded/random holdout cell의 HIL/bench replay

### 5.4 kinetic source-lock

G0에서 kinetic type을 한 가지로 정한다. sacrificial contact interceptor를 택한다면
최소한 다음이 필요하다.

- relative impact speed와 contact geometry
- time-to-intercept 및 flight envelope
- attacker neutralization의 success model
- defender platform loss/회수 규칙
- no-kill zone의 의미와 안전 판정

`p_kill=1`은 sensitivity endpoint일 수 있으나 유일한 primary 값이 될 수 없다.
kinetic timing proxy는 time-to-intercept만 검증하며 neutralization·safety probability를
검증하지 않는다. effect model을 별도로 검증하지 못하면 minimum-cost 결론을
**source-locked simulation plant 안의 결과**로 명시한다.

### 5.5 cost source-lock

비용은 세 층으로 구분한다.

1. **물리 자원:** cartridge 수, platform loss, energy, time
2. **운용 규약:** unsafe kinetic 허용상한, sortie availability, reload horizon
3. **금전 환산:** 공개·감사 가능한 근거가 있을 때만 부가 case study

primary는 1–2층의 dimensionless cost-ratio map으로 충분하다. 근거 없는 원화·달러값을
정밀하게 붙이지 않는다.

---

## 6. 방법론 패키지

### 6.1 전체 구조

```text
mode-specific physical models
    ├── net launch/capture set
    └── kinetic safe-intercept set
            ↓
low-dimensional reach/avoid + switching oracle
            ↓
scripted existence and counterfactual physics tests
            ↓
mode-conditioned defender learning
            ↓
PFSP / population attacker training
            ↓
frozen cross-play + common fresh-response closure
            ↓
risk-constrained cost and capability frontier
            ↓
F2/F3 transfer and preregistered/blinded-cell validation
```

### 6.2 planner와 학습의 역할

- **저차원 planner/HJ/DP:** mode set, latest safe switch, recourse inclusion과 exact 또는
  certified inner result를 제공한다.
- **trajectory optimization/search:** full-dimensional world에서 존재 가능한 attainment와
  policy recovery gap을 제공한다. upper bound라고 부르지 않는다.
- **MAPPO/HAPPO 계열:** heterogeneous low-level coordination과 high-level mode decision을
  학습한다. 새 MARL 알고리즘을 주장하지 않는다.
- **PFSP/PSRO 계열:** adaptive attacker와 empirical game closure를 만든다. 새 population
  method를 주장하지 않는다.

### 6.3 권장 policy architecture

가장 해석하기 쉬운 시작점은 두 시간척도의 hierarchy다.

- **High-level coordinator:** `WAIT/SHAPE`, `NET_COMMIT`, `KINETIC_COMMIT`을 낮은 주기로 선택
- **Low-level role policies:** limiter, net shooter, kinetic interceptor의 CTBR 또는
  acceleration command
- **Centralized critic:** 학습 중 joint state와 inventory를 사용
- **Decentralized execution:** 실제 관측과 명령권 구조가 허용하는 범위만 사용

state-level MoE/router는 기존 문헌과 겹치므로 구현 선택일 뿐이다. 대조군으로 동일
parameter/inference budget의 stochastic monolithic policy와 latent-conditioned single policy를
반드시 둔다.

### 6.4 attacker curriculum

1. **A0 scripted family:** 현 A-family와 명시적 feint/bait script. debugging과 존재성 확인.
2. **A1 parameter search:** frozen defender에 대한 sealed-budget CEM 등. exact worst-case라고
   부르지 않는다.
3. **A2 league/PFSP:** attacker policy population을 만들고 defender를 함께 훈련한다.
4. **A3 held-out archive:** 학습 중 matchmaking에 쓰지 않은 frozen policies.
5. **A4 common fresh-response closure:** 최종 defender 후보 각각을 상대로 같은 예산으로
   fresh attackers를 학습한 뒤 그 합집합을 동결하고 모든 defender를 다시 평가한다.

서로 다른 defender-specific exploiter에서 얻은 minimum끼리 직접 빼지 않는다. 공통 union
attacker set에서 cross-play해야 한다.

### 6.5 repertoire의 지위

net-first, kinetic-first, option-preserving shaping, immediate kinetic 등의 tactic이 나타날 수
있다. 이들을 episode-level empirical mixture로 유지할지 conditional single policy로 distill할지는
성능·복잡도 결과로 결정한다.

repertoire가 유용하더라도 주장 범위는 다음과 같다.

> 선언한 empirical library와 fresh-response budget에서 여러 mode-conditioned responses의
> support가 pure candidate보다 낮은 달성비용 또는 높은 robust value를 보였다.

정책 파일 여러 개가 이론적으로 필수라고 말하지 않는다. distillation이 같은 성능을 내면
배포는 single conditional policy로 하고, 기여는 physical recourse와 cost frontier에 남긴다.

---

## 7. 필수 대조군과 인과 설계

### 7.1 doctrine baselines

1. **Net-only**
2. **Kinetic-only**
3. **Fixed net-first then scripted kinetic fallback**
4. **Myopic cheapest-feasible:** 현재 추정 성공률과 비용만 보고 mode 선택
5. **Static WTA:** 고정 또는 offline-estimated pairwise `p,c` 표로 선택
6. **Dynamic receding-horizon joint optimizer:** 방어자 기동과 sensor/effector scheduling,
   mode별 미래 rollout을 함께 최적화
7. **Temporal multi-type allocation learner:** 탄약 상태와 순차 작용을 포함한 Yao et al.
   계열 DRL을 현재 plant에 맞게 구현
8. **Stochastic minimum-cost reach-avoid learner:** 같은 `α,β` 문턱과 비용 계약으로 이식
9. **Learned monolithic hybrid policy**
10. **Mode-conditioned hierarchy/repertoire**
11. **Low-D oracle / high-D search attainment**

6–10번은 같은 observation, low-level authority, fallback permission, parameter/inference budget,
training/search budget으로 맞춘다. 정적 WTA 하나만 이기고 trajectory-coupled receding-horizon
optimizer나 minimum-cost reach-avoid learner를 이기지 못하면 Q1 novelty를 주장하지 않는다.

### 7.2 cooperation controls

- shooter-only
- limiter hold
- independent/noncoordinated limiters
- full coordination
- teammate observation/channel mask
- limiter action shuffle
- one-at-a-time limiter withdrawal
- 동일 자산 수를 유지한 homogeneous all-net 또는 all-kinetic team

개별 limiter의 leave-one-out effect를

\[
I_i=\widehat C^{\mathrm{att}}_{-i}
-\widehat C^{\mathrm{att}}_{\mathrm{full}}
\]

로 기록한다. 양쪽 policy가 같은 문턱을 certified한 비교에서만 비용 차이를 쓴다.
superadditive team effect는 shooter와 각 단일 limiter의 증분 합과 full-team 증분을
비교하되, post-hoc로 유리한 정의를 고르지 말고 사전 봉인한다.

### 7.3 physics controls

- `τ_net>0` 대 `τ_net=0`
- live projectile net 대 FIRE-time frozen capture predicate
- one-shot 대 reload/reusable net
- finite 대 effectively infinite active window
- explicit kinetic dynamics 대 fixed `p_kill`
- no-kill rule on/off
- platform attrition on/off
- post-FIRE attacker reaction on/off

특히 delay × depletion의 2×2 factorial을 권장한다. 각 physics cell에서 새 policy를 학습한
결과만 비교하면 학습 난이도가 물리 원인으로 보일 수 있다. 다음 두 평가를 모두 둔다.

1. **Frozen-library transplant:** 같은 policy library를 counterfactual plant에 교차 이식하여
   즉각적인 payoff·mode-rank reversal을 측정
2. **Matched retraining:** 각 plant에서 같은 budget으로 재학습하여 달성 가능한 성능을 측정

### 7.4 resource controls

- net cartridge `K_N=1` 대 `K_N=2`
- kinetic platform reserve 1대 대 2대
- E1 episode reset 대 E2 persistent inventory
- 실제 mode change 대신 `+1 cartridge` 또는 `+1 interceptor`를 준 대조

협력의 이득이 단순히 자산 하나를 더 둔 효과인지 분리한다.

### 7.5 information controls

- **No-late-information:** `t_0` 이후 mode-relevant cue를 mask하여 fixed와 recourse의
  정보집합을 같게 둔다.
- **Cue shuffle:** 물리 trajectory는 유지하고 후기 cue를 episode 사이에서 섞어 선택가치가
  실제 branch 정보에서 왔는지 본다.
- **Oracle reveal:** true `λ`를 사전 정한 시점에 제공한 정보상한과 realistic observation
  policy를 비교한다.
- **Delayed/noisy reveal:** cue latency·오분류율에 따라 `G_R^att`,
  `G_att,r\setminus f`, `VoDC_C^att`가 어떻게 닫히는지 측정한다.
- **Identifiability audit:** confirmation과 분리한 자료에서 `b_t` 또는 branch decoder의
  proper scoring rule·calibration을 보고한다.

후기 관측을 지웠는데도 recourse gap이 그대로라면 정보의 가치가 아니라 policy class,
optimization 또는 다른 action authority 차이일 가능성이 크다.
F1-E의 fixed-vs-switch 그림에는 이 통제가 아직 없으므로 그 차이를 “정보 가치”나
“recourse gain”으로 이름 붙이지 않는다.

---

## 8. 분석적 특성화 패키지

### 8.1 T1 — hybrid basin factorization

single irreversible commit, 명시적 Markov/information 가정 아래 full winning set을
post-commit launch-success set과 pre-commit reach-avoid basin으로 분해한다. full-dimensional
exact equality가 어렵다면 sound inner approximation으로 낮춘다.

검증은 저차원 subcase에서 monolithic HJ/exhaustive solution과 nested solution의 일치 또는
보수성을 비교한다.

### 8.2 T2 — information-matched recourse inclusion과 strict witness

§4.6의 filtration과 matched policy class에서 `Π_fixed⊆Π_rec` embedding을 먼저 보이고
`B_fixed^oracle⊆B_rec^oracle`을 얻는다. **작은 유한 toy의 exact backward DP/전수열거를
T2 기본 경로**로 둔다. 이 경로가 해당 저차원 모형에서도 불가능할 때만 recourse inner와
fixed outer를 구해 `S_B^cert`를 인증한다. 이어 `t_0` 뒤의 informative observation과 branch-dependent
mode-rank reversal이 동시에 있는 reduced planar/1D 예제를 구성하여 strict inclusion을 보인다.

핵심은 양화 순서다.

```text
fixed:    F_t0에서 doctrine을 하나 선택한 뒤 latent branch 분포의 제약을 만족
recourse: stopping time τ의 F_τ 정보로 최초 mode를 선택하며 같은 제약을 만족
```

toy의 `M_N/M_K`는 연구자가 고르므로 mode-rank reversal을 파라미터로 만들어낼 수 있다.
따라서 T2는 **solver·정책군·정보구조의 검산과 실험 설계**까지만 맡는다. 독립성 있는
G2의 물리적 증거는 F1에서 별도 source-locked parameter와 held-out scenario로 확인한다.
이 toy witness는 실험 설계를 정당화하는 장치다. 실제 hybrid stochastic game의 nontrivial
equivalence, sufficient condition 또는 certified bound를 얻기 전에는 독립 theory
contribution으로 세지 않는다.

### 8.3 T3 — latest safe kinetic switch

단조 closing 및 한 번 통과하면 되돌릴 수 없는 ROE boundary 가정 아래
`M_K(s)=0`이 latest-safe-switch surface를 이룬다는 sufficient condition을 제시한다. 단순 radial
subcase의 후보 경계는

\[
r\ge R_{NK}+v_{in}\tau_K+\frac12a_{in}\tau_K^2
\]

형태이나, 실제 상대동역학과 부호 규약에 맞춰 재유도한 뒤 사용한다. limiter가 `M_K`를
증가시킬 수 있는 조건을 보이고 solo basin이 team basin에 포함됨을 증명한다.

null action이 허용되면 일반적으로 `B_solo⊆B_team`이지만 strict inclusion은 자동이 아니다.
constructive witness 또는 sufficient condition이 필요하다.

### 8.4 T4 — model-error erosion

plant/net 오차 집합 `E`가 확보되면 nominal launch set `L`을 그대로 robust set이라 부르지
않고 `L⊖E`와 같은 erosion으로 sound inner set을 구성한다. 통계 calibration만 있다면
보장 확률과 exchangeability/coverage 가정을 명시한다.

### 8.5 분석의 한계

- recourse와 optimal switching 자체는 고전 개념이다.
- reachability, engagement zone, stochastic flexibility와 WTA도 확립 분야다.
- basin 분해, class inclusion, 1D witness, 단순 erosion만으로 Q1 theory contribution을
  주장하지 않는다.
- Q1 설득력은 이 분해가 실제 net/kinetic physics와 adaptive attacker에서 측정 가능한
  mode-rank reversal, certified strict recourse region, switch/cost 결과로 이어질 때 생긴다.

---

## 9. 평가·통계 계약 초안

**적용 시점:** 이 절은 G1 이후 world와 후보를 고정하고 독립 평가를 시작할 때의
확인 계약 초안이다. docs/105의 F1-E 첫 그림과 T2 toy 설계 탐색은 여기서 **면제**한다.
면제는 확정 주장까지 허용한다는 뜻이 아니다. F1-E에서 고른 파라미터·정책·축을
그대로 같은 데이터에 적용하여 아래 신뢰경계나 `VoDC`를 사후 계산해도 확인 결과가
되지 않는다.

### 9.1 primary endpoints

1. finite low-D exact strict-region measure `G_B^{exact,finite}`; exact solve가
   불가능한 별도 문제에서만 sound inner/outer `G_B^cert=μ(S_B^cert)`
2. oracle/attained mode-rank reversal measures `G_R^oracle,G_R^att`
3. selected-policy attained basin differences `G_att,r\setminus f`와 반대 방향
4. 양쪽 selected policy가 feasible인 support의 `VoDC_C^att(α,β;\boldsymbol\rho)`
5. `VoC_C^att(α,β;\boldsymbol\rho)`
6. attained-cost break-even/capability surface

여섯 개를 모두 동등한 primary로 두지 않는다. **T2 계산의 기본 경로는 finite exact
solve**이며 `G_B^{exact,finite}`가 선언한 유한 정책군에서 양수인지 확인한다.
이는 정보구조와 solver의 구조적 결과이지 F1 물리의 존재성 증거가 아니다.
저널의 물리·시스템 주장은 별도 source-locked F1에서 후기 관측 가능한 mode-rank
reversal, 같은 제약 아래 selected policy의 비용 차이, 그리고 §7 대조군이 함께
지지해야 한다. F1에서 저차원 exact 결과를 재현하지 못하면 toy를 headline으로
승격하지 않는다. `G_R^oracle`은 T2 mechanism endpoint,
`G_R^att,G_att,r\setminus f,VoDC_C^att,VoC_C^att`는 F1 이상에서의 학습·system
endpoints다. cost surface는 설계 결과다. E2를 포함하면 raid-level cumulative
resource/attrition cost를 별도 secondary로 사전 등록한다.

### 9.2 primary axes

primary map의 축은 세 개를 넘기지 않는다.

- net delay/agility를 묶는 한 좌표
- kinetic safe-window 또는 ROE margin 한 좌표
- cost-ratio vector `\boldsymbol\rho`에서 사전 선택한 한 축

net aperture, active window, shooter mobility, limiter authority, sensor latency를 모두 한꺼번에
primary로 올리지 않는다. cheap Morris/variance screen 또는 물리 논리로 승격 변수를 정한 뒤
나머지는 robustness arm으로 둔다.

### 9.3 독립 단위

- **policy-instance claim:** freeze한 policy의 environment replicate가 평가 단위다.
- **learning-algorithm claim:** 독립 training seed가 algorithm replicate이고 episode는 그
  아래의 반복 측정이다. seed를 “후보 policy 수”로 세거나 best seed만 고르지 않는다.
- cross-play cell을 독립 policy 표본처럼 세지 않는다.
- cell·policy·mode 비교 전체에 사전 선택한 familywise simultaneous LCB/UCB 또는 동등한
  scenario-level procedure를 적용한다.
- rollout 기반 `G_R^att`와 attained basin은 point-classification 지도로 계산하지 않고
  certified/failed/unresolved cell과 그 측도의 신뢰구간을 보고한다. switch surface도 한
  선보다 confidence band로 쓴다. 이 통계 처리는 policy-class nonmembership certificate를
  대신하지 않는다.
- common random numbers는 initial state와 stochastic plant에 사용하되 attacker policy seed와
  섞지 않는다.
- training seed 수와 cell당 episode 수는 smoke-test 관행값이 아니라 preregistered
  minimum detectable effect, power/precision target, multiplicity correction으로 정한다.

### 9.4 discovery와 confirmation

- discovery에서 cost weights, axes, policy candidates, closure rounds를 탐색한다.
- 독립 selection split에서 policy class별 최종 checkpoint 하나와 tie-break를 고정한다.
- confirmation 전 `Ω_eval`, `α`, `β`, `\boldsymbol\rho` grid,
  finite exact `G_B^{exact,finite}` 또는 대안 `G_B^cert`의 범위,
  `G_R^oracle/G_R^att`의 최소효과,
  seed·episode 수, 동시 신뢰절차, censoring 규칙을 봉인한다.
  finite toy의 계산 자체에는 표본 신뢰절차가 필요 없지만, 출판할 toy의
  전이표·정책군·경계 처리·탐색 이력은 고정해 공개한다. F1의 경험적 효과는
  별도 selection/confirmation 자료에서만 판정한다.
- untouched confirmation set에서는 후보를 다시 고르거나 cost minimum을 다시 최적화하지
  않는다. 불가피하면 별도 selection split 또는 selection-adjusted inference를 쓴다.
- fresh-response attackers는 confirmation payoff를 본 뒤 추가하지 않는다.
- closure가 예산 안에서 plateau하지 않으면 “robust” 대신 “tested against N archived and M fresh
  responses”라고 쓴다.

### 9.5 최소 양성 판정

Q1 spine을 유지하려면 다음이 모두 필요하다.

1. **Rank reversal:** 후기 관측으로 구별 가능한 information state 사이에서
   toy의 `G_R^oracle>0`가 exact로 계산되고, 독립적인 source-locked F1에서
   관측 가능한 상태 사이의 순위 변화와 selected controller의 `G_R^att`가 확인된다.
2. **Strict recourse 구조:** 먼저 선언한 작은 이산 toy에서 exact
   `B_rec^oracle\setminus B_fixed^oracle`와 `G_B^{exact,finite}`를 구한다.
   exact가 불가능한 문제에서는 sound `B_rec^in\setminus B_fixed^out`이 필요하다.
   search나 rollout의 fixed-policy 실패만으로 통과시키지 않는다.
   **toy의 양성만으로 G2를 통과시키지 않으며**, F1의 별도 물리 증거가 필요하다.
3. **Cost:** 양쪽 selected policy가 같은 `α,β` 문턱을 certified한 support에서만
   `VoDC_C^att`의 paired CI 하한이 사전 최소효과보다 크다.
4. **Team attribution:** cooperation controls에서 `VoC_C^att` 방향이 유지된다.
5. **Adaptivity:** common held-out + fresh-response closure에서 status와 효과를 각각
   보고하며, 사전 정한 robustness 문턱을 만족한다.
6. **Physics:** frozen-predicate/fixed-p controls가 full physics 결과를 설명하지 못한다.
7. **Transfer:** frozen policy의 F2와 사전 규칙으로 고른 F3 경계 양쪽/blinded cell에서
   검증한 물리 성분의 방향이 유지된다.

“학습 성공률이 높다” 하나로 통과시키지 않는다.

---

## 10. 반증 결과와 정직한 축소 경로

| 결과 | 해석 | 처분 |
|---|---|---|
| 한 mode가 전 영역에서 지배 | switching 가치 없음 | dominant-mode capability paper로 축소하거나 중단 |
| low-D `B_rec^oracle=B_fixed^oracle` 또는 certified strict witness 없음 | deferred commitment의 구조적 이득 미확인 | recourse spine 철회 |
| static WTA가 coupled policy와 동등 | trajectory coupling 실익 없음 | 고정 effectiveness abstraction이 충분하다는 결과 |
| fresh-response closure에서 recourse gain 소실 | scripted conditional | robustness 주장 철회, exploitation mechanism 보고 |
| limiter intervention 효과 없음 | cooperation 아님 | single-selector paper로 축소 |
| physics ablation에서도 같은 결과 | effector physics 원인 아님 | learning/selection artifact로 재판정 |
| net 이점이 episode reset에서만 발생 | raid-level resource 이점 없음 | E1 단일교전 주장으로 제한 |
| F2/F3에서 switch surface 붕괴 | reduced-world artifact | Q1 투고 중단 또는 모델 재설계 |
| learned policy가 search를 회수 못함 | 학습 실패 | planner/frontier paper만 가능한지 재판정 |

negative result를 숨기지 않는다. 특히 “net-first가 항상 싸다” 또는 “hybrid가 항상 낫다”를
가정하고 world를 조정하지 않는다.

---

## 11. 실행 순서와 gate

### Track A — 현 학기 foundation

1. B2 작업 트리의 provenance·hash 충돌을 해결한다.
2. 봉인된 B2 scripted primary와 forced-fire arm을 실행한다.
3. stop rule을 판정한다.
4. PASS일 때만 `docs/89`의 3-arm MAPPO를 실행한다.
5. current-world 학습성과와 throughput을 확보한다.

Track A에서 kinetic mode learning, PFSP co-adaptation, live net을 몰래 추가하지 않는다.

### Track B — Q1 방향; 첫 착수는 docs/105의 F1-E

| Gate | 질문 | 통과 조건 | 실패 시 |
|---|---|---|---|
| **G0 Scope** | kinetic type·비용·ROE가 정해졌는가 | mechanism 1개와 cost/constraint contract; 우선 sacrificial contact 후보를 문서로 판정 | world 구현 금지 |
| **G1 Physics parity** | 두 mode가 비교 가능한가 | live net, explicit kinetic, dt/validation checks | 학습 금지 |
| **G2 Existence** | 정보가 닿는 branch의 순위 반전이 F1 물리에서도 생기는가 | T2 toy의 finite exact strict difference **및 별도 source-locked F1 held-out에서 관측 가능한 reversal·matched cost/guard 확인**; toy나 search만으로 통과 금지 | Q1 spine 중단·세계 재검토 |
| **G3 Coupling** | 강한 dynamic baseline도 놓치는가 | receding-horizon joint optimizer와 min-cost reach-avoid learner 대비 matched gap | 기존 solver 적용 수준으로 축소 |
| **G4 Learning** | policy가 structural gap을 회수하는가 | MDE/precision 기반 seed·episode, held-out grid, oracle recovery | method 재설계 |
| **G5 Adaptivity** | fresh response에서도 남는가 | common closure set에서 사전 정한 `G_R^att/G_att,r\setminus f/VoDC_C^att/VoC_C^att` 문턱 유지 | scripted-only로 제한 |
| **G6 Transfer** | 현실적 plant에서 남는가 | F2 frozen transfer + preregistered boundary/blinded F3 anchor; kinetic effect 범위 명시 | 출판 보류 또는 simulation-only로 축소 |
| **G7 Raid** | raid-level 자원·손실 주장이 가능한가 | 봉인한 finite-raid inventory model에서 방향 유지 | E1 비용만 주장 |

### 권장 계산 예산 순서

1. G0 결정 카드 작성 — 새 world 코드 없음.
2. NumPy 저차원 finite-grid DP/전수열거 — **T2의 정책군·정보구조 검산까지만**.
   파라미터를 고른 toy의 양성은 G2 물리 증거가 아니다. finite exact가 실패한
   별도 문제에만 inner/outer 또는 interval/HJ 경로를 검토한다.
3. Track A의 B2 stop rule **판정**을 확인한다. 판정 전에는 Track B F1-E world
   구현을 시작하지 않는다. FAIL이면 Track A의 봉인된 전환 경로와 자원 배분을
   먼저 재검토한다. G0·toy는 Track A의 서버 실행과 병행 가능하다.
4. 별도 F1-E module에서 scripted net-first/kinetic-first/threshold switch,
   시각화 우선의 cost-ratio sweep과 반례 탐색.
5. 흥미로운 신호가 있을 때만 G1 parity·source-lock을 닫고 F1 독립 확인,
   single-policy throughput pilot로 진행한다.
6. 이후 small attacker pool → full league/closure → selected F2 transfer → E2 raid를
   각 gate의 결과에 따라 선택한다.

G2가 실패하면 대규모 PFSP를 돌리지 않는다. 먼저 세계가 질문을 실제로 포함하는지 확인한다.

---

## 12. 권장 논문 형태

### 12.1 가제

**권장**

> *Preserving the Last Safe Option: Risk-Constrained Net–Kinetic Mode Switching against
> Adaptive UAVs*

대안

> *Least-Cost Interception with Deferred Effector Commitment for Heterogeneous Counter-UAS*

> *Physics-Coupled Effector Recourse in Adaptive Counter-UAS Engagements*

### 12.2 contribution package

1. **Physical finding:** endogenous target–defender coupling이 만드는 mode-rank reversal과
   low-D certified strict recourse region
2. **Analytical characterization:** information-matched policy classes, launch-success set,
   certified recourse basin과 latest-safe-switch subcase
3. **Learning/evaluation:** standard MARL+PFSP를 사용한 coupled mode policy와 common
   fresh-response closure
4. **System result:** 사전 고정한 protection/safety 문턱에서의 attained basin,
   `VoDC_C^att`, `VoC_C^att`와 attained-cost break-even surface
5. **Validation:** 강한 dynamic baseline, matched physics counterfactual, F2/F3 source-locked
   transfer

### 12.3 핵심 figure set

1. net/kinetic mode graph와 사라지는 kinetic window
2. finite exact DP의 `L_N,L_K`와
   `B_rec^oracle\setminus B_fixed^oracle`; inner/outer는 exact가 불가능할 때의 대안
3. attacker branch별 mode ranking과 switch surface
4. cost ratio × threat/latency의 attained-cost mode map
5. static WTA, dynamic optimizer, fixed doctrine, learned recourse의 threshold-matched cost 비교
6. limiter intervention의 `VoC_C^att` 및 mode-margin 변화
7. scripted → held-out → fresh-response의 feasibility/effect change
8. F1 → F2/F3 transfer
9. E2 raid의 cumulative cost와 남은 inventory

### 12.4 출판 분할

- **현 학기 결과:** current-world feasibility/MAPPO foundation. Q1 r3.1의 물리 증거로 포장하지
  않는다.
- **Q1 본 논문:** Track B의 G0–G6. E2가 되면 raid-level cumulative
  resource/attrition cost까지 포함한다.
- **후속:** 다수 동시 공격기, online threat-type inference, 실제 multi-effector flight test.

한 논문에 새로운 MARL 알고리즘, 다중 swarm, perception, hardware prototype까지 모두 넣지
않는다. Q1 본체의 우선순위는 **물리 parity → recourse effect → adaptive closure → cost
frontier**다.

---

## 13. 주장·용어 통제

### 13.1 허용 표현

- “attained cost of the preregistered selected policy on the finite evaluation suite”
- “empirical robust value over a frozen finite attacker/plant set”
- “fresh response found under a sealed training budget”
- “physically coupled mode choice”
- “deferred effector commitment”
- “certified mode-rank reversal under the sealed information contract”
- “low-dimensional certified strict recourse region”
- “attained-policy basin difference”
- “source-locked F2 transfer”
- “low-collateral design intent”

### 13.2 증거 없이는 금지

- globally optimal / guaranteed worst case
- first-ever multi-effector C-UAS policy
- real-world least cost
- exact best response
- net is non-destructive
- kinetic always succeeds
- cooperation is necessary
- policy mixture is inherently superior to a neural policy
- sim-to-real success
- inventory economics from a single reset episode
- lifecycle economics from a short finite raid
- clairvoyant branch-wise mode selection presented as fixed doctrine
- cost `VoDC_C^att` when either compared selected policy is infeasible or unresolved
- adaptive robustness from scripted A-family only

### 13.3 mode와 role을 구분한다

- **Role:** limiter, net shooter, kinetic interceptor처럼 platform이 담당하는 기능
- **Mode:** 현재 mission-level commitment가 shaping, net, kinetic 중 무엇인지
- **Mechanism:** 실제 효과가 생기는 물리 과정
- **Tactic/policy:** state/history에서 role action과 mode를 정하는 제어법

이 네 단어를 교환해서 쓰지 않는다.

---

## 14. 채택 시 필요한 산출물

1. `B0 v4` world contract
2. net dynamics validation card
3. kinetic mechanism and attrition card
4. ROE/no-kill semantics contract
5. cost and inventory contract
6. latent branch·observation filtration·commit stopping-time contract
7. matched fixed/recourse policy-class and fallback contract
8. E1/E2 scenario contract
9. NumPy finite-grid exact DP/전수열거 스크립트와 저장 그림
10. launch-set, rank-reversal and basin estimator
11. defender training contract
12. attacker population and common-closure contract
13. static/dynamic WTA, joint optimizer and min-cost reach-avoid baseline specifications
14. causal intervention preregistration
15. F2/F3 transfer and blinded-cell protocol
16. simultaneous-inference, MDE/power and split-sample analysis plan
17. claim–evidence registry

`docs/104` 승인만으로 이 산출물들이 봉인되지는 않는다. G0가 먼저다.

---

## 부록 A. 가장 가까운 문헌의 정확한 위치

### A.1 Zheng et al.

**Canlun Zheng et al., “Vision-Based Cooperative MAV-Capturing-MAV,” IROS 2025.**

<https://arxiv.org/html/2503.06412>

- cooperative perception–pursuit–launch–capture system
- circular formation으로 target을 capture zone에 유지
- four corner-node future envelope와 0.5 s dwell
- 실제 17회 중 11회 포획 보고

본 연구는 Zheng을 “단순 firing threshold”로 요약하지 않는다.

### A.2 Gavin & Bronz

**T. Gavin and M. Bronz, “Intercepting an Agile Target with Net-Carrying Drones using
Competitive Multi-Agent Reinforcement Learning,” 2026.**

<https://arxiv.org/html/2607.05939>

- 3v1, CTBR, MAPPO+PFSP
- blocking, encirclement, 후속 capture 기회를 기다리는 행동
- 모든 pursuer가 homogeneous rigid underbody net 보유
- 별도 FIRE, deploy, active, spent, ammo state 없음

### A.3 AgilePE

**W. Tang et al., “AgilePE: Autonomous UAV Pursuit-Evasion via Self-Play Reinforcement
Learning,” 2026.**

<https://arxiv.org/html/2608.14135>

- 1v1 CTBR, self-play/FSP/PFSP
- dynamics response, latency/noise/randomization
- archived-policy evaluation과 zero-shot hardware

adaptive opponent와 PFSP/sim-to-real은 여기서 신규성이 아니다.

### A.4 Huh et al.

**“Multi-Agent Reinforcement Learning for Multi-UAV Pursuit with Full Planar Motion and a
Limited Detectable Region,” Machines 14(4):413, 2026.**

<https://www.mdpi.com/2075-1702/14/4/413>

- 6DOF, limited FOV, MAPPO
- net-gun engagement envelope와 capturability reward

### A.5 Liu et al.

**R. Liu, H. Ren, and W. Fan, “Dynamics and Control of Vision-Aided Multi-UAV-tethered
Netted System Capturing Non-Cooperative Target,” 2025.**

<https://arxiv.org/abs/2506.03297>

- spring–damper tethered net, MBD, vision, MAPPO

### A.6 Han et al.

**K. Han et al., “Dynamics and Experimental Validation of a UAV-Borne Flexible Net for
Intercepting Low, Slow, and Small Targets,” Drones 10(7):478, 2026.**

<https://www.mdpi.com/2504-446X/10/7/478>

- stow, deployment, collision, entanglement의 전체 sequence
- field test와 형상·시간 비교
- 확인한 주 모델은 target stationary assumption을 포함

post-contact net physics 자체도 신규성으로 주장하지 않는다.

### A.7 launch/decision 선례

**SD2AC: A reinforcement learning framework using distribution evaluation and sequential
decision-making for UCAV combat, 2025.**

<https://academic.oup.com/jcde/article/12/7/96/8120254>

- missile flight dynamics
- explicit stochastic hold-fire/launch policy

**Catch Planner: Catching a Moving Object with a Robot Arm, 2023.**

<https://arxiv.org/html/2302.04387>

- catching time과 terminal state를 함께 다루는 planning-with-decision

**A. Selmonaj et al., “Hierarchical Multi-Agent Reinforcement Learning for Air Combat
Maneuvering,” 2023.**

<https://arxiv.org/html/2309.11247>

- heterogeneous aircraft dynamics와 weapon envelope
- ammunition observation, cannon/rocket action, hierarchical command와 league self-play

### A.8 population/response 선례

- PSRO: <https://proceedings.neurips.cc/paper_files/paper/2017/hash/3323fe11e9595c09af38fe67567a9394-Abstract.html>
- NeuPL: <https://arxiv.org/html/2202.07415>
- OPRE: <https://proceedings.mlr.press/v119/vezhnevets20a.html>
- Conflux-PSRO: <https://arxiv.org/abs/2410.22776>
- Fast Peer Adaptation: <https://proceedings.mlr.press/v235/ma24n.html>
- MAVIPER: <https://arxiv.org/abs/2205.12449>
- VolleyBots fresh exploiter evaluation: <https://arxiv.org/html/2502.01932>

### A.9 WTA와 C-UAS 비용 선례

- *A hybrid multi-objective evolutionary algorithm with high solving efficiency for UAV
  defense programming*, 2024: <https://doi.org/10.1016/j.swevo.2024.101572>
- *Robust Resource Allocation for C-UAS Defense: A Reinforcement Learning Approach*, 2026:
  <https://doi.org/10.1201/9781003739234-6>
- *Effect-based weapon-target assignment with minimised collateral damage*, 2016:
  <https://doi.org/10.1504/IJOR.2016.080149>
- *EdgeTwin-DRL: Real-Time Counter-UAS Detection and Response Optimization*, 2026:
  <https://www.mdpi.com/1424-8220/26/17/5632>
- hard/soft coordination: <https://cdn.aaai.org/Symposia/Fall/2001/FS-01-05/FS01-05-001.pdf>
- ship maneuver with weapon/sensor scheduling: <https://doi.org/10.1002/nav.22186>
- multi-type ammunition, temporal constraints and sequential DRL:
  <https://doi.org/10.1016/j.iswa.2026.200665>
- leakage–hard-interceptor efficient frontier: <https://doi.org/10.1287/opre.2024.1025>
- stochastic minimum-cost reach-avoid RL: <https://arxiv.org/abs/2605.11975>
- UK government C-UAS competition requirements—cost per use, proportional effect and low
  collateral: <https://www.gov.uk/government/publications/countering-drones-finding-and-neutralising-small-uas-threats/competition-document-countering-drones-finding-and-neutralising-small-uas-threats>

이 자료들은 minimum-cost response와 multi-effector selection의 실용성을 뒷받침하지만,
그 자체를 신규성으로 주장할 수 없게 한다.

### A.10 hybrid reachability와 engagement mode 선례

- *Hamilton-Jacobi Reachability Analysis for Hybrid Systems with Controlled and Forced
  Transitions*: <https://arxiv.org/abs/2309.10893>
- *Capture, Shield, or Neutralize: Engagement-Aware Pursuit-Evasion*:
  <https://arxiv.org/abs/2607.10986>

따라서 hybrid mode reachability나 engagement mode 변경 자체도 신규성으로 세지 않는다.

---

## 부록 B. 현재 증거와 장기 주장 사이의 방화벽

| 현재 증거 | 허용 해석 | 금지되는 확대 |
|---|---|---|
| R2a limiter-hold map | fixed current-world feasibility structure | net/kinetic switch surface |
| rule-based B null | 해당 규칙이 current net frontier를 못 밂 | cooperation/recourse 무가치 |
| search C `+0.370` | finite-budget current-world attainment witness | deployable policy 또는 upper bound |
| B0 v3 `pending_capture` | FIRE-time predicate의 delayed report | projectile net dynamics |
| current kinetic contact | simulator의 phase/contact 규약 | calibrated kinetic effect |
| `p_kill=1.0` | 현재 contract value | 실제 kinetic reliability |
| 6 m veto | current no-kill convention | 외부 ROE validation |
| scripted A2 | 한 attacker family | adaptive attacker closure |
| current 65-D common state | common observation | realistic distributed sensing |
| B2/MAPPO future result | foundation learning outcome | minimum-cost mode-switching evidence |
| F1-E 첫 fixed-vs-switch 탐색 그림 | 소재 계속 여부·궤적/first-hit 디버그 | `VoDC`, recourse gain, 정보 가치, certified feasibility |
| 파라미터를 고른 finite toy exact DP | 선언한 이산 모형의 T2 정책군/정보구조 검산 | source-locked F1 물리의 mode-rank reversal 또는 G2 단독 통과 |

---

## 장기 확장안의 권고

아래 권고는 §0–§14의 확대판에만 적용한다. 당장 착수할 논문 소재와 첫 실험은 문서 앞의
“먼저” 절을 따른다.

후속 Q1 연구는 **“협력 정책을 더 잘 학습한다”**가 아니라 **“서로 다른 물리·비용·안전
제약을 가진 net과 kinetic 효과기의 결정을 얼마나 늦게까지 열어둘 가치가 있으며, 팀 기동이
그 선택권을 어떻게 보존하는가”**를 묻는 편이 강하다. Gavin & Bronz의 PFSP와 병렬 MARL은
학습 엔진으로 채택하되 contribution으로 세지 않는다. Zheng과 Han은 net physics/launch의
기준선으로 사용한다. static WTA뿐 아니라 trajectory-coupled receding-horizon optimizer,
temporal multi-type allocation, stochastic minimum-cost reach-avoid learner를 강한
대조군으로 둔다.

가장 먼저 할 일은 대규모 학습이 아니다. G0에서 kinetic mechanism, 비용 vector, no-kill
rule, 정보구조를 고정한 뒤 F1 world에서 후기 관측이 식별 가능한 mode-rank reversal과
`B_rec^in\setminus B_fixed^out`의 certified strict witness를 실제로 만드는지 저차원
oracle/bounded solver로 확인해야 한다. search는 recourse feasibility의 보조 witness일 뿐
fixed class의 불가능성을 증명하지 못한다. 그 존재성이 확보된 뒤에만 PFSP와 heterogeneous
MARL로 attained basin, `VoDC_C^att`와 adaptive robustness를 묻는다.
