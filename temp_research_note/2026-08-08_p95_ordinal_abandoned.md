# P95′ RED — stop rule 발동, ordinal taxonomy 폐기 트랙 (사다리 [4]~[9] + 리뷰 7 사이클 완주)

**2026-08-08 · 실행 세션 2부. 커밋: 08c7a31(B2/B4) · 0bbf672(C/D hygiene) ·
657b330(P92) · a32a854(A4b) · a532f06(P93, 1100 확정) · f7a65c6(P95 RED) ·
f7e4cd0(리뷰7 프롬프트) · 06d4b59(docs/67+68 r0) · e14936c(r1 이행+P92′) ·
7715608(P93′) · c2f4957(P95′ RED). 전부 push 대기.**

하루 요약 (18단계 사다리 기준):

1. **[4] 완결**: docs/66 비준 → B2 (CWC=+b_net 명시 분기) + B4 (truth table
   테스트 10종, canonical = step10 proximity→step50 clean capture). 525 pass.
2. **[5]**: C/D hygiene — G03/G04/G05 해소, params 오기 4건, claim scan
   테스트(C10), coma_D diagnostic-only, registry RESOLVED 갱신.
3. **[6]~[8]**: P92 GREEN(draw_threat_v3 배선) → A4b(분포 hash pin +
   threat_layer 배관) → P93 PASS(1100 확정).
4. **[9] P95 RED** (medium>strong 역전, 14/30) → 리뷰 7 (3안 비교 프롬프트)
   → 판정: (a)경계재조정 기각·(b′)gain/sense 분리 채택·(c)지표변경 기각 →
   docs/68 r0 → Hyunjun 조건부 비준 (명칭 route-gain stratum · GREEN/RED
   해석 제한 · P93′ 필수) → r1 이행 + factorization v2 구현 (hash
   e048bd39→efeffcbf, pin 동일 커밋) → P92′ ALL PASS → P93′ PASS →
   **P95′ confirmatory 1회 = RED** (cruise PASS / sprint med 역전 /
   sprint_slowdown mean 역전).
5. **Stop rule 이행**: P95″ 금지·추가 탐색 금지·해석 제한 그대로 기록.
   원 P95 30판 = 봉인 유지. 성능 지표 전 과정 미열람.

★ **대기 중인 결정 (Hyunjun, docs/68 §3 stop rule 트랙)**:
route_gain 구간 처리 — (A) 무명 design bins 유지 (분포·draw 불변, 9셀
구조·셀별 공개 유지, ordinal 명칭만 전면 금지) vs (B) continuous nuisance
(U[0.2,0.8], 층 구조 제거 — 분포 hash 재변경 + P92″ 재실행 필요).
어느 쪽이든 MARL 진행 가능 (P95 계열 = taxonomy semantic gate, 학습 금지
아님 — docs/61 규율). 논문 서사는 "반응성 스펙트럼 층화 학습" →
"randomized-gain reactive attacker 분포 학습" 으로 강등, 한계절 문장 2개
고정 (docs/67 §5).

다음 큐: 위 결정 → TRAIN 분포 최종 동결/hash → docs/63 scripted baseline
설계·비준·동결 (리뷰 8 후보) → A4c → G smoke → MARL.
