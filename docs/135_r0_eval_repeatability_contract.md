# 135 — R0 평가 반복성 계약: env seed 만 바꿀 때 천장은 얼마나 흔들리고, 교차 감사 배율은 그보다 큰가

- **일자**: 2026-10-12 · **봉인**: `scripts/fs1_r0_manifest.py` → `artifacts/fs1/r0_manifest.json` (`0dfec67442ca6951`).
- **결재**: 사용자 2026-10-12. 설계 = 지도교수 10-12 스케치. 10/26 전 유일하게 허용된 새 계약.
- **동기**: 10-12 확인 — `--env-seed` 고정 시 재평가는 바이트 동일 → 반복성은 env seed 를 바꿔서 잰다 (평가 초기 상태 seed 대역은 고정).

## 1. 설계
- slot 선택 규칙 (봉인 전 고정, 기존 E7-b readout 값): det 정합 천장이 15 slot 중앙값 21 에 가장 가까운 slot (동점 = manifest 순서 첫째) =
  **t0.5_h1.0_cv s0** (평탄부) / det 정합 천장 최소 = **t0.7_h1.0_cv s1** (7, 낮은 천장).
- slot 마다 착취자 2 (det `judge_exploiter`, sto `judge_exploiter_sto`) × env seed 0–7 = 16 평가, 총 32. 각 평가 = learned_det·learned_sto 240판
  → 정합 칸 (det|det, sto|sto) 과 불일치 칸 (det|sto, sto|det) 이 한 번에 나옴. 플래그는 E7-b 러너와 같음 (+ `--env-seed k`). 재학습 없음.
- 천장 = `eval.summarize` 의 defended (E7-b 와 같은 정의).

## 2. 라벨
- 칸별 분산: env seed 간 SD ≤ 1.5 × 이항 SD → `R0_BINOMIAL`, 아니면 `R0_OVERDISPERSED`.
- 과대평가: (slot, 방어 줄) 4 칸의 불일치/정합 비율, env seed bootstrap (분자·분모 독립 재표집) 2000, 95% 하한 > 1.5 가
  4/4 → `INFLATION_EXCEEDS_NOISE` · 1–3 → `INFLATION_PARTIAL` · 0 → `INFLATION_WITHIN_NOISE`.
- 라벨 의미 단위 테스트 `tests/test_fs1_eval.py::test_r0_label_semantics` 통과 (이항 / beta-binomial / 3:1 / 1:1 / 혼합).
- 쓰임: 평가 방법 절의 배율 2.6–3.8 옆과 경계선 판정 옆에 "측정 잡음" 한 문장. **봉인된 판정의 재판정 없음.**

## 3. 검정력·비용
- 지도교수: 정합 p ≈ .08 → 이항 SD ≈ 4.2판, 불일치 p ≈ .25 → ≈ 6.7판, 차이 ~40판 ≈ 5σ. 위험은 과분산.
- CPU: 평가 32회 × 약 5분 (6 worker) ≈ 3 h. 러너 `scripts/run_fs1_r0_eval.sh`.
