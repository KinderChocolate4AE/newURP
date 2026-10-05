# 125 — E3b: 방어 예측불가성 × μ 요인 분리 (+ 조건부 동시학습)

- **일자**: 2026-10-06 · **상태**: **phase 1 봉인** (사용자 승인; pin = JAX 42f8835, cell_idx = 지역 0/1/2, hash 는 manifest 파일 참조) (`scripts/fs1_e3b_manifest.py`)
- **결정 근거**: E3 stage 1 = `E3_BAND_EMPTY` (전 격자 0~2%, `d8f6b92`) — 단 **프로토콜이 "고정
  정책은 암기당한다" 와 분리 안 됨** (사용자 정정, 노트 2026-10-06a §4.3 r2). 공격자는 고정 scripted
  에 과적합 (교차 55~229/240, 사다리 236+). 성급한 결론 2개를 가설로 강등하고 요인을 분리한다:
  "μν 무관" (고정-scripted 조건부였음), "적응성이 손잡이" (미검).

## 1. 사전 등록 질문

- **Q-A (예측불가성 단독)**: 학습·적응 없이 episode 추첨만으로 (혼합/파라미터 무작위 scripted)
  전용-exploiter 천장이 고정 순수 대비 열리는가.
- **Q-B (μν 재검정)**: 비고정 방어에서 천장이 μ 에 따라 열리는가 — stage 1 의 μ 결론이
  고정-방어 artifact 였는지의 직접 검정.
- **Q-C (학습 효과, phase 2 조건부)**: 동시학습 방어 (고정 후 평가) 가 최강 혼합 scripted 천장을
  넘는가.

## 2. Phase 1 (학습 없음 — exploiter 6 run 만)

| 요소 | 내용 |
|---|---|
| cell | **m0.35_n1 · m0.7_n1 · m1.4_n1** (ν=1.0 고정, μ 3점) |
| 방어 family | **P** 고정 순수 (stage 1 수치 재사용 — kfirst50/fin12_fb 천장 0~4/240, 재실행 없음) · **M1** mix5050 (episode 추첨 50/50 {kfirst50, fin12_fb} — 평가는 시드 짝홀로 정확 50/50) · **M2** kfirst_rand (무장 반경 U[30, 70] m episode 추첨 — mode 불확실성 vs 파라미터 불확실성 분리) |
| exploiter | cell × {M1, M2} = **6 run × 1e7** (JAX `0df35f3` `--stack r4`, `--exploit scripted:mix5050 / scripted:kfirst_rand` — 학습 중에도 episode 마다 분포에서 추첨된 방어를 상대). 과적합 속도 = 학습 로그 wr 궤적으로 보고 (추가 run 없음) |
| 평가 | 정본 240판 paired (server4), cell 시드 = 264000 + cell_idx×1000. 보고 추가: M1/M2 를 **stage-1 의 ex_kfirst50/ex_fin12_fb (구 exploiter) 상대로도** 평가 (산술 하한 검증 — ckpt 가 이미 server4 에 있어 공짜) + R1/R2 로그 + 궤적 |
| **Q-A 판정** | cell 별: max(ceil_M1, ceil_M2) − ceil_P(stage 1) ≥ **+24/240** → `UNPREDICTABILITY_OPENS(cell)` |
| **Q-B 판정** | ceil_M(m1.4) − ceil_M(m0.35) ≥ **+24** (같은 family 내) → `MU_REOPENS_UNDER_MIXTURE`; m0.7 은 단조 보고 |
| 무효 | budget/completion/paired/manifest 위반 cell 제외·보고 |

## 3. Phase 2 (동시학습 — **별도 addendum 으로 phase 1 판독 후·학습 전 봉인**)

- 생산: 선정 cell 에서 arm A (r4′) / arm B (κ0.2) × 3 seed × 1.1e8 (JAX) — FS1 동시학습은
  방어 생산 단계로만 쓰고, 판정 공격자는 **완성 방어를 상대로 새로 학습한 held-out exploiter**.
- Q-C 기준 형식 (수치는 addendum 에서 봉인): ceil_learned − max(ceil_M family) ≥ +24, seed 2/3 →
  `LEARNING_BEATS_MIXING`. learned_sto·R1/R2·B−A (목적함수 변경 효과) 보고.
- phase 1 이 전 cell 바닥이면 (예측불가성으로도 안 열림) phase 2 는 "열린 cell 부재" 로 보류하고
  세계 설계 축 (E7 net 사양 등) 논의로.

## 4. 규율

판정 평가 = server4 · pooling 금지 (stage 1 수치 재사용은 동일 manifest 사슬 계보 명시) ·
어휘 가드 유지 · 봉인 전 pin 커밋 dry-run (v1.1 교훈) · 격리본 불사용.
