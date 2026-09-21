# 2026-09-22 — MAPPO preflight와 8-run pilot: NO_SELECTION

**판정:** W5 PASS 뒤 허용된 hyperparameter pilot은 완주했지만 봉인된 후보 자격을 한 개도 충족하지 못했다. **본 3-seed campaign은 열리지 않았다.** B2 PASS와 pilot NO_SELECTION은 서로 다른 게이트다.

## 시간순 실행

| KST | 사건·지위 | 근거 |
|---|---|---|
| 04:11~04:12 | B0 v3 credit/termination interface preflight: CPU 128 step, optimizer update 1회, limiter commit head 없음, 유한값 검사 PASS. 학습 성능 증거는 아님 | `17baf59`, `f445377`, [docs/109](../docs/109_b0v3_mappo_pilot_preflight.md), [preflight](../artifacts/marl/b0_v3_mappo_preflight.json) |
| 04:39~04:48 | [docs/110](../docs/110_b0v3_mappo_hyperparameter_pilot_contract.md)과 [manifest](../artifacts/marl/b0_v3_pilot_manifest.json) 봉인, lineage guard 보강, 공통 BC dataset 확정 | `bfd6d8d`, `eb8bb87`, `226088f` |
| 04:48 이후 | 서버 smoke PASS, 이어 4 candidate × 2 seed의 full pilot 실행. 각 run 32,768 env step/64 update, 공통 BC hash와 평가 scenario signature 사용 | 사용자 서버 출력, [8-run readout](../artifacts/marl/b0_v3_pilot/readout.json) |
| 06:17 | 8/8 완주·계보 검사 PASS, 판독 `NO_SELECTION` 수확 | `8305099`, 같은 readout |

BC dataset `b48aad5eab4a92bd`는 clean N 에피소드에서 얻은 **597 state, FIRE positive 66, 26/28 boundary cell**이다. capturer pointing/fire head만 BC, limiter는 neutral mean에서 시작했다. `H_illegal` 에피소드는 positive BC에서 제외했다. 8개 full run은 코드 커밋 `226088f`, 평가 scenario signature `5b63d689cc4f3189`를 공유한다. 서버 smoke의 작은 32-sample dataset과 full BC dataset을 혼동하지 않는다.

## 봉인된 선택 문턱과 결과

평가는 각 seed마다 boundary 28 cell × 10 = **280 episode**, 후보당 2 seed의 평균이다. 자격 문턱은 평균 `P(N)≥0.10`, 평균 `P(FIRE)≥0.20`, 각 seed `P(N)≥0.05`, 평균 `P(H_illegal)≤0.0563`, 완주·유한값이다.

| 후보 | 평균 P(N) | seed별 P(N) | 평균 P(FIRE) | 평균 P(H_illegal) | 선택 |
|---|---:|---:|---:|---:|---|
| c0_base | 0.0321 | 0.0357 / 0.0286 | 0.1196 | 0 | 탈락 |
| c1_entropy | 0.0304 | 0.0393 / 0.0214 | 0.1411 | 0 | 탈락 |
| c2_low_lr | 0.0214 | 0.0214 / 0.0214 | 0.1054 | 0 | 탈락 |
| c3_no_pbrs | 0.0357 | 0.0214 / 0.0500 | 0.1321 | 0 | 탈락 |

네 후보 모두 N·FIRE 문턱에 못 미쳤다. c3의 수치상 최고 평균 N을 “선택 후보”로 승격하지 않는다. 이 차이만으로 PBRS의 해로움도 판정할 수 없다. `H_illegal=0` 역시 engagement 자체가 적은 정책의 결과일 수 있어 안전 우위가 아니다. 32,768 step에서 성과가 낮다는 결과를 더 긴 학습의 불가능성으로 일반화하지 않는다.

원래 [89 §7](../docs/89_research_plan_r2_hybrid_marl.md)은 pilot을 W5 PASS 직후, 본 학습을 W6~W9(10/13~11/9)에 두었다. pilot이 9/22 조기 완료돼도 **NO_SELECTION이 본 학습 진입을 막는다.** W6 training contract, 공개 MAPPO reference 처분, B-3/B-4 shared actor·architecture parity, 새 평가·중단 규칙은 여전히 열려 있다. 원래 pilot 평가 280사례를 본 뒤 문턱을 낮추거나 같은 표본으로 후보를 다시 뽑지 않는다.

병목을 좁힌 후속은 [역할 교체 진단·현재 게이트](2026-09-22c_role_swap_capturer_bottleneck_current_gates.md)에 기록한다.
