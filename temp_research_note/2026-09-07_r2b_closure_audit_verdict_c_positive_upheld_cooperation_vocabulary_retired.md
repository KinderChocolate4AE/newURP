# 2026-09-07 — R2b 종결 감사 판정: C_POSITIVE 실질 유지, 단 "협력" 기전 어휘 폐기 (B0 봉인 문장 amend) — 브리프 r3 = 등록 정본

외부 감사 (적대적) 판정 접수 → 전면 반영. 정본 = `docs/review_prompt_r2b_closure.txt` r3.

## 판정 요약

- **Q1 봉인 사슬 PASS-w-edits**: 과학 데이터 생성 사슬 온전. 단 C 판정 규칙의
  지위는 "B0-preregistered" 가 아니라 **"pre-outcome analysis rule,
  mechanically transplanted from the preregistered P1 rule"**. blindness 는
  timestamp 로 "회수 전 봉인"까지만 기계 증명 (seal 21:40:52 < 회수 21:44:43
  < 판독 21:46:20; 서버 생성은 선행) → "pre-retrieval locked per recorded
  workflow" 로 등록. proxy 도 pre-execution locked 표기.
- **Q2 FAIL — 핵심 교정**: B0 봉인 문장의 "cooperation-is-meaningless is
  rejected" · "exploitable cooperative geometry" 는 **C 구성이 지지 못 하는
  mechanism 어휘** (single-limiter / independent / coordinated 미분해) → 폐기,
  9.2 append-only amendment (선례: v1 "oracle upper bound" 폐기).
- **Q3 PASS-w-edits**: caveat c1 (witness-based lower bound 로 정정) · c4
  (**intended 14h resource gate not actually satisfied** — mis-specified
  estimator) 개정 + 신설 c7 (χ50 경계 추정 아님 — "+0.37 만큼 경계 밀림" 오독
  차단) · c8 (협력 필요성 미확립) · c9 (late-seal 지위).
- **Q4**: C047·C048 PASS-w-edits (문안 교정: "did not meet pre-specified
  criterion" / "cooperative" 삭제 / Δχ50 아님 명시), **C049 FAIL → 감사 교체
  문안으로 등록** (브리프 §6이 정본).

## 감사 대응 신규 증거 (이 세션 계산)

- **plan-class 분해**: Δp_CA +0.370 중 +0.3675 (99.2%) 가 accels-best class
  (1962판, in-class +0.524); intercept-best 818판은 **C_N == B_N 818/818
  완전 재생** (기여 0.8%); hold-best 20판 기여 0. → 해석 (2차 감사 톤):
  **gain 은 hold/intercept 재생만으로 설명되지 않고 accels-best class 에
  집중** — class 별 Σ(C_N−A_N) descriptive attribution 이지 기전 증거 아님
  (감사 §8d 해소, 협력 필요성 미확립 c8).
- **기각된 자체 주장**: "어떤 합리적 규칙에도 강건" · nosol 역전 "무해" 일반화.

## 가장 안전한 최종 결론 (감사 문장)

> rule-based null 은 limiter-control opportunity 의 부재를 뜻하지 않는다.
> "협력이 존재하고 rule 만 실패했다" 는 별도 기전 claim — **necessity
> ablation (single / independent / coordinated) 이 선행 조건** (브리프 §7-5
> deferred, docs/89 편입 여부 사용자 결정).

## 2차 감사 (같은 날) — 하향 4건 + 경로 확정 → 브리프 r4

- 하향: "규칙 무능"→"해당 rule 이 exploit 못함" · "협력 효과"→**limiter-control
  opportunity** (사슬 중간 칸 명칭) · attribution 톤다운 · η gradient 는
  "기회의 지도" 아니라 tested S_C 위 descriptive gradient.
- **최종 서사 정본** = 브리프 r4 §10.1 ("R2b separated controller failure
  from opportunity absence...").
- **경로 확정: R2b freeze → B0 v3 → MARL (docs/89).** necessity ablation 은
  조건부 카드 (논문이 cooperative shaping 을 title/claim 급으로 원할 때만).
- **전방 지표**: search-benchmark recovery R_rec = (p_learned−p_A)/(p_C−p_A),
  같은 S_C·world·semantics 한정, R_rec>1 가능 ("upper bound 회수율" 명명 금지).
  B0 v3 에서 정식 봉인.
- 저비용 진단 카드 (blocker 아님): 성공 plan counterfactual replay (한 기씩
  hold/제거) — plan 미저장이라 scenario 당 re-search ~6 min, 소표본만 유효.

## 사용자 트랙

- C047~C049 등록은 **브리프 r4 §6 문안 그대로** + R2b freeze.
- docs/89 의 동기 문장에서 "cooperative geometry" 계열 어휘 제거 필요 (§7-3).
