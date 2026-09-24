# 2026-09-24 — B-5 limiter-only 판독: scripted capturer 고정에서도 일관된 학습 순증가 없음

**판정:** 결과 전 봉인한 scripted-capturer 의존 기제 실험은 계보·완주 검사를 통과했다. learned limiter는 hold 대비 seed0 `−1 N`, seed1 `+5 N`으로 방향이 갈렸고 c5 대비 두 seed 모두 낮았다. 이 예산과 새 평가 namespace에서 **limiter 학습의 일관된 clean-N 순증가는 관측되지 않았다.** 어떤 결과도 W6를 열거나 learned cooperation 성과로 승격하지 않는다는 manifest 해석 범위를 유지한다.

- 정본: `artifacts/marl/b5_limiter_only/readout.json`
- 수확 commit: `425808f`
- manifest: `451d371873103f3b`
- B0 v3: `5e7b5b486b9d8a4a`
- 실행 코드: `e519655`, 두 run 32,768 step / 64 update, CUDA, 미완주·비유한값 없음
- canonical seed log에 CuBLAS 비결정론 경고 없음. 다만 `CUBLAS_WORKSPACE_CONFIG` 값 자체는 summary에 기록되지 않아 산출물만으로 환경변수 값을 증명하지는 못한다.

## 새 paired 평가 결과

| arm | clean N / 280 | FIRE / 280 | clean crossing episode / 280 | H_illegal / 280 |
|---|---:|---:|---:|---:|
| hold limiter + scripted capturer | 140 | 277 | 280 | 0 |
| c5 limiter + scripted capturer | 149 | 274 | 279 | 15 |
| learned limiter seed0 + scripted capturer | 139 | 277 | 280 | 0 |
| learned limiter seed1 + scripted capturer | 145 | 277 | 280 | 0 |

episode-level paired discordance:

| 비교 | both N | learned only N | control only N | both fail | ΔN |
|---|---:|---:|---:|---:|---:|
| seed0 vs hold | 135 | 4 | 5 | 136 | −1 |
| seed1 vs hold | 139 | 6 | 1 | 134 | +5 |
| seed0 vs c5 | 124 | 15 | 25 | 116 | −10 |
| seed1 vs c5 | 128 | 17 | 21 | 114 | −4 |

c5의 N 수치는 두 learned seed보다 높지만 H_illegal 15건을 함께 만들었다. 이를 안전성과 교환 가능한 성능 우위나 채택 근거로 읽지 않는다. learned와 hold는 H_illegal 0이고 crossing 280/280으로 같았다. 따라서 scripted capturer가 발사 기회를 회복한 뒤 남은 limiter 차이는 작고 seed에 따라 부호가 바뀌었다.

훈련 rolling capture는 update 1부터 대략 0.4~0.65 범위였고 마지막에도 같은 범위였다. 이 로그에서도 낮은 출발점에서 limiter 학습이 뚜렷하게 상승하는 추세는 보이지 않는다. 고정 32,768-step 예산의 관측이며 더 긴 학습의 불가능성을 뜻하지 않는다.

## 처분

1. B-5 limiter-only 실험은 여기서 종결한다. 추가 seed·예산 연장·후속 선택은 하지 않는다.
2. 결과는 “작동하는 scripted launcher를 고정해도 현재 limiter 학습이 hold를 일관되게 개선하지 못했다”로만 기록한다. 정책은 scripted capturer에 의존하며 learned cooperation 결과가 아니다.
3. 다음 실험 우선순위는 docs/111의 F1 capturer BC-SNR 수정이다. 새 namespace에서 BC 직후 stochastic crossing/N 회복을 먼저 판정하며 RL update는 아직 열지 않는다.
4. 후속 실행기는 재현성 provenance에 `CUBLAS_WORKSPACE_CONFIG` 값을 직접 기록한다.
