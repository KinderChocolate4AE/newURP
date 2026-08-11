# 2026-08-10 — ablation 완전 null (stop rule 발동) · pilot 본실행: chi 경계 0.8↔1.2 발견, COOP 신호 0

## 1. docs/71 LS-COMMIT ablation — 판정 (analyze_ls_commit 1회, 사전등록 그대로)

- **primary Δ_shape = 0.0 (전 confirmatory seed 1..4 동일)**. SHAPING regime (n=185
  paired) 에서 ls-live·ls-off 모두 p_net = 0.000. CI [0.0, 0.0], positive_evidence
  = false. index seed 0 도 동일 (0.0/0.0).
- **verdict (산출물 원문)**: "disabling commit did not recover measurable
  SHAPING-regime net-capture gain under the frozen learning contract → 본편 rescue
  search 종료 (docs/71 §3 stop rule)".
- 해석 한도: commit head 는 SHAPING 실패의 causal contributor 가 **아니었다**.
  마지막 learning-contract rescue 가 null → headline (LL 0/300 · LS SHAPING 0/164)
  교체 금지 조항 확정. Phase III 전환 동기가 사후적으로도 유지됨 —
  단 이 결과는 Phase III 를 *"motivate 하되 validate 하지 않는다"* (docs/74 §6).
- 파일: `results/iid_abl/` 12건 + `analyze_ls_commit.json` (band=ablation
  10300..10599, b_boot 10000).

## 2. coarse pilot 본실행 (40 셀 × 20 ep, 전 스텝 + 해석적 pre-screen, ~270k 상태)

### 핵심 관측 — **선명한 chi 경계 (0.8 ↔ 1.2)**

| chi | ep_FREE (20 ep 중) | engaged FREE | V0_max | LN_max |
|---|---|---|---|---|
| 0.4 | **20/20 전셀** | 0.21–0.28 | 1.00 | 1.00 |
| 0.8 | 10–14/20 | 0.02–0.03 | 0.97–1.00 | 0.98–0.99 |
| 1.2 | 0/20 (1 예외: kap1.1·N1 에서 1/20) | 0.000 | 0.53 | **0.00** |
| 1.6 | 0/20 | 0.000 | 0.26 | 0.00 |
| 2.0 | 0/20 | 0.000 | 0.14 | 0.00 |

- chi = a_att·τ²/(2ρ) (회피 변위/net 반경). **chi ≥ 1.2 에서 V0_max 가 ~1/chi 로
  단조 붕괴** (0.53→0.26→0.14) — 전개 지연 동안의 회피 변위가 net 반경을 넘어서는
  물리 경계와 정합.
- **kappa (kill 구 크기) 전 구간 불감**: 0.2→1.1 에서 행 동일 수준. 봉쇄 채널
  세기가 cheap 후보 배치에서는 결과를 전혀 못 바꿈 — §3.0 scope 선언의 "채널
  세기 강건성" 방향 실측 (단 constructive 후보 2종 한정).
- **coop_candidate ≈ 0 전셀** (유일 blip: chi0.8·kap0.8·N4 에서 0.002).
  N=1 → N=4 이득이 cheap 하한에서 전무.
- engaged 내 **INF (certified 불가) 0.48–0.67 지배**, AMB 0.21–0.47 잔존.

### 분기 판정 (docs/77 [E] 읽는 법 기준 — 잠정)

- **①-B (negative systems result) 방향 우세**: chi ≥ 1.2 의 480 에피소드에서
  cheap constructive 기회가 문자 그대로 0 + INF certified 질량 지배 + COOP 신호 0.
- **단 ①-C 잔여 리스크**: engaged AMB 0.35–0.47 (chi ≥ 1.2) 는 U_cheap (제거
  낙관) 이 열어둔 미해결 질량. 이건 게이트 7 (N-limited outer relaxation) 만이
  닫을 수 있다 — **AMB 가 INF 로 붕괴하면 ①-B 확정, 일부가 열리면 COOP 재검토**.
- 비싼 계산([F])의 지목 좌표 = **chi ∈ {0.8, 1.2} 경계대역** + 전 셀의 AMB 질량.

## 3. 다음 (docs/77 [F]~)

1. **게이트 7 continuous outer relaxation** — AMB 판정이 분기의 열쇠. 우선순위 1.
2. 게이트 12 boundary refinement 는 chi 0.8~1.2 에 집중 (Z_master 격자 내 선택만).
3. KSAS 추계 초록 (docs/75 §6): ablation null + chi 경계는 금지 문장 3종 피해서
   기술 가능.
4. OSF r3.3+r3.4 timestamp ✅ (osf.io/39gxw, 03b8b94) — 감사 체인 완결.

파일: `results/phase3/coarse_pilot_{0_10,10_20,20_30,30_40}.json` (r3.3 스탬프).
