# 2026-09-25c — CLBC1-F3 판독: robust FIRE head PASS, 잔여 오차는 MC draw flip

## 봉인 판정

Manifest `00a9e45ff4b0506d`, 실행 코드 `09f3e0b`, harvest `9274b8a`의 결과는 **`PASS_F3_TO_CAPTURER_ONLY_RL_CONTRACT_DRAFT`**다. lineage, pairing, finite, completion, exact F2 parent, collection support, FIRE-head-only identity, authoritative FIRE logging, budget이 모두 PASS이며 결과 전 gate의 모든 조항이 참이다.

기존 `NO_SELECTION`, `STOP_F1`, `STOP_CLBC1`, `STOP_F2`는 그대로 유지한다. 이 결과는 별도 capturer-only RL 계약을 작성할 자격만 열며 W6, PFSP 또는 learned cooperation 성과가 아니다.

## 결과

| seed | arm | N | FIRE | robust FIRE | nonrobust FIRE | SPENT | FIRE→N | crossing | H_illegal |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | F2 control | 67 | 151 | 67 | 84 | 84 | 44.4% | 177 | 0 |
| 0 | F3 robust FIRE BC | **79** | 80 | **79** | **1** | **1** | **98.8%** | 177 | 0 |
| 1 | F2 control | 59 | 170 | 59 | 111 | 111 | 34.7% | 204 | 0 |
| 1 | F3 robust FIRE BC | **78** | 79 | **78** | **1** | **1** | **98.7%** | 204 | 0 |

Held-out soft-gate 상태에서 control balanced accuracy는 seed0/1에서 0.667/0.625, FPR은 0.667/0.750이었다. F3는 두 seed 모두 balanced accuracy 1.0, FPR 0, TPR 1.0이다. 독립 FIRE MLP만 바뀌었고 조준 mean, `log_std=-2.3`, limiter, critic, normalizer는 bit-identical이다.

## Paired 전이

- seed0: 기존 N 67건을 전부 보존하고 SPENT 12건을 N으로 바꿨다. SPENT 71건은 발사를 억제한 뒤 PENETRATED가 됐다.
- seed1: 기존 N 59건 중 58건을 보존하고 SPENT 20건을 N으로 바꿨다. N 1건은 PENETRATED로 바뀌었고 SPENT 90건은 발사를 억제한 뒤 PENETRATED가 됐다.
- clean crossing episode 총수는 각 seed에서 control과 동일했다. 따라서 N 순증은 새로운 crossing 생성보다 FIRE 선택 개선에서 왔다.

## 잔여 3건과 환경 계약

F3의 nonrobust FIRE는 seed별 1건뿐이다. 두 건 모두 정책 입력은 `v_worst=1`이었지만 같은 step의 authoritative judge는 `v_worst=0`이었다. seed1에서 잃은 N 1건은 반대로 control 정책 입력이 `v_worst=0`인데 authoritative judge가 1이었다.

`shepherd/env.py`는 post-move observation을 현재 `step_seed`로 계산하고, 다음 action의 pre-move judge를 다음 `step_seed`로 다시 계산한다. 물리 상태는 같아도 finite Monte Carlo witness draw가 달라질 수 있다. `tests/test_fire_audit.py`는 이 재표본화를 명시적으로 허용하므로, 이번 판독에서 기본 환경을 수정하거나 봉인 F3 결과를 재해석하지 않는다. 결과적으로 F3에 남은 두 SPENT와 잃은 N 한 건은 FIRE head의 held-out 분류 실패가 아니라 관측 draw와 authoritative draw의 경계 flip이다.

## 해석 범위와 다음 단계

F3는 scripted hold limiter와 CLBC1+F2 aim에 의존한 BC-only capturer다. scripted launcher 성능 148/280과 직접 같은 정책이 아니며, 현재 N 78~79/280은 여전히 약 절반이다.

다음 허용 단계는 이 F3 초기화를 고정한 **작은 capturer-only RL 계약 초안**이다. 그 계약은 limiter를 scripted hold로 고정하고, capturer 행동만 PPO로 학습하며, scripted action을 PPO log-prob로 취급하거나 FIRE를 외부에서 강제하지 않아야 한다. fresh train/eval namespace와 결과 전 gate가 다시 필요하다.
