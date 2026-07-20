# 25 — C-1 회랑 해부 (③-lite, seed 1100) — bank builder 진단 근거

> 2026-07-19, docs/09 (xxx)+(yyy). 도구 = `shepherd/scripts/c1_dissect.py`(재사용 — ③-full bank clustering에 재활용). 목적 = seed 1100 회랑의 비대칭 shaping 구조를 **진단**해 bank builder 탐색을 잘 설계.

> **⚠ 정정 ((yyy), 외부 리뷰 채택 — 초판의 "role×phase 저차원 search를 축으로" 과잉 표현 철회)**: **Boxer/shaper는 trajectory ablation에서 얻은 사후적·시점 국소 기능 라벨이며, 사전 정의되거나 지속되는 역할이 아니다. 해석·군집화·warm-start 진단에는 사용할 수 있지만 corridor 생성이나 정책 구조를 제한해서는 안 된다. 역할 분화는 상태 의존적이고 창발적으로 유지한다.** 즉 §5의 role×phase parameterization = **여러 proposal 중 하나(warm-start/진단)**이지 유일 search space도, 정답 구조도, MARL 정책 구조도 아님. bank 생성기 = role-agnostic·표현력 있는 knot-CEM 유지(비대칭·phase 표현 가능하면 족함), 학습 = 역할 창발(파라미터 공유 + 상태 조건).

## 1. 기전 — feasible-set 압축 vs cone-alignment의 knife-edge

seed 1100(A2·속도 20·공격자 직진, pre-commit dodge 없음)의 타임라인:

| t | v_soft | p_feas | n_feasible | 해석 |
|---|---|---|---|---|
| 4–5 | 0.10 | 1.00 | 2000 | feasible 전개, cone 밖 |
| 6–9 | 0.04→0.21 | 0.97→0.18 | 1941→351 | **압축 진행**(p_feas 단조 감소), 아직 cone 밖 |
| **10** | **1.000** | **0.0016** | **3** | **knife-edge: feasible sliver 3개가 전부 net cone 안** → eligible |
| 11+ | 1.000 | 0.000 | 0 | 완전 boxed(발사 후) |

회랑 = **feasible set을 sliver(≈3/2000)까지 조이되 그 잔여가 전부 finisher cone에 정렬되는 단일 프레임.** 한 스텝 전(t=9): sliver 아직 큼(0.18)·대부분 cone 밖(v_soft 0.21). 한 스텝 후(t=11): 완전 boxed(p_feas 0). fresh-CRN 300/300 견고((www)).

## 2. 역할 구조 — 3 boxer + 1 shaper (비대칭)

t=10 drop-one 귀속(all4: p_feas 0.0016·v_soft 1.000):

| 제거 | Δp_feas | drop 시 v_soft | 역할 |
|---|---|---|---|
| L0 | **+0.068** | 0.098 | **BOXER** |
| L1 | **+0.103** | 0.015 | **BOXER** |
| L2 | **+0.217** | 0.020 | **BOXER** |
| L3 | +0.002 | **0.444** | **SHAPER** |

- **L0·L1·L2 = boxer**: 제거하면 feasible 7~22% 재개방 + v_soft 붕괴 → reachable set을 cone 안으로 압축.
- **L3 = shaper**: 제거해도 p_feas 거의 불변(+0.002 = bulk boxing 아님)이나 v_soft 1.0→0.444 → **잔여 sliver를 cone에 정렬(trim)**하는 비대칭 역할. corral 대칭 편대엔 이 역할이 없음.

## 3. Phase 구조 — compress → brake-and-shape (t=10 flip)

limiter별 가속을 공격자 프레임 radial(공격자 향 +)/tangential 분해:

- **Phase 1 (t≤9, compress)**: 전 limiter radial **+12~+22**(공격자로 접근) + 큰 tangential(16~35, 선회하며 조임). p_feas 단조 감소.
- **Phase 2 (t=10, brake-and-shape) — mean radial 부호 반전(flip)**: L0/L1/L2 radial **−30/−7.5/−26**(급제동)·tangential 붕괴(4~7); **L3만 tangential 유지(23.1)** = 채널 성형. 이 프레임에 v_soft가 1.0로 점프.

## 4. corral vs CEM 결정적 차이

corral best(press2_block2) 동일 seed 1100 재생: **eligible 스텝 = 0** — p_feas 높은데 v_soft 낮음(t6–10 p_feas .95/v_soft .05) → 곧장 boxed(t12–14 v_soft 1.0/p_feas 0)로 **clean 창을 건너뜀**. 대칭 press는 잔여를 cone에 정렬하는 shaper가 없어 "전개(정렬 안 됨) ↔ 완전 boxed" 사이를 못 뀀. **CEM은 brake-3 + shape-1 비대칭으로 둘을 동시 달성.**

## 5. bank builder parameterization 권고 (이 해부의 목적)

288차원 blind CEM 대신 **role×phase 저차원**:

- **discrete**: shaper 지정 limiter 1개(4택) + boxer 3개.
- **Phase 1 (compress)**: boxer approach gain(radial-in) + tangential(선회) gain.
- **switch time** τ_switch(compress→brake).
- **Phase 2 (brake-and-shape)**: boxer brake gain(radial 반전), **shaper channel angle**(net cone 기준 tangential 방향·gain).
- 연속 ~6–10 dim + discrete 1 → 288차원 대비 급감. CEM winner에서 warm-start(이 구조를 이미 실현) + fresh-CRN 게이트로 search.

이 parameterization이 bank builder(②)의 winner-local restart·near-miss-as-mean·저차원 knots의 축이 됨. ③-full = bank 전체를 이 role×phase 특징으로 clustering.

## 6. 캐비앗

- 단일 seed(1100) 구조 — 다른 nominal seed가 같은 3+1 구조인지는 bank(②)에서 확인(cluster 수 = 열린 질문). 공격자 직진(pre-commit)이 이 구조의 전제 — dodge/속도 변화 시 phase 타이밍 재적응 필요(R3 속도특이와 정합).
- shaper/boxer 귀속은 drop-one 근사(한계적 기여) — 상호작용 항은 미분리.
