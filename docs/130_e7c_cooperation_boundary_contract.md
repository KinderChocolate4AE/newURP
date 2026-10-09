# 130 — E7-c: ②축 (협력) 이 경계를 미는가 — 전이 구간 2×2 (ρ 아래/위 × limiter 발사후-치명/무력)

- **일자**: 2026-10-08 · **상태**: **봉인 v1.1** (§7 해석표 추가 — 사용자 승인, 결과 전; v1 = 사용자 결재 "고정" 2026-10-08 — 교전 규칙 수정안
  포함; **E7-b 결과 전**). manifest = `fs1_e7_manifest.py` `build_e7c` (pin dry-run 전제 유지).
- **결정 근거**: E7-a′ (노트 10-08d) = scripted limiter 의 즉시 witness 폐쇄 몫 ≈ 0 (전 ρ,
  공격자 조건부) + 궤적 조형 경로 미측정. 연구 정체성 기여 ③ ("협력 조형이 경계를 미는가")
  의 증거 = 현재 0. 당초 설계 순서는 **limiter 협력 → net 시도 → 실패 시 kinetic fallback**
  인데, 현행 학습 레시피의 교전 규칙 (r3 A안: net 전 kinetic 허용, +0.5) 은 "먼저 되는 쪽"
  이라 1단계를 그 의미대로 검정할 수 없었다 (사용자 정리 2026-10-08). E7-c 는 **당초 순서로
  돌아가** 1단계를 검정하고, 동시에 K1 경계 ρ* (가정 A5 = limiter 없음) 의 학습 수준 검정을
  같은 설계에서 얻는다.

## 1. 설계 — 2×2 × seed 3 = 12 run

| | **무장 (post-shot)** — 발사 후에만 치명 | **무력 (inert)** — 판정·kinetic 효과 0 |
|---|---|---|
| **P1: t0.85_h1.0_cv** (ρ = 1.923/0.85² ≈ **2.66**, ρ* 의 −5.4%) | 협력이 있어야만 열릴 수 있는 칸 | ρ* 아래 + 협력 없음 → 닫혀야 함 |
| **P2: t1.0_h1.5_cv** (ρ **2.94**, ρ* 의 +4.6%) | 참조 | 콘 단독으로 열려야 함 |

- ρ* = 2.813 (P-ρ2 등록). P2 는 E7-a 창 3.0 step (비승격, 학습 하 첫 측정). P1 은 E7-a 격자
  밖 (τ 0.85) — 선정 근거는 해석적 ρ 위치뿐, 실측 오염 없음.
- **무장 (post-shot) 교전 규칙**: limiter 의 kinetic 교전 (무장·커밋 경로 **와** 접촉 경로
  `_resolve_contacts` 둘 다) 은 **finisher 가 발사한 뒤에만** 허용 (fsm 이 LOADED 를 떠난
  시점부터). 발사 전 limiter 는 무해하게 움직일 뿐이다. 판정의 witness 폐쇄는 원래부터 "net
  비행 τ 동안 탈출하면 limiter 에 죽는다" 를 가정하므로 이 규칙과 의미론이 정확히 일치한다.
  공격자는 "발사 전 무해, 발사 후 치명" 을 학습한다 → limiter 의 과제 = 발사 전에 탈출 경로
  근처에 자리 잡기 (분할 기하 = limiter-control opportunity 의 원래 의미).
- **무력 (inert)**: `physics.kill_radius = 0` (config 단일 소스 → 판정 witness 폐쇄 와 kinetic
  접촉 동시 0). limiter 는 계속 움직이고 관측 구조 불변. 공격자가 무해한 limiter 에 재적응 →
  1단계 (협력) 와 3단계 (fallback) 를 모두 뺀 **net 단독 세계 = K1 가정 A5 세계**.
- 생산: 조건별 BC 신규, arm C-① 레시피 (r4p + 증류 fire head) 를 **각 조건의 교전 규칙
  하에서** 학습, 1.1e8. **조건별 전용 judge exploiter** (그 조건의 동결 방어 상대, 1e7, jseed
  279000대). server4 GPU 1장 (서버 룰), **E7-b 생산 종료 후** 직렬 (~12h).
- E7-b (A안 교전 규칙) 와는 교전 규칙이 달라 **직접 비교·pooling 금지** — E7-c 내부 비교만.

## 2. 지표 — 발사 교전 방어 수 D_shot

- **D_shot = NET 포획 (NET_CAPTURE + CAPTURE_WITH_CONTACT) + 발사 교전 창 안의 kinetic 무력화**
  (발사 후 net 판정이 나기 전, 즉 net 비행 중 탈출하던 공격자가 limiter 에 걸린 경우). 이것이
  "발사 tick 의 보장-포획 판정 (net 이 잡거나 limiter 가 막는다)" 이 실전에서 성립한 횟수다.
