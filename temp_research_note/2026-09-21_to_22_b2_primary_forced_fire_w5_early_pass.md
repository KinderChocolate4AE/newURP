# 2026-09-21~22 — B2 본 실험, forced-fire, W5 조기 판정

**상태:** B2 측정 완료, W5 **PASS**. PASS는 MAPPO 설정 pilot 착수 허용이며 협력 성능이나 학습 성공의 판정이 아니다. 모든 날짜·시각은 KST 커밋 시각이다.

## 시간순 사건과 계보

| 시각 | 사건 | 정본 |
|---|---|---|
| 9/21 23:36 | 8개 primary shard, 100,800 ep 수확. `b2_check --expect-commit fd4eb19`의 5축 모두 PASS. 50,400 CRN scenario × 두 arm, 결손·중복·미완주 0 | `121d92d`, [manifest](../artifacts/r2b/b2_scripted/manifest.json) |
| 9/22 00:27 | primary 판독 저장. 측정 결과이며 W5 판정과 분리 | `638db52`, [readout](../artifacts/r2b/b2_scripted/readout.json) |
| 9/22 00:39~01:48 | 비인가 engagement 재생 감사와 별도 forced-fire 436 probe. 같은 랩서버 재생 3/3 일치, intervention 전 동일성 PASS | `9968bfd`, `a5355a7`, [forced-fire readout](../artifacts/r2b/b2_scripted/forced_fire_readout.json) |
| 9/22 01:53 | Amendment A1: `H_illegal`을 PRE/PENDING 중 point-contact 또는 활성 swept resolver가 감지한 **비인가 kinetic engagement**로 정정. “불법 충돌”이라는 축약 폐기. 코드·B0 hash·결과는 그대로 | `49b358c`, [docs/108](../docs/108_b0v3_amendment_a1_illegal_engagement.md) |
| 9/22 03:44 | W5 투자 판정 PASS 봉인 | `073c05e`, [docs/107](../docs/107_w5_stop_rule_decision_draft.md), [decision](../artifacts/r2b/b2_scripted/w5_decision.json) |

## B2 primary: 거의 같은 net 성공률, 다른 doctrine 비용

| 50,400 episode/arm | SOLO | RULE_COOP |
|---|---:|---:|
| clean net capture `N` | 26,763 / 50,400 = 0.5310 | 26,866 / 50,400 = 0.5331 |
| FIRE | 48,853 / 50,400 = 0.9693 | 48,935 / 50,400 = 0.9709 |
| 비인가 kinetic engagement `H_illegal` | 0 | 2,840 / 50,400 = 0.0563 |
| 허가된 fallback `H_fb` | 29 | 559 |

clean N의 순차이는 RULE 쪽 **+103/50,400 = +0.0020**뿐이다. 쌍 비교에서는 SOLO-only N 3,472, RULE-only N 3,575로 서로 다른 결과가 7,047쌍이었다. c5 arc가 결과를 많이 바꾸지만 양방향 churn이 거의 상쇄된다. cell×seed 부호는 RULE 우세 28, 열세 14, 혼합 14로 일관된 우세 영역도 없다. `H_fb` 증가를 clean N 증가에 합치지 않는다. SOLO의 `H_illegal=0`은 limiter hold가 만든 구조적 대조다.

forced-fire는 **436/436 발사, net 회복 0/436**이었다. 결과는 `F_other` 392, `H_illegal` 29, `H_fb` 15. 사전 지정된 boundary-band/no-FIRE 개입에서 FIRE gate만 제거해도 실패가 복구되지 않았다. 따라서 이 표본의 주된 병목은 gate censoring보다 post-FIRE 도달·제어 쪽이다. 이것은 다른 발사 정책 전체의 불가능성 증명이 아니다. forced-fire는 primary와 별도 계정이므로 pooling하지 않는다.

## W5 판정의 정확한 범위

RULE_COOP clean-N `χ50`이 **14/14행**, 두 λ slice 각각 **7/7행**, 전 행 **3/3 seed**에서 추정되고 censoring은 0이었다. 봉인 판정은 PASS: 현재 A2-nominal B0 v3 세계에서 경계를 측정할 수 있으므로 MAPPO hyperparameter pilot에 투자할 수 있다는 뜻이다. c5 협력 규칙의 우위, 학습된 정책의 경계 이동, 외부 물리 타당성을 인정한 것이 아니다. W5 초안은 결과 전 작성됐지만 당시 미추적이어서 VCS 시각만으로 confirmatory 사전등록을 증명할 수 없다는 점도 docs/107에 남겼다.

원래 [89 §7](../docs/89_research_plan_r2_hybrid_marl.md)은 B2를 W4(9/29~10/5), W5 판정을 10/6~10/12로 배치했다. 실제 판정은 **9/22 조기 완료**다. 이를 뒤 일정 전체가 자동으로 앞당겨졌다는 뜻으로 쓰지 않는다. 후속은 [같은 날 pilot 기록](2026-09-22b_mappo_preflight_pilot_no_selection.md)으로 이어진다.
