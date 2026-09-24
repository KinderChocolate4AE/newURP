# 2026-09-24c — capturer-F1 판독: STOP_F1 (pooled H_illegal 41 > 40, 1건 차이). 표본 SNR은 고쳐졌고, 남은 병목은 폐루프 mean drift

**판정:** 봉인 gate(manifest `aca08029be1a2fb9`)에 따라 **`STOP_F1`**이다. 두 BC seed 모두에서 F1의 clean crossing episode 수와 clean N 수는 대조보다 늘었다. 그러나 pooled H_illegal이 40에서 41로 1건 늘어 `pooled_H_illegal_not_increased` 조항이 실패했다. 결과 전에 봉인한 조항이므로 결과를 본 뒤 문턱이나 해석 규칙을 바꾸지 않는다. 소규모 RL 계약 작성 자격은 열리지 않는다. RL update는 0회이고, promotion은 없으며, W6는 닫혀 있다.

정본: `artifacts/marl/b0_v3_capturer_f1/readout.json` (harvest `dd92ac7`, pre-result `242945f`).

## 1. 계보

- lineage, pairing, finite, completion 모두 PASS: 1,120 episode, code `242945f`, scoped dirty 없음.
- 실행 환경: CUDA 12.4, torch 2.6.0+cu124, `CUBLAS_WORKSPACE_CONFIG=:4096:8`, deterministic algorithms 켜짐.
- cosine 대조 앵커는 두 seed 모두 **exact-metric-match**였다(`bc_init.json` 지표 6개 |Δ|=0). 원본 checkpoint가 아니라 지표에 고정한 재구성이다. 결과 전에 걱정했던 CuBLAS 드리프트는 실제로 생기지 않았다.

## 2. 자기 궤적 (BC 직후 + scripted c5, 새 namespace 81000)

| seed | objective | N | crossing ep | crossing 합 | FIRE | H_illegal |
|---|---|---:|---:|---:|---:|---:|
| 0 | cosine | 7 | 19 | 25 | 23 | 20 |
| 0 | **F1** | **18** | **37** | 68 | 35 | 20 |
| 1 | cosine | 6 | 26 | 41 | 24 | 20 |
| 1 | **F1** | **10** | **44** | 68 | 29 | **21** |

- paired discordance (clean N, 표기 = F1만 성공 / 대조만 성공): seed0 16/5, seed1 7/3. clean crossing episode 기준으로는 seed0 30/12, seed1 28/10이다.
- cell별 ΔN 부호 (+/−/0): seed0 10/4/14, seed1 7/3/18. Δcrossing 부호: seed0 15/4/9, seed1 14/4/10.
- H_illegal 40건은 두 objective에서 **같은 scenario**다. 이 사건들은 scripted c5 limiter의 접촉이 지배한다. 추가된 1건은 seed1 `r09c1/sid184`이며, 대조는 F_other로 끝났고 F1은 FIRE 후 H_illegal로 끝났다. 규칙상 이 1건은 그대로 실패로 센다.
- 이 표는 과학적 유의성의 증거가 아니다. N의 절대 수준(≤18/280)은 scripted 참조(role-swap 148/280)보다 여전히 훨씬 낮다.

## 3. 교사 적합도 (교사 상태, BC 시점 norm)

| seed | objective | mean cos (P50 각) | \|μ\| | 표본각 P50 / P90 | fire tpr / tnr |
|---|---|---|---:|---|---|
| 0 | cosine | 0.9997 (1.02°) | 0.162 | 75.2° / 141.5° | 1.00 / 0.977 |
| 0 | F1 | 0.9995 (0.96°) | 0.999 | **25.4° / 44.2°** | 1.00 / 0.977 |
| 1 | cosine | 0.9996 (1.05°) | 0.164 | 75.0° / 141.1° | 1.00 / 0.979 |
| 1 | F1 | 0.9994 (0.99°) | 1.001 | **25.3° / 44.1°** | 1.00 / 0.979 |

F1은 설계 의도대로 작동했다. |μ|는 약 1이 되었고, 표본 조준 오차는 75°에서 25°로 줄었다. 방향 적합도와 FIRE head는 두 objective에서 같다(FIRE head는 bit 동일).

## 4. 궤적 판독 (trace 16장; 이 판독은 수치보다 먼저 했다)

- 자기 궤적 평균 (episode 중앙값): 표본 명령과 교사축의 각도는 약 80°에서 약 50°로 줄었고, |μ|는 0.13에서 0.88로 커졌다. 하지만 **policy mean과 교사축의 각도는 36~43°로 거의 그대로**이고, 실제 자세와 교사축의 각도도 58°에서 48°로만 줄었다.
- trace에서 F1의 표본 명령은 mean을 잘 따라간다. 그러나 **mean 자체가 t≈10~20 이후 교사축에서 벌어져 100~150°까지 발산**하고(r00c1, r13c2, r07c1), 자세가 그 mean을 따라가므로 cone(≈12°) 밖에 머문다. v_shot_soft는 가끔 짧게 튀는 정도다.
- 결론: 2026-09-22e에서 1차 기제로 본 **표본 SNR은 F1로 해소됐다.** 현재 일차 병목은 22e에서 2차로 적었던 **개방루프 BC의 off-manifold 누적(폐루프에서 mean이 drift하는 현상)**이다. 이것은 관측 해석이며 gate 판정과는 별개다.

## 5. 이 판독이 여는 것과 열지 않는 것

- **열지 않는다:** F1 기반 소규모 RL 계약, W6, candidate selection, PFSP, "협력 학습" 주장. `NO_SELECTION`과 기존 봉인 판정은 모두 불변이다.
- **다음 후보 (사용자 결정, 각각 새 계약으로 결과 전 봉인이 필요):** ① 폐루프 조준 drift를 겨냥한 BC 수정(교사 relabel이나 DAgger류 on-policy 상태 수집), ② F1 결과를 기제 근거로만 남기고 capturer 경로를 재설계. 어느 쪽이든 F1의 1,120사례를 선택 근거로 재사용하지 않는다.
