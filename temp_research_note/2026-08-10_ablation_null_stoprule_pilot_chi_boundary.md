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

## 4. (2026-08-12 추가) GPT 교차검증 v2 적분 — 분기 규칙·문구 정정

하네스 = `ANDES/URP/gpt_crossval_harness_v2_phase3_coop_null.md` · 전문 적분 = `third_party_feedback.md` §19 (v0.9).

1. **κ 불감 → "예측 미시험" 정정 (로컬 검증 완료)**: ρ=1.77 동결값 → 발현 예측 r_kill≈3.0 은 **κ*≈1.69 > pilot 최대 1.1**. 시험 범위 전체가 pre-onset. 금지 문구: "채널 세기 강건성"·"kappa robustness". 허용: "no κ sensitivity over the tested pre-onset range". §2 의 "채널 세기 강건성 방향 실측" 서술은 이 항으로 대체.
2. **게이트 7 단독으로 ①-B 확정 불가**: 게이트 7 = 같은 construct·같은 상태분포에서 상한만 조임 = **H4-upper 만 판정**. H2(construct truncation)·H3(반응 문법 → state-support bias)는 원리적으로 못 닫음. AMB→INF 여도 확정 가능한 최대 문장 = scoped claim ("등록된 fixed-state static-blockade + V3 상태분포 한정, N 1→4 회복 불가"). "협력으로도 안 열린다" 는 H3 닫기 전 금지.
3. **H3 정제**: "무반응 attacker" 버전 기각 (route_gain≥0.2 전 에피소드 closed-loop). 생존형 = "반응 basis 1종(각도-갭 비끼기)이 만든 state-support 선택 편향". 결과 A/B 는 solver 수준 조건부 독립·상태생성 수준 공통원인 (partial dependence — '두 leg 독립' 함정의 동종·부분형).
4. **χ 경계**: correctness 는 순환 아님(sound necessary condition), **discovery claim 만 위험** — pre-screen 이 aτ²/2 항을 공유. 3-arm audit (P0 무스크린 / P1 현행 / P2 aτ²/2 항 제거, 동일 snapshot) 전엔 "경계를 발견했다" 서술 금지.
5. **새 실행 순서 ([F] 앞 진단 삽입)**: χ pre-screen audit → **off-manifold certificate probe** (χ≈1.2 상태 100–200개 × 섭동 4축: 감속/heading/횡속도/dwell 위상 — rollout 불필요, 질문 = 근방 COOP island 존재 V1<θ≤L_N?) → (island 발견 시만) 300ep 2×2 reaction×coordination probe (deterministic controller, MARL 금지) → 게이트 7. island 0 이면 H3 급락·①-B 실질 강화, island + scripted controller 도달 가능이면 ①-B 즉시 중단.
6. 심사자 working odds: ①-B 55 : 재설계 45. 프로젝트측 반론 3건 (frozen-Z counterfactual 은 진단 한정 / posterior % 는 수사 / richer attacker A1 의 역-허수아비 위험) 은 §19.6 에 기록.

## 5. (2026-08-12 추가) F-0a·F-0b 실행 결과 — 스크린 무죄 (Case 1) · COOP island 0 · F-0c 조건 미충족

구현: `shepherd/scripts/f0a_prescreen_audit.py` · `f0b_offmanifold_probe.py` (선언 = 각 모듈 docstring, 결과 전 고정. 로컬 실행 ~35분, r3.3 스탬프).

### F-0a — chi pre-screen 3-arm audit: **Case 1 (경계 실재)**

| chi | pass P1 | pass P2 (aτ²항 제거) | delta | P1-거부 표본 | false-INF |
|---|---|---|---|---|---|
| 0.4 | 0.045 | 0.044 | 1 | 42 | **0** |
| 0.8 | 0.122 | 0.109 | 14 | 42 | **0** |
| 1.2 | 0.115 | 0.105 | 10 | 42 | **0** |
| 1.6 | 0.088 | 0.081 | 7 | 42 | **0** |
| 2.0 | 0.087 | 0.078 | 8 | 42 | **0** |

- **false-INF 0/210**: 스크린이 거부한 상태를 full solver 로 재판정해도 전부 INF (G=0) — 스크린 soundness 실측. P0 (무스크린) 지도는 현행과 동치였을 것.
- delta 상태 (aτ²/2 항이 살린 상태) 37건 전수: FREE/SINGLE **0** (전부 INF 13 / AMB 24, LN 전부 0.0) — 이 항이 경계를 제조하지 않음. P1↔P2 pass-rate 차 ≤ 0.013.
- **판정: chi 경계 sharpness 는 스크린 주입이 아니라 certificate 실재** (교차검증 §19.3-2 의 Case 1). "경계 발견" 서술 금지 해제 — 단 caveat 병기: 표본 audit (셀당 42) · kappa 0.5 · N=1 슬라이스.

### F-0b — off-manifold probe: **island 0/1300**

- chi 1.2 × kappa {0.2, 0.5, 0.8, 1.1} × N=4, base 100 상태 (engaged 표집) × [base + 섭동 12 (감속 ½·¾ / heading ±10~30° / 횡속도 ± / apex 쪽 10·25% 이동)] = **1300 평가. COOP island 0. LN_max = 0.000 (전 평가 identically 0)**. LN≥θ-but-INF 도 0.
- **선언된 읽기 (docstring 4) 그대로: H3 급락 — 반속·±30°·apex 25% 접근까지 밀어줘도 N=4 constructive 가 열리는 상태가 근방에 없다.** ①-B 실질 강화. **F-0c (2×2 reachability probe) 는 조건 미충족으로 skip** (island 존재 시에만).
- 정직 caveat 2건: (i) LN 이 θ 미달이 아니라 **정확히 0** — constructive 후보 2종(probe 4점 + hold)이 g=1 을 전혀 못 만든다는 뜻이라, **H4-lower (후보 성김) 는 이 probe 가 닫지 않는다**. 완결은 게이트 7 (상한) + 필요시 richer constructive (하한). (ii) base 상태는 여전히 V3 분포 — probe 는 그 국소 근방의 존재/부재 진단 (선언 5).

### 다음: **게이트 7** (F-0a Case 1 + F-0b island 0 으로 진입 조건 충족 — §19.4 순서 그대로)

게이트 7 AMB→INF 시 확정 문장은 여전히 scoped claim 상한 (§4-2). 파일: `results/phase3/f0a_prescreen_audit.json` · `f0b_offmanifold_probe.json` (+ 각 .log).
