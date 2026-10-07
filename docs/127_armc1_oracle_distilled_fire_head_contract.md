# 127 — arm C-①: 판정기-증류 발사 머리 (oracle-증류 명찰)

- **일자**: 2026-10-07 · **상태**: **봉인** (사용자 ③ 게이트 사슬 결재 2026-10-07 → 단계
  기준 선언 = main, docs/126 §4; pin/manifest 는 발사 전 기록 — `scripts/fs1_armc1_manifest.py`
  build/load, **봉인 전 pin dry-run 전제 조항 유지**)
- **결정 근거**: `E3B2_NULL` (RL 단독으로 fire 를 창에 못 맞춤, 노트 10-07b) + 1.5a (창 실재
  18~22/24 ep, 1~4 step) + **P0a `AXIS3_NULL`** (창은 판정 보수성 아닌 세계 성질) +
  **P0b AUC 0.887** (상태 특징 7개 로지스틱만으로 창 열림 감지 가능, 노트 10-07e).
  가설: RL 의 실패는 탐지 불가가 아니라 **신호 희소성** — 판정기를 fire 채널에 직접
  지도학습 (증류) 하면 1~2 step 창을 맞출 수 있다.

## 1. 사전 등록 질문·기준

- **Q-C1a (capability — oracle-증류 명찰의 주장 상한)**: 증류 fire head 가 **held-out tick**
  에서 창 열림 (judge robust = worst≥1 ∧ ¬boxed) 을 감지하는가.
  기준: held-out AUC ≥ **0.9** (P0b 7-특징 로지스틱 0.887 을 full-obs 증류가 넘어야 의미)
  → `C1_DISTILL_OK`. 주장은 여기까지: "**증류로 창 감지가 가능하다**" — 창발·협력·학습
  성공 주장 금지.
- **Q-C1b (정본 — 천장이 열리는가)**: 증류 발사 머리를 단 방어 (동결) 가 **전용 judge
  exploiter** (완성 방어 상대 신규 학습, phase 2 와 동일 예산) 상대로:
  **ceil_det ≥ 29/240** (ceil_ref 5 + 24 — E3b p2 와 동일 문턱 가족), **seed 2/3**, cell 별
  → `ARMC1_OPENS(cell)` / 전 cell 미달 → `ARMC1_NULL`. learned_sto 는 보고.
- **착취자 감사 서명 (arm D 투입 조건)**: judge exploiter 학습 곡선 (0.05→0.99 서명) 보고.
  C-① 후에도 감사 ~97%+ 관통 지속 → arm D (이력 조건화) 투입 조건 성립 (docs/126 §4).

## 2. 생산 (JAX 레인 — worktree `newURP-jax`, canonical read-only)

| 요소 | 내용 |
|---|---|
| cell | **m0.35_n1 · m1.4_n1** (phase 2 와 동일 2 cell) × seed {0,1,2} |
| 라벨 | 매 tick "지금 발사 시 포획?" = **judge robust (worst≥1 ∧ ¬boxed)**, JAX parity 판정기 (seal v2 `14b9d56f20b1cfb9`) 로 rollout 전 궤적 라벨링. 라벨 의미론 = 보장-포획 하한 (기존 계보 — P0 turn-limited 계보 아님) |
| 학습 | 이동 = r4′ (`--stack r4p`) 유지, **fire 채널 = 증류 지도 loss** (BC: 라벨 양성 tick 에 arm, 음성에 hold). 동시 vs 교대-동결 등 구현 재량 = JAX/학습 레인, 단 **라벨 정의·주장 한계·예산 (phase 2 와 동일 1.1e8) 불변**. held-out 라벨 분할 (rollout 단위) 로 Q-C1a 측정 |
| C-② 측정 (공짜 로그) | per-limiter counterfactual: limiter i 제거 시 judge p_feasible/robust 변화 = **탈출 집합 축소량 귀속** (coma_D 계열, D 측정 전용). **보상 아님** — 승격은 이 로그가 기울기 부재를 보일 때만 별도 심사 (docs/126 §4 C-②) |
| judge exploiter | 완성 방어 (동결) 상대 신규 학습, cell×seed 당 1 — 착취자 감사 |

## 3. 정본 평가 (server4 고정)

- 240판 paired, cell 시드 = **272000 + cell_idx×1000** (학습·라벨링에 사용 금지 — 누수 가드).
  방어 = 동결 learned_det (판정) + learned_sto (보고), `--groups none --traj 2` (viz-first).
- 보고 추가: **발사 tick 명중률** (fire tick 의 judge robust 비율 — 증류가 실전에서 창을
  맞추는지 직접 측정) · fire@None 비율 (phase 2 의 발사 보류 침투 서명 대비).
- 보고 전용 (게이트 아님, 구현 여력 시): **oracle-gated fire 상한 defender** (판정기 직접
  발사 — 증류 손실 vs oracle 상한 분해, CLAUDE.md B-6 oracle-lite 와 동형 지위).

## 4. 규율

결과 전 봉인 (본 문서) · 판정 평가 = server4 · pooling 금지 (phase 2·P0 수치와 합산 금지,
비교는 같은 문턱 가족 참조만) · 어휘: "oracle-증류" 명찰 상시 병기, "cooperation" 금지
(limiter-control opportunity), 창발 주장은 무증류 arm 로그만 (= 본 arm 에서 창발 주장
원천 금지) · 격리본 불사용 · JAX git 은 newURP-jax 에서만 · 무효: budget/completion/
paired/manifest 위반 cell 제외·보고.

## 5. 다음 단계 (게이트 사슬, docs/126 §4)

판독 → `ARMC1_OPENS` ∧ 감사 관통 완화 → E7 계약 (ρ vs ceiling 머니 커브) 직행 /
`ARMC1_NULL` ∨ 감사 97%+ 관통 지속 → arm D (이력 조건화, sto>det 간접 지지) 투입 심사 →
E7. ③축은 E7 격자 불포함 권고 (P0a, 노트 10-07e).
