# 2026-10-04f — run3 pilot 판독 = FS1_NULL (v1·v2 일치, 무효 0) — 더 큰 발견: 이 세계의 천장 ≈ 1.3% (전용 exploiter 앞에서 최강 scripted 포함 모든 방어 붕괴)

harvest `d34a931` (server4, manifests v1 `f4271b12a1d50b39` / v2 `f9e819e0d1171054`).
**run3 = pilot** (r4 반복 manifest r2 `a38993a8541264cd`): 확정에 세지 않음, r4 와 pooling 금지.
판정 평가 환경 = server4 (manifest r2 조항 준수).

## 1. 판정

| | v1 (legacy 사다리) | v2 (공칭 사다리) |
|---|---|---|
| D_pool | **−27** (학습 41 vs kfirst50 68 /240) | — |
| D_ex | **+6** (학습 9 vs kfirst50 3 /240) | — |
| D_ladder | −159 | **−171** (학습 66 vs kfirst50 237 /240) |
| 판정 | FS1_NULL | **FS1_NULL** (governs) |

문턱 ±24 대비: D_pool·D_ladder 는 명확한 음수, D_ex 는 양수지만 +6 — 양쪽 다 바닥이라 무의미.

## 2. ★ 천장 측정 (판정보다 중요한 발견)

- **kfirst50 vs 전용 exploiter (1e7): 3/240 = 1.3%.** 학습 방어 vs 전용 exploiter: 9/240 = 3.8%.
- exploiter 학습 종료 시 공격 승률 98~99%. 예산 1e7 짜리 보통 exploiter 로도 충분했다.
- → **이 cell (r06c1, 공격 20.5 vs 방어 7.16 m/s²) 은 적응 공격자 앞에서 사실상 방어 불가.**
  "학습이 실패했다" 가 아니라 "이 세계에서는 아무도 못 막는다" 쪽. 게이트 A 의 천장 질문에 답.
- 교차 강건성도 scripted 우위: kfirst50 vs ex_learned = 90/240, 학습 vs ex_kfirst50 = 7/240
  (단 그 셀은 240 중 214 가 TRUNCATED — 교차 exploiter 가 학습 방어 앞에서 침투 대신 배회.
  exploiter 전략이 상대-특이적이라는 증거, 보고용).

## 3. 궤적 (viz-first)

- **learned_det vs pool**: limiter 를 spawn 직후 전부 무장 (arm_d ≈ 188~247 m) → PN 이 나쁜 기하에서
  장거리 추격 → 산개. 공격자는 10 m 근방에서 loop/턴으로 흘려보내고 침투. iter 119 의 "12 m 전진
  kinetic 요격" 창발은 최종 정책에서 사라짐 (군비 경쟁으로 퇴화). fire_d 14~15 m (scripted 11.4 보다
  멀어서 net 명중률도 손해).
- **kfirst50 vs ex_kfirst50**: 직선 접근 → 5~10 m 종말 급회피 1회로 K_FIRST 요격 cone 과 net 을
  동시에 피함. limiter 는 자산 (반경 2 m) 에서 출발해 8~10 m 전개가 한계 — 가속 열세 + 짧은 활주로
  (P1c/P1d 주제와 정합).
- 기전 요약: 민첩 3 배 공격자의 **종말 1 회 회피**가 (i) net 중심 예측 (ii) PN 요격 (iii) miss 후
  fallback 을 모두 무력화. run1 의 "8 m/s² 흔들림만으로 scripted net 19/30→3/30" 관찰의 종점.

## 4. 함의

1. r4 (같은 cell) 도 같은 구조적 이유로 NULL 유력 — 단 반복 계약은 봉인됐고 JAX 로 비용이 ~1h 라
   **계약대로 실행** (정직한 반복 기록 + r3 대비 수정 효과 측정).
2. 학습 우위 주장은 이 cell 에서가 아니라 **regime 축 (E3)** 에서 찾아야 한다 — 방어/공격 기동성
   비율을 물리 근거로 고른 격자 (결과 전 봉인).
3. 예산 스케일링 (E2) 의 질문이 선명해짐: 방어 예산을 1e9~5e9 로 올리면 전용 exploiter 상대
   방어율이 1~4% 에서 움직이는가. 움직이지 않으면 cell 탓, 움직이면 예산 탓.
4. mode-rank reversal 증거 없음: 학습 방어의 K_FIRST 비율이 사다리 17.9% vs 적응 9.8~14.3% 로
   역전 없음 (docs/123 §7 기대와 반대).

## 5. 다음

JAX (d) 판정 (server5, 승인됨·14:45 현재 미시작) → exploiter 비교 → r4 최종 manifest 개정
(JAX commit + parity hash + 예산) → r4 BC → r4 3 seed → 확정 판정. 병행: E2/E3 계약 초안.
