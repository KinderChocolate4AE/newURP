# 2026-09-25b — CLBC1-F2 판독: STOP_F2, 조준 분산은 큰 병목이었지만 남은 병목은 robust FIRE decision

**봉인 판정:** manifest `567f134a862335ce`의 결과 전 gate에 따라 **`STOP_F2`**다. lineage, pairing, finite, completion, exact CLBC1 parent, single-factor identity, authoritative FIRE logging, budget은 모두 PASS다. 두 seed 모두 표본각·robust-ready FIRE·N·crossing 조항을 통과했지만 SPENT_FAIL 비증가 조항을 실패했다. 기존 `NO_SELECTION`, `STOP_F1`, `STOP_CLBC1`은 유지하며 capturer-only RL 계약은 열리지 않는다.

정본은 `artifacts/marl/b0_v3_capturer_clbc1_f2/readout.json`이다. pre-result code는 `549a4fa`, harvest는 `1253cd8`이며 실행 코드와 manifest는 harvest에서 바뀌지 않았다.

## 1. 결과

| seed | arm | N | robust FIRE | FIRE | SPENT_FAIL | crossing ep | sampled↔mean 중앙값 |
|---|---|---:|---:|---:|---:|---:|---:|
| 0 | control | 26 | 26 | 75 | 49 | 87 | 29.04° |
| 0 | F2 low std | **58** | **58** | **171** | **113** | **189** | **7.62°** |
| 1 | control | 27 | 27 | 85 | 58 | 97 | 27.81° |
| 1 | F2 low std | **63** | **63** | **189** | **126** | **205** | **7.43°** |

F2는 의도대로 작동했다. 표본 오차가 약 28~29°에서 7.4~7.6°로 줄었고, N은 seed0에서 26→58, seed1에서 27→63으로 늘었다. 그러나 FIRE도 75→171, 85→189로 늘어 SPENT_FAIL이 각각 49→113, 58→126으로 증가했다. FIRE→N 전환율은 seed0 34.7%→33.9%, seed1 31.8%→33.3%로 거의 변하지 않았다. F2는 포획 가능한 상태에 들어가는 빈도를 늘렸지만, 발사 한 번의 조건부 품질은 개선하지 않았다.

paired 결과에서 F2만 발사한 episode는 seed0 105개(N 34, SPENT 71), seed1 113개(N 34, SPENT 79)다. clean N discordance는 seed0 F2-only/control-only 41/9, seed1 45/9다. 큰 순증은 실재하지만, 새로 열린 발사의 약 2/3가 탄을 소비하고 실패했다.

## 2. 실제 FIRE judge

이번 실행은 정책 입력 observation의 v_shot과 별도로 `env.step`이 FIRE를 수락한 바로 그 step의 판정을 기록했다.

- 520개 accepted FIRE 전체에서 authoritative `robust_ready`와 최종 N이 정확히 일치했다.
- boxed FIRE는 0건이었다.
- F2 성공 FIRE의 authoritative v_soft 중앙값은 두 seed 모두 1.0, SPENT FIRE는 약 0.967~0.973이었다.
- F2 명령축 오차 중앙값은 성공과 SPENT 모두 약 7.5~8.5°였다. 실제 자세 오차는 성공 약 3.1°, SPENT 약 5.1°로 차이는 있지만 둘 다 cone 반각 12.2° 안쪽이다.

따라서 남은 실패를 단순한 조준축 cone 이탈로 설명할 수 없다. soft score가 높은 상태에서도 robust reachable set 전체가 cone 안에 들지 않아 `v_worst=0`인 경우가 많다.

## 3. 관측과 실제 judge의 일관성

정책 입력 `v_shot_worst`와 authoritative robust 판정은 520 FIRE 중 514건에서 일치했다. F2만 보면 360건 중 355건이 일치한다.

- F2 N 121건 중 정책 입력 v_worst=1: 119건
- F2 SPENT_FAIL 239건 중 정책 입력 v_worst=1: 3건
- 나머지 불일치는 입력-only 3건, authoritative-only 2건이다.

이전 trace에서 발견한 step-seed 재평가 차이는 실재하지만 현재 실패의 주원인은 아니다. 정책이 받은 observation만으로도 robust-ready와 soft-only FIRE를 거의 분리할 수 있었다.

## 4. 기제 판정

F2로 residual aim sampling 병목은 크게 줄었다. 현재 일차 병목은 **FIRE head가 soft crossing에서 발사하도록 학습되어, observation의 v_worst=0인 상태에서도 Bernoulli FIRE를 허용하는 것**이다. 원래 BC 교사의 FIRE label과 환경 FIRE gate가 soft threshold를 사용한 결과와 일치한다.

다음 최소 후보는 CLBC1+F2 aim을 고정하고 FIRE head만 robust-ready label로 다시 지도학습하는 단일요인 실험이다. 세계의 FIRE gate를 바꾸거나 inference에서 외부 규칙으로 발사를 억제하면 다른 세계 또는 scripted 보조 정책이 되므로 우선 후보로 삼지 않는다. 새 실험도 fresh namespace, 두 seed, paired control, 결과 전 gate가 필요하며 `N 증가`, `SPENT_FAIL 감소`, `robust-ready FIRE 보존`, `H_illegal=0`을 함께 요구해야 한다.
