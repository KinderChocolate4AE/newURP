# 리뷰 6 사이클 완결 — 감사 피드백 문서화·3자 판정·비준까지 하루에 닫음 (4be56f4)

**2026-08-08 · 리뷰 세션. 산출물 = docs/64 (감사 종합 피드백 + 판정 요청 7건)
+ docs/65 r1 (리뷰 6 판정 로그 + 통합 실행 큐, Hyunjun 비준 반영). 커밋
4be56f4 — push 는 로컬 권한 차단으로 미실행 (수동 push 필요).**

흐름: `artifacts/audits/` 감사 3종 → docs/64 로 종합 (판정 요청 7건 명시,
docs/61 동결·기잠긴 규율은 리뷰 스코프 밖으로 차단) → 외부 리뷰 6 → docs/65
판정 로그 → Hyunjun 비준 (같은 날) → r1 반영.

핵심 판정 (정본 = docs/65):

1. **리뷰 총평 채택**: 병목은 reward/threat 재설계가 아니라 — "MARL 이라
   부를 모든 코드 경로가 먼저 동일한 v3 세계를 실행해야 한다". 운영 규율로
   승격: train/eval/sweep/scripted 는 **동일 resolved world contract 를
   공유할 때만** 같은 실험 family.
2. **blocker 재편 승인**: 최상위 = train/eval contract parity (구 #1+#2
   통합, parity 필드 13종) · fresh-state 규율 blocker 승격 (legacy
   ckpt/norm restore 금지) · docs 정정은 hygiene 강등.
3. **CWC 원칙 비준, 값은 보류**: else=0 금지 + terminal→utility class 명시
   연결은 확정. `R(CWC)=R(NET_CAPTURE)` 는 **B1 semantics trace → B3 truth
   table 비준 후** 확정 (분기 3건 명문화).
4. **구조 수정 2건**: A4 parity 를 A4a(지금)/A4b(P92 후)/A4c(docs/63 후)
   로 분리 — 미존재 runner 를 미리 검사하던 dependency 해소. Phase B 는
   B1→**B3 비준**→B2→B4 (구현이 truth table 을 역정의하는 것 방지).
5. **문장 규율 갱신**: pre-fire "창" → "NK-밖 engagement opportunity 의 첫
   witness" 하향 · NK 42/42 engagement 어휘 · MARL gain/무이득 각각의
   금지 문장 (P88/P94 = controllability ≠ learnability) · coma_D =
   diagnostic only.
6. **신규 금지 2건**: P95 에서 route_gain 상향 금지 (semantic validity 검증
   이지 difficulty tuning 아님) · docs/63 F9 = runtime controller 의 env
   oracle 접근 금지 (offline TRAIN metric 튜닝만 허용).

다음 세션 = 18단계 사다리 [1]~[2]: A1~A3 runtime pass-through 복구
(train_m4/sweep_m4 R1/R2 · mission_eval standby/extra_cfg) → A4a manifest
harness + A5 fresh-state + A6 분류 (BLOCK/NON-EVIDENCE/trap). 그 다음 B1
CWC semantics trace. 새 실험 설계 없음 — docs/61 재오픈 없음.
