# 2026-09-07 — R2b C arm 판정: C_POSITIVE — 협력 기하 opportunity 실재, rule-based controller 가 실현 실패 (3-way = B_null_C_pos)

science 커밋 `59826d3` (샤드 9파일 + c_readout.json). 판독 규칙은 회수 **전**
`55c6bcc` 에 봉인 (P1 규칙 기계 이식, 새 상수 0). 샤드 전부 code `82b3145`.

## 봉인 판정 (해석 재량 없음)

- **C rule: 14/14 행 양수 · slice {0: 7/7, 2: 7/7} · 전역 paired Δp_CA_net
  +0.370, CI95 [+0.353, +0.388]** (셀-층화 bootstrap B=4000) → **C_POSITIVE**.
- 3-way key = **B_null_C_pos**, B0 v2 봉인 문장 원문:
  > cooperation-is-meaningless is rejected; the rule-based controller failed
  > to realize exploitable cooperative geometry — 'motivates a learned or
  > more expressive cooperative controller' (NOT 'MARL will solve it')
- secondary Δp_U(C−A) = +0.409 [+0.390, +0.426].

## Descriptive (판정 외, 브리프·논문 재료)

- **kinetic substitution 아님**: p_C_hard 셀별 0~0.14 (저 η 셀 대부분 0) —
  C 의 이득은 순수 NET_CAPTURE. P1 에서 저 η kinetic 1:1 치환을 보인 바로 그
  영역 (η 2.1–2.4) 에서 Δp_CA 최대 (+0.44~+0.62, p_C_net 0.90–0.98).
- **η gradient**: Δp_CA 는 η 증가에 단조 감소 (η3.9: +0.10~+0.24),
  lite_no_solution 은 단조 증가 (η3.9 에서 0.22–0.40; 전역 9.7%) — 빠른
  공격자일수록 search 가 실패. 봉인 문구의 "at the tested lite search budget"
  한정어가 실질적으로 묶이는 영역.
- **B ≈ A 재확인**: Δp_CB = +0.370 ≈ Δp_CA (전 셀).
- best plan 구성: CEM accels 70.1% / intercept 29.2% / hold 0.7%. nosol 271판
  중 13판이 replay 에서 C_N=1 (lite↔full 역전 — 예상된 비대칭, 판정층은 replay).
- λ slice 간 정성 동일 (slice 2 가 전반적으로 baseline 높고 Δ 약간 작음).

## 정직 caveat (종결 감사 브리프에 그대로)

1. p_C_hat = **봉인 search 절차의 attainment rate** — 물리적 achievability
   확률 아님 (미발견 feasible plan 존재 가능; 특히 고 η 의 nosol 영역).
2. C plan 은 **privileged open-loop**: scenario 별 CEM 이 그 scenario 에서
   탐색 (공격자는 closed-loop 반응). 배치가능 controller 가 아니라
   achievability benchmark — "upper bound" 어휘 금지 (retired).
3. per-scenario C_N ≥ B_N 비보장 (유한예산 stochastic search) — dCB 는
   descriptive 전용.
4. **T_proj 4× 과소추정**: 봉인 benchmark 방법 (elapsed/len(records)) 이 CEM
   없는 싼 arm 을 섞어 per-solve 비용을 희석 → 8.71h 예측 vs 실측 ~37h.
   분기 결정 (FULL_28x100) 자체는 봉인 규칙대로 유효; 방법 교훈만 기록.
5. 판정은 scenario 당 **1회 replay** 라벨 — replay 자체는 full-fidelity
   결정론이므로 추가 반복 불요.

## 다음 수 (의존 순서)

1. ~~★viz-first~~ **완료 (같은 날, PASS)**: `figures/r2b_c_viz_trajectories.png`
   + `r2b_c_viz.py`. 3판 전부 replay-parity gate 통과 (봉인 search 결정론
   재실행 = 서버 기록 bit-exact — 플랫폼 FP 발산 없음). 육안: C 성공 2판은
   접촉 0·회랑 중간 포획·정상 fire→capture 시퀀스 (judge artifact 아님);
   nosol 판은 best=hold 로 A 와 동일 (고 η 한계 정직 노출). 정성 (n=2):
   발견 plan 은 추격형 아님 — limiter 배치 재구성으로 회피 선택을 좁히는
   패턴, B rule 이 표현 못 하는 계열. 브리프 r2 §8 에 수록.
2. R2b 종결 감사 브리프 (txt) 발송 → 감사 통과 시 claim 등록 (C047+?) +
   campaign freeze.
3. docs/89 hybrid MARL plan 의 동기 사슬이 이것으로 완성 — "physics says
   opportunity exists → simple rule cannot exploit it → learned controller"
   (단 봉인 문구대로 'motivates', 'will solve' 금지).
4. 대기열 불변: q_dec 1/12 mini-map → OAT screen → prop1 → 6DOF gate (docs/93).
