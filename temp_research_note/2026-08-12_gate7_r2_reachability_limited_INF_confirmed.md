# 2026-08-12 — 게이트 7 r2 판정: G7-1 PASS — reachability-limited ①-B (전 primary 셀 certified-INF ≥ 0.97, ΔU ≡ 0)

계약 = `docs/79` r2 (판독 표 결과 열람 전 봉인) · 구현 = `gate7_relaxation.py` (unit gates G7-A~F 전부 PASS) + `gate7_pilot_adapter.py` · tranche = 미접촉 ep 20..39 (dev set 0..19 제외).

## 1. 결과 표 (셀당 원래-AMB 100 상태, invalid 0)

| chi | kappa | closed@h→h/2→h/4 | n_sigs=0 | U4 med (=U1 med) | ΔU max | margin med |
|---|---|---|---|---|---|---|
| 0.8 | 0.2 | 0.96→1.00→**1.00** | 97 | 0.286 | **0.000** | 0.614 |
| 0.8 | 1.1 | 0.75→0.92→**0.95** | 91 | 0.391 | **0.000** | 0.509 |
| 1.2 | 0.2 | 0.97→1.00→**1.00** | 98 | 0.202 | **0.000** | 0.699 |
| 1.2 | 1.1 | 0.76→0.89→**0.98** | 82 | 0.208 | **0.000** | 0.692 |
| 1.6 | 0.2 | 0.93→1.00→**1.00** | 93 | 0.114 | **0.000** | 0.786 |
| 1.6 | 1.1 | 0.79→0.93→**0.97** | 77 | 0.104 | **0.000** | 0.796 |

- **G7-1 predicate (docs/79 r2 §5): PASS** — primary 셀 chi{1.2,1.6}×kappa{0.2,1.1} 전부 certified-INF ≥ 0.97 (기준 0.95) · AMB 잔여 ≤ 0.03 · refinement 안정 (per-state monotone, invalid 0).
- **판독 표 1행 (reachability-limited ①-B) 정확히 일치**: 대부분 n_sigs=0, U4 ≡ U1 ≡ baseline, **ΔU 는 600 상태 전부에서 정확히 0** — blocker 수의 한계효용 부재가 아니라 **τ=0.3s window 내 인과 도달 자체 부재**.
- 깊게 닫힘: U4 중앙값 0.10–0.39, 인증 여유 중앙값 0.51–0.80 ("0.8999 INF" 아님). baseline 이 chi 에 단조 (0.29→0.20→0.11) — 1/chi 물리와 정합.

## 2. 판별력 증거 (내부 control 3종 — "전부 닫히는 공허한 게이트" 반증)

1. **미폐쇄 10 상태의 구조가 전부 동일**: n_sigs=1 · frac_bad_touched ≈ 1.0 · U=1 — **limiter 가 snapshot 에서 이미 escape bundle 근방에 있던 상태**. 게이트 7 은 인과 도달이 실재하는 상태를 닫지 않는다. 전원 kappa 1.1 (큰 kill 구) 에서만 발생 — 물리 정합.
2. **FREE 상태 실데이터 positive control**: chi0.8 FREE (V0=0.918) → U4_bound = 0.918 (V0 와 정확히 일치, soundness 등호) — 닫히지 않음. 단 표본 1 (FREE 는 engaged 의 2–3%라 희소).
3. chi0.8 AMB 대량 폐쇄는 **selection 효과로 해소** (판독 표 최하단 경고 행 발동 → 조사 → 해소의 순서 기록): AMB 정의 자체가 V0<θ 라 causal reach 부재 시 U≈baseline<θ 로 닫히는 게 정합. chi0.8 의 판별 신호(V0≈1)는 FREE 상태에 있고 이는 입력에서 구조적으로 제외됨. 원래 control 기대문이 AMB-only 입력에 대해 오보정이었음.

## 3. 확정 문장 (docs/79 r2 상한 — 이 이상 금지)

> Within the registered fixed-state static-blockade model, and for states induced by the tested reactive scripted attacker distribution, **up to four path-limiters cannot recover certified net-capture feasibility in the high-chi regime within the registered 0.30-s deployment window** — not because of diminishing blocker-count returns (ΔU ≡ 0), but because **no reachable blockade configuration with causal influence on the escape bundle exists from the sampled snapshot states** (n_sigs = 0 in 77–98%).

- 금지 유지: "협력으로도 안 열린다" (채널 (ii)(iii) 미측정) · τ 확장 단조 주장 (τ 는 양측 reach 를 동시 증가) · "chi is governing parameter" (게이트 10 iso-Π 전).
- 시스템 설계 함의: 설계 변수가 "몇 기" → **"언제부터 shaping"** 으로 이동. 미폐쇄 10 상태(사전 배치된 limiter)가 그 방증. dynamic shaping (발사 가능 snapshot 을 미리 만드는 문제) 은 게이트 7 측정 대상 밖 — H2/H3 논쟁과의 접속 지점.

## 3.5 (같은 날 추가) 명칭 정정 — ①-B 세분화: 확정된 것은 **①-B1** 뿐

- **①-B1 = terminal-blockade infeasibility** (오늘 확정): commit 후 0.30 s window
  에서 사전 배치되지 않은 limiter 의 신규 개입 불가. "①-B = 협력 불가" 약칭 폐기.
- **①-B2 = pre-commit dynamic shaping infeasibility** (미확정 — MARL/채널 ii·iii
  의 질문. 게이트 7 은 정의상 이걸 측정하지 않음).
