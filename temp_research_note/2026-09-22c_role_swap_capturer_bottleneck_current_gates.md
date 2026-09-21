# 2026-09-22 — 역할 교체 진단과 현재 연구 위치

**판정:** pilot `NO_SELECTION`을 유지한다. 한 checkpoint의 사후 역할 교체는 learned capturer 쪽에서 발사 기회와 clean trajectory를 잃는 현상을 가리키지만, 협력 이득의 부재·존재 또는 원인을 단정하지 않는다.

## 06:52~07:15 KST: post-hoc role swap

진단 코드 `1b7088e`(06:52), 계보 검사 수정 `b2b2c8b`(06:54), 산출물 수확 `47a4341`(07:15). 정본은 [role-swap JSON](../artifacts/marl/b0_v3_pilot/role_swap_c0_base_seed0_e10.json)이다. **c0_base/seed0의 최종 32,768-step checkpoint 하나**, pilot 때 이미 본 280개 평가 scenario만 사용했다. 실행 코드 `226088f`, 평가 코드 `b2b2c8b`; 사후 기제 진단이며 재선택 실험이 아니다.

| limiter / capturer | clean N / 280 | FIRE / 280 | 비인가 engagement / 280 | clean crossing을 만든 episode / 280 |
|---|---:|---:|---:|---:|
| scripted c5 / scripted | 148 | 279 | 20 | 280 |
| learned / scripted | 156 | 279 | 1 | 280 |
| scripted c5 / learned | 14 | 44 | 22 | 32 |
| scripted c5 / learned, pointing을 policy mean으로 실행 | 11 | 44 | 21 | 31 |
| learned / learned (봉인 pilot 결과 재사용) | 10 | 39 | 0 | 기록 안 됨 |

scripted capturer를 유지하면 learned limiter도 156/280 N을 얻는다. 반대로 learned capturer를 넣으면 scripted limiter를 그대로 써도 clean crossing이 280→32, N이 148→14로 급감한다. mean pointing으로 바꿔도 crossing 31, N 11이므로 **최종 checkpoint의 실패를 stochastic pointing noise 하나로 설명할 수 없다.** 낮은 FIRE도 적어도 이 비교에서는 발사 head 단독 문제로만 읽을 수 없다. 발사할 수 있는 기하·궤적 자체가 대부분 사라졌다. 다른 역할을 고정한 사후 개입이므로 learned limiter의 독립 협력 기여나 학습 원인을 확인하는 증거는 아니다.

같은 날 로컬에서 추가로 돌린 `hold limiter + scripted capturer`는 151/280 N, 279/280 FIRE, 280/280 clean crossing, `H_illegal=0`이었다. **현재 정본 파일·커밋 없는 보조 계산**이며 서버 role-swap의 c5 baseline `H_illegal=20`과 로컬 재실행의 21이 달랐다. 이 값을 `learned limiter 156`에 대한 확정 효과 추정치로 쓰지 않는다. 동일 실행 환경·정본 산출물로 재현하기 전까지는 “learned limiter가 단순 hold보다 낫다”는 주장도 보류한다.

## 계획상의 위치와 권한

- **Track A:** [89 §7](../docs/89_research_plan_r2_hybrid_marl.md)의 B2/W5는 원래 9/29~10/12 일정이었으나 9/22 조기 완료. [docs/107](../docs/107_w5_stop_rule_decision_draft.md)의 PASS로 MAPPO pilot을 열었고, [docs/110](../docs/110_b0v3_mappo_hyperparameter_pilot_contract.md)의 `NO_SELECTION`으로 **W6 본 학습은 아직 닫혀 있다**. 연구 질문은 살아 있지만 학습 양성 결과는 없다.
- **Track B:** [105 r4](../docs/105_mode_switch_execution_plan.md)의 D0/G0·D1 toy는 9/18 완료. toy strict band는 설계된 양성 사례이며 F1-E 실증이 아니다. B2 stop-rule 선행조건은 충족됐으므로 D2 구현은 **시간 게이트상 가능**하지만 아직 미착수다. Track A 병목 분석과 서버·인력 우선순위를 지키면서 착수 여부를 정한다. F1-E net/kinetic 물리 모델은 [106 r3](../docs/106_mode_switch_g0_contract.md)의 대리 가정 범위에 묶인다.
- **출판 주장:** 현재는 “B0 v3 scripted 경계는 측정 가능, c5는 clean N을 늘리지 못하고 비인가 engagement를 늘림, 현재 MAPPO pilot은 실패”까지다. learned cooperation, frontier extension, mode-switch 비용 우위, 실기 타당성을 아직 주장하지 않는다.

## 다음 행동 — 좁은 순서

1. **capturer 기제 감사:** 동일 checkpoint와 같은 scenario를 고정해 BC 직후 대 최종의 aiming axis/방향 오차, 기동 명령과 실제 위치·속도, clean crossing 발생 시점, FIRE logit·발사 여부를 함께 그린다. 특히 “명령은 적절한데 세계가 기회를 잃는가”와 “정책이 기회를 만드는 방향을 내지 않는가”를 분리한다. 이미 사용한 280개는 **진단용**으로만 쓴다.
2. 원인에 맞춘 최소 수정 한 가지를 별도 계약·새 평가 namespace에 고정한다. 예를 들어 BC 입력분포/지도 target 오류면 그 부분만 고치고, 초기 BC는 좋지만 RL 중 무너지면 capturer-only 또는 초기 freeze/해제 실험을 작게 비교한다. 현재 pilot의 선택 문턱을 사후 하향하지 않는다.
3. 새 평가에서 발사 기회와 N이 함께 회복되는지 확인한 뒤에만 W6 본 학습 계약을 갱신한다. 공개 MAPPO reference 또는 자체 core 승인 근거, B-3/B-4 구현·architecture parity, 공통 초기화, seed/checkpoint/중단 규칙을 먼저 봉인한다. **그 전에는 대규모 joint 재학습을 재개하지 않는다.**
4. Track B의 D2는 별도 로컬 F1-E 세계로 시작할 수 있으나, 위 Track A 감사의 결론을 흐리지 않도록 산출물·평가를 분리한다. 첫 결과는 성공률보다 paired 궤적과 first-hit 사건을 먼저 확인한다.
