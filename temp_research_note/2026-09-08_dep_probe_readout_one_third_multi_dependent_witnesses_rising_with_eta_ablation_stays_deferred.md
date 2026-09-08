# 2026-09-08 — dep-probe 판독: multi-dependent witness 32.9% (η 상승 경향) — 협력 어휘는 계속 폐기 유지, C_single ablation 은 카드로 존속

plan-level multi-limiter dependence probe (봉인 29bc681, 어휘 사전 선언) 판독.
**지위 = descriptive witness — necessity 증거 아님** (reoptimization 없음: 단독
실패는 "이 plan 의 단독 절단이 실패"이지 "단독 plan 불가능"이 아니다).

## 수치 (n=140, 전 셀 5판, 전부 full=NET_CAPTURE 재확인, code fcbf696 단일)

- **multi_dependent (¬solo_any): 46/140 = 0.329**
- solo_any: 94/140 = 0.671 · loo_all: 48/140 = 0.343
- n_solo_success 분포 {0:46, 1:44, 2:6, 3:3, 4:41} — 쌍봉: "특정 1기 결정적"
  (44) 과 "임의 1기로도 충분" (41) 공존.
- **η gradient**: multi_dep 0.25 (η2.1~2.7) → 0.30 (3.0~3.3) → 0.45~0.50
  (3.6~3.9). λ slice 무차이 (0.343 vs 0.314).
- 4기 전부 필요 (n_loo_success=0) 는 3판.

## 해석 (사전 선언 어휘 한도 내)

1. **협력 어휘 복권 근거로는 불충분** — 다수 (67%) 가 단독 재현 가능하므로
   C 의 gain 상당 부분은 single-limiter opportunity 로 설명될 여지. 어휘 규율
   (limiter-control opportunity) 유지.
2. **그러나 ablation 카드를 죽이지도 않는다** — 3분의 1의 multi-dependent
   witness, 특히 **고 η (어려운 영역) 집중 상승**은 "richer/multi-limiter
   control 이 hard regime 에서 중요할 수 있다"는 descriptive 단서. 논문에는
   witness 문장으로만 (necessity 금지).
3. **결정: C_single necessity ablation 은 계속 조건부 카드** (즉시 착수 안 함).
   근거: (i) 혼합 결과라 캠페인이 어휘를 복권해줄 기대값이 낮고, (ii) docs/89
   W2~W6 사슬 (B0 v3 → MARL) 이 우선이며 (iii) 학습이 성공하면 learned policy
   의 역할 분해가 같은 질문에 더 나은 증거를 낸다. 재고 트리거 = 논문 집필 시
   cooperative shaping 을 title/claim 급으로 원할 때.

## 파생 활용

- docs/89 학습 서사 보조 문장 (witness 톤): "in one third of the search
  successes — rising to ~half in the hardest η cells — no single limiter's
  action alone reproduced the capture." (필요 시 집필에서 사용.)
- 산출물: artifacts/r2b/c_dep_probe/shard00..07.json (140 records).