- **fallback 무력화** (net 빗나간 뒤 = net_spent 이후 kinetic) 는 3단계 효과라 D_shot 에서 제외,
  별도 보고. post-shot 규칙상 발사 전 kinetic 은 0 이어야 함 (위반 = 구현 결함 → 무효).
- 무력 조건에서는 kinetic 이 없으므로 D_shot = NET.
- 근거: NET 만 세면 분할이 작동해 limiter 가 탈출을 막은 경우 (라벨 HARD_KILL) 가 빠지고,
  전체 defended 를 세면 fallback (3단계) 이 섞인다. D_shot 만이 1단계+2단계를 잰다.

## 3. 사전 등록 예측·게이트 (기존 문턱 가족: 29/240, +24, seed 2/3)

- **P-ρ2L (ρ* 의 학습 수준 검정, 무력 = A5 세계)**: D_shot(inert, P2) ≥ 29 **그리고**
  D_shot(inert, P1) < 29 (각 seed 2/3) → `P_RHO2L_SUPPORTED`. 그 외는 `NOT_SUPPORTED` + 방향 보고.
- **P-②d (협력이 경계를 민다 = 기여 ③)**: P1 (ρ* 아래) 에서 D_shot(armed) ≥ 29 **그리고**
  D_shot(armed) − D_shot(inert) ≥ +24 (같은 seed 쌍, 2/3) → `COOP_PUSHES_BOUNDARY`. P1 무장도
  닫히면 `COOP_NULL_BELOW`. P2 의 armed−inert 차이는 보고 (고-ρ 협력 무관/boxed 손해 방향 —
  E7-a′ H↑ 의 학습판).
- **기전 귀속 (보고, 126 보조 주장 1)**: 무장 조건 `--coop-window` 창 tick 협력 몫 C·H (최소
  신호 하한 1% — 미만이면 즉시 폐쇄 경로 `LOW_SIGNAL`). D_shot 차이 중 C 로 설명되지 않는
  부분 = 궤적 조형 경로 후보 (정량 분해는 주장하지 않고 범위로 보고). fallback 무력화 수 보고.
- 무효: budget/completion/paired/manifest/BC-계보 위반, 또는 post-shot 규칙 위반 (발사 전
  kinetic > 0) run 제외·보고.

## 4. 정본 평가

server4 CPU, 240판 paired, 조건 시드 = **278000 + cond_idx×1000** (cond 순서 = P1-armed,
P1-inert, P2-armed, P2-inert; 학습·라벨링 사용 금지), `--tau-scale/--theta-scale/--aim` +
`--limiter-roe post_shot | --limiter-inert` + `--coop-window`, defenders = learned_det (판정) +
learned_sto (보고), 조건별 ex_judge. 에피소드 기록에 kinetic 무력화 시점 분류 (`kill_phase` ∈
{pre_shot, shot_window, fallback}) 추가.

## 5. 구현 전제 (봉인 후·생산 전, canonical 선행 → JAX 미러)

- `FS1Spec.limiter_roe` ∈ {"a" (현행 기본, bit-exact), "post_shot"}: post_shot 이면 발사 전
  limiter 무장 채널 0 강제 + 접촉 resolver 비활성, 발사 후 둘 다 복원.
- `FS1Spec.limiter_inert`: `physics.kill_radius = 0`.
- 테스트: (a) 기본값 no-op bit-exact, (b) post_shot 에서 발사 전 kinetic 0 / 발사 후 접촉 무력화
  가능, (c) inert 에서 판정 = limiter 제거 판정, kinetic 0, (d) eval `kill_phase` 분류.
- JAX parity: 기준 golden 불변 + post_shot·inert 각 1조건 f64 spot-check.

## 6. 해석 범위·어휘

- 두 점 × seed 3 = 경계 근처 **국소 검정** (ρ 전역 협력 프로파일 아님). 양성은 "1e7 착취자
  조건부". "cooperation" 금지 → limiter-control opportunity. 창발 주장 금지 (증류 머리 레시피).
- not_evidence_for: 세계 천장, 실물 대표성, E7-a/b·arm C-①/D 와의 pooling.

## 7. 해석표 고정 (v1.1, 2026-10-08 — 사용자 승인, **E7-c 생산·결과 전**)

게이트 (§3) 는 바꾸지 않는다. 아래는 P1 (ρ* 아래) 결과를 서사에 연결하는 규칙을 결과 전에
고정한 것이다 (지도교수 세션 권고 + main 의 수치화).

- **Δ** = D_shot(armed) − D_shot(inert), P1, 같은 seed 쌍. 행 판정은 seed 2/3 다수결.
- **폐쇄 지표 두 개**: C = 무장 조건 창 tick 협력 몫 (`--coop-window`, 3-seed 합산) /
  K_sw = 무장 조건의 발사 교전 창 kinetic 무력화 수 (`kill_phase = shot_window` — net 비행 중
  탈출하던 공격자가 limiter 에 걸린 횟수, 즉 폐쇄가 실전에서 실현된 횟수).