- **논문 서사 재배치 (약속 유지 — 오히려 완성)**: 지도(feasible/infeasible) =
  shaping 의 목표 집합 정의 (limiter 무관한 net 물리 — chi 경계·V0 붕괴 층은 이번
  논쟁과 독립적으로 생존) → 게이트 7 = "terminal 개입으로 shaping 을 대체할 수
  없다" (**shaping 의 필요성**, ①-B1) → T_lead 실험·MARL = "목표 집합에 실제로
  몰 수 있는가" (**shaping 의 가능성**, 미해결). 원 spine "Dynamic Capture
  Viability Shaping" 과 정확히 합치.
- 정확한 한 문장 (영문, 리뷰어 합의): *"The Gate-7 result does not show that
  MARL-based cooperation is infeasible; it shows that, once the net-deployment
  decision is made, the remaining 0.30-s window is too short for
  non-prepositioned limiters to causally reshape the escape geometry. Any useful
  cooperation must therefore act before commit by creating a favorable capture
  state."*
- 다음의 싼 실험 (MARL 재학습 아님): **T_lead probe** — T_lead ∈ {0, 0.5, 1, 2, 4} s
  동안 scripted cooperative controller 로 limiter 사전 기동 허용 → commit snapshot
  에서 certificate 재평가. 게이트 7 은 T_lead=0 극단의 측정이었다.
  **정제 정의 (2026-08-12 합의)**: T_lead = t_commit − t_shaping,onset — 실제
  closed-loop attacker 상호작용이 있는 pre-commit horizon. **primary outcome 은
  capture rate 가 아니라 commit-state 분포의 이동**: T_lead ↦ Pr(z_commit ∈
  C_feasible) — shaping lead time 증가에 따라 commit 상태분포가 certified feasible
  set 쪽으로 이동하는가. (보조: n_sigs / L4 / U1<θ≤U4 등장 시점 T*_lead.)

## 3.6 증거 수준 분리 규율 (문서 전반 적용 — 2026-08-12 고정)

| 명제 | 증거 수준 | 인용 규칙 |
|---|---|---|
| **B1** terminal-blockade infeasibility | **certified / confirmatory** (게이트 7 r2, G7-1 PASS) | scoped headline 그대로 |
| **B2** pre-commit shaping feasibility | **open question** | 어떤 방향으로도 확정 서술 금지 |
| 과거 MARL null (0/300 · 0/164) | B2 를 부정하는 증거가 **아님** — 기존 policy/configuration 이 B2 를 실현 못한 **motivating failure** | ★ **MARL null 과 게이트 7 을 나란히 놓고 "두 증거가 cooperation impossibility 를 지지" 구조 금지.** 올바른 서사: *"prior MARL failure motivated identification of the missing mechanism; Gate 7 then localized that mechanism temporally to the pre-commit phase."* |

연구 전체를 정리하는 문장 (합의): *"MARL is not asked to rescue an infeasible
shot during deployment; it is asked to steer the pre-commit state distribution
toward the certified capture set."* / 구조 3행: **Map tells you where to get.
Gate 7 tells you you cannot wait until the shot to get there. T_lead/MARL asks
whether cooperation can get you there beforehand.** KSAS 원고는 이 논쟁으로
재수정하지 않는다 (core claim = limiter-independent capture physics).

## 4. 다음

- **서버 확장** (docs/79 §4-2): 40-셀 격자 전체의 AMB 질량에 adaptive 적용 (tmux + ntfy, long-run policy). 로컬 pilot 배선·판정 전부 유효하므로 결과 방향 무관 진행.
- 이후 [G] 게이트 10 iso-Π → 12 refinement → 13 cooperation audit → 14 certified map.
- τ ∈ {0.3, 0.4, 0.5, 0.6} sweep 은 비확증 sensitivity 로 별도 (main 과 분리).
- FREE positive control 표본 확대 (n=1 → 수십) 는 서버 확장에 끼워 넣기 (비용 미미).

파일: `results/phase3/gate7_pilot_r2_{chi08,chi12,chi16}.json` (+ .log, r3.3 스탬프) · `gate7_unitgates.json`.

## 5. (2026-08-13 추가) 서버 full 20셀 확장 완료 — B1 은 map-wide · FREE control 102 상태 전부 sound

`gate7_full_{0_5,5_10,10_15,15_20}.json` (서버 4샤드, CPU, ep 20..39, free-control).

- **유효성**: 전 20셀 invalid 0 · FREE positive control **102 상태 (chi0.4 셀당 20 + chi0.8 셀당 5–6) 전부 sound_viol 0 · n_closed 0** — "전부 INF 로 만드는 장치" 반증이 n=1 → n=102 로 확대.
- **B1 은 map-wide**: closed@h4 0.93–1.00 (전 20셀) · n_sigs=0 69–98% · U4 중앙값이 chi 에 단조 (0.43–0.48 → 0.29–0.46 → 0.20–0.23 → 0.09–0.12 → 0.07–0.08). reachability-limited regime 이 격자 전체에서 유지.
- **ΔU 최초 비영**: chi 2.0 · kappa {0.8, 1.1} 에서 dU_max 0.001/0.003 — 존재하나 무시 가능 (θ 회복 요구량 ~0.8 대비). B1 판정 불변.
- **재현성 판정**: 로컬↔서버 중복 6셀 중 집계치 5셀 상이 → 조사 결과 **rng 소비 순서 인공물** (프로세스 내 셀 위치에 따라 같은 AMB 풀에서 다른 100개 표집 — `rng.choice` 가 선행 셀 수에 의존). **공통 (ep,t) 상태 131개에서 U4/U1/n_sigs 값 불일치 0** — 물리·certificate 는 플랫폼 간 bit-재현. 교훈: 집계 재현성 비교는 상태 단위로 할 것 (per-cell fresh rng 파생이 더 나은 설계였음 — 결과 무영향이라 코드 불변경).
- 다음 = [G] 게이트 10 iso-Π. T_lead probe 는 그 뒤 (§3.5).
