# 2026-09-18 — Track B 착수: D0(106 G0 카드)·D1(toy DP) 완료, DP=전수 일치, strict band 존재(설계된 양성)

> **2026-09-22 사후 정정·후속:** 아래 D0 수치와 `106 r0` 표기는 9/18 당시의
> 작업 기록이다. 현행 계약은 [106 r3](../docs/106_mode_switch_g0_contract.md)·
> [105 r4](../docs/105_mode_switch_execution_plan.md)이다. 현재 net은 전개 완료 후
> `[t_FIRE+0.15, t_FIRE+0.45)`에서만 포획 가능한 이동 원판이며,
> `R_net=1.77 m`, `v_net=55 m/s`(20 m/s sweep)이다. 8.22 m는 시뮬레이션에서
> 계산한 전개 완료 시점의 중심 이동거리이지 실측 유효사거리가 아니다.
> B2 W5 판정은 9/22 PASS로 끝나 D2의 시간 게이트는 해제됐지만, D2 세계는
> 아직 구현되지 않았다. [9/22 현재 위치 노트](2026-09-22c_role_swap_capturer_bottleneck_current_gates.md)를 참조한다.

## 판정

- **D0 완료:** `docs/106_mode_switch_g0_contract.md` r0 — 105 §3의 10행 결정을 한 버전으로
  고정. kinetic = sacrificial contact (r=0.75 재사용, p_kill ∈ {0.7,0.85,1.0} sweep — 1.0
  단일 봉인 안 함), net = projectile 1발 (R_net 2.0 Xu anchor, τ_deploy 0.4 재사용,
  v_net/T_active/T_H 는 SYNTHETIC_EXPLORATORY), first-hit 우선순위 = 위반>breach>성공,
  비용 ρ_K ∈ {0.5,1,2,4,8}.
- **D1 완료:** `shepherd/mode_switch/toy_dp.py` + `shepherd/scripts/mode_switch_toy_dp.py`
  + `tests/test_mode_switch_toy_dp.py` (7/7 pass). 산출물 `artifacts/mode_switch/toy_dp/`
  (results.json + figA strict grid + figB rank reversal).
- **검산 결과 (105 §4.2 전부 통과):**
  - DP 도달가능 벡터집합 == 전수열거 (tiny T=3 과 default T=5 둘 다).
  - cue 완전 마스킹 → strict gap 0 (구조적: 경로 분기 소멸 → Π_rec ≡ Π_fixed).
  - 지배 mode null → reversal 0.
  - **q=0.5 잡음 cue → strict gap 0** (잡음 조건화 confound 가 이 toy 에선 안 생김 — 기록).
- **본 결과 (설계된 양성 — G2 증거 아님):** strict band = prior ∈ [0.2, 0.5] 에서 20/45 cell
  (극단 prior 는 pure doctrine 으로 충분, 중간에서만 recourse 필수 — 이론 예상과 일치).
  reversal 1 epoch: t=1 에서 cue=0→NET(prot .76), cue=1→KIN(prot .838) — 각 mode 가 자기
  branch 에서만 feasible 한 feasibility reversal. ρ 축은 feasibility 에 무영향 (비용은
  min-cost 비교에만 작용; JSON 에 cell 별 min_cost 저장됨).

## 구조 메모

toy 가 strict cell 을 내려면 **net-first 가 kinetic fallback 을 잃어야** 한다:
t_roe=1, τ_net=2 (net commit → resolve 때 ROE 창 이미 닫힘). τ_net ≤ t_roe 로 두면
net-first+fallback 이 너무 강해서 strict 가 사라진다 — F1-E 세계 설계에서도 같은
구조(사라지는 fallback)가 관건이라는 예고.

## 레지스트리

`shepherd/params.py` §10 신설: `mode_switch.toy.*` 15키, 신규 status
`SYNTHETIC_EXPLORATORY` + 신규 wired `registry-direct` (105 §3 규약). frozen-YAML
drift check OK (as_config 미소비 경로라 Track A 무영향).

## 다음

- Track A: **B2 stop rule 판정이 D2 gate** (artifacts/r2b/b2_scripted 는 아직 smoke 만).
- D2 (F1-E world) 는 판정 후에만 착수. 첫 결과는 궤적 시각화부터 (viz-first).