| 행 | 조건 (P1) | 해석 | 논문 처분 |
|---|---|---|---|
| A | Δ ≥ +24 **그리고** (C ≥ 0.01 **또는** K_sw ≥ Δ/2) | 탈출로 폐쇄가 경계 아래에서 작동 | 기여 ③ 복귀 (원래 형태) |
| B | Δ ≥ +24 **그리고** C < 0.01 **그리고** K_sw < Δ/2 | 위협에 의한 궤적 조형 — 협력은 실재하나 기전이 다름 | ③ 을 "kinetic 위협이 만드는 조형" 으로 재정의 |
| C | −24 < Δ < +24 | 이 regime (이 net 기하·교전 규칙·착취자 예산) 에서 net 협력 효과 없음 | Paper 1 은 ③ 없이. ②축은 기하 Lemma (탈출 구 반경 vs kill 반경) 로 설명, 협력 질문은 Paper 2 (mode 전환) 로 |
| D | Δ ≤ −24 | 경계 근처에서 협력이 해로움 (boxed 손해 기전) | C 와 같고, 손해 기전 보고 |

- seed 3 개가 서로 다른 행에 흩어져 2/3 다수가 없으면 `MIXED` — 행 판정 없이 seed 별 보고.
- 어느 행이든 주장 범위 = "두 점 × seed 3, 이 net 기하·post-shot 교전 규칙·1e7 착취자 조건부".
  "협력은 의미 없다" 같은 일반 명제는 쓰지 않는다.
- A 행과 `COOP_PUSHES_BOUNDARY` (§3 P-②d) 는 별개: A 는 Δ 만 보고, P-②d 는 P1 무장의 절대
  천장 (≥ 29) 까지 요구. 둘의 조합은 그대로 보고.

## 8. 후속 (형식만, 미봉인): κ = R_k / r — ②축의 물리 손잡이

- kill 반경 R_k 를 탈출 구 반경 r = ½aτ² 로 나눈 무차원비 κ 가 ②축에서 ρ 와 같은 역할을 할
  후보 (지도교수 세션 제안). 판정기 구조상 limiter 가 공격자 현재 위치의 R_k 안이면 전 경로
  폐쇄 (boxed) 이므로, 부분 폐쇄 (분할) 가 가능한 영역은 탈출 부채꼴 끝 옆의 두께 ~r 껍질뿐
  이라는 가설 — τ↓ 로 r 이 줄면 협력은 "무폐쇄 / 전폐쇄" 양자택일로 퇴화 (E7-a′ 의 C≈0,
  H↑ 와 정합).
- 순서: ① 사용자 손 유도 (부분 폐쇄 껍질의 두께·위치를 R_k, r, N 의 함수로 — 영역 경계식)
  ② 그 예측을 등록한 뒤 **E7-c 판독 후** 학습 없는 프로브 (E7-a′ 프로토콜 + 판정 kill_radius
  {0.25, 0.5, 0.75, 1.0, 1.5} m × ρ 2~3 점, C·H; 0.75 m 세계에 적응한 공격자 편향 명시)
  ③ R_k × 교전 규칙 학습 sweep (조건별 착취자) 은 **Paper 2 (mode 전환, V_mode 지도)** 로 이관
  — URP 10주 안에서는 열지 않음.

## 9. 정정 v1.2 — 확률 정책 감사 팔 추가 (2026-10-09, 사용자 승인, **E7-c 생산·결과 전**)

- 근거: E7-b 에서 열린 세계의 det 판정은 결정성 착취에 막힐 수 있음이 드러남 (노트 10-09b).
  det 만으로 판정하면 ②축 검정이 그 효과에 묻힐 위험.
- 추가: 4 조건 × seed 3 각각에 **확률 정책 동결 방어 상대 전용 착취자** (`--exploit-sto`, 1e7,
  jseed **283000 + cond_idx·1000 + seed**) — 기존 det 착취자 (jseed 279000대) 와 별도.
- 판정은 **두 계열을 나란히** 낸다 (우열 없음, 사전 선언): det 계열 = §3 게이트 그대로
  (learned_det vs det-착취자) / sto 계열 = 같은 게이트 문구를 learned_sto vs sto-착취자로 적용
  (`P_RHO2L_S`, `COOP_PUSHES_BOUNDARY_S`) + §7 해석표를 sto 계열에도 적용. 두 계열이 다른
  결론이면 둘 다 보고하고, 차이 자체를 "예측불가성 효과" 로 기록 (창발 주장 아님).
- 정본 평가: 같은 시드 (278000 + cond_idx·1000), 착취자 그룹 2개 (`ex_judge`, `ex_judge_sto`).
