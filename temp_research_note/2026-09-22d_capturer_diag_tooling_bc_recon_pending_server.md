# 2026-09-22 — capturer 진단 도구 구현: 훈련 로그는 "BC-직후부터 on-policy 실패"를 선지시, 확정은 서버 재구성 대기

**판정:** 재현 가능한 capturer 진단 3종(BC-직후 재구성 + 적합도 행렬 + paired 평가·trace)과
B-5 한정 limiter-only 실험(별도 namespace, 결과 전 봉인)을 구현했다. 코드 감사에서 **배선
결함은 발견하지 못했고**, 봉인 산출물은 바꾸지 않았다. 이미 수확된 pilot 산출물의 재독만으로
"RL 중 망각" 단독 가설은 약해졌으나, 가설 확정은 서버 실행 산출물이 나온 뒤에만 한다.
`NO_SELECTION`은 유지된다.

## 1. 기존 산출물 재독에서 이미 읽히는 것 (새 실험 아님 — [22c](2026-09-22c_role_swap_capturer_bottleneck_current_gates.md) 후속)

`artifacts/marl/b0_v3_pilot/c0_base/seed0/{train_log,summary}.json` (봉인 pilot의 수확물):

1. **훈련 rolling capture율은 update 1부터 이미 0.05~0.067**이고 64 update 내내 그 수준이다
   (rolling 20 에피소드 해상도). 높았다가 무너지는 구간이 없다. scripted capturer는 같은
   경계셀에서 hold limiter로도 148~151/280을 얻으므로, **BC-직후 정책이 on-policy에서
   이미 ~5% 수준이었다는 방향**이다. 단 훈련 분포는 neutral limiter + frontier 편중이라
   해석 한정이 있고, 확정은 재구성 정책의 paired 평가로만 한다.
2. rolling에서 `fire_events`와 `clean_cross_rate`가 전 구간 동행한다 — **발사 head는
   crossing이 생기면 쏜다.** 병목은 발사 판단이 아니라 clean crossing의 생성이다
   (role-swap의 crossing 280→32 급감과 정합).
3. 훈련 1,070 에피소드의 credit 종결: `PENETRATED 967 / NET_SPENT 73 / N 30`. on-policy
   상태 분포는 교사 분포(clean N 궤적)와 극단적으로 다르다.

## 2. 코드 감사 결과 — 배선 결함 0건, 설계 차원 관찰 2건

검사한 것: 행동 패딩(P46/P48 기존 테스트, finisher live (0,1,2,4)→env Box(5) idx4 = fire),
Bernoulli FIRE의 표본 평가(P47), `fire_mode`의 평가 의미, PBRS `p_feasible=0`(기존
`test_b0_v3_credit`), NET_SPENT/H_illegal credit cut(동), `RunningNorm` batch update
(`test_obs_norm`), BC 초기화의 RNG 경로(`seed_everything` → `PilotRunner` 생성 →
`initialize_from_bc` 내부 `torch.manual_seed` — 사이에 torch RNG 소비 없음 → 같은
device면 재구성 가능).

- **새 회귀검사 1**: `fire_mode`는 scripted 역할이 없는 순수 policy 경로에서 **관성 인자**다
  — pilot `evaluate()`의 `fire_mode="never"`는 발사를 막지 않는다
  (`tests/test_b0_v3_capturer_diagnostic.py::test_fire_mode_is_inert_on_the_pure_policy_path`).
  낮은 P(FIRE)를 평가 인자 탓으로 돌릴 수 없음을 못박는다.
- **설계 관찰 A (normalizer 희석)**: `initialize_from_bc`가 BC 표본 597개로 `RunningNorm`을
  세팅한 뒤, RL rollout이 `normalize(update=True)`로 **계속 갱신**한다. 32,768 step 뒤 BC
  표본 비중은 597/33,365 ≈ **1.8%** — 최종 norm은 사실상 on-policy(PENETRATED 위주) 분포다.
  **같은 weight라도 입력 인코딩이 달라진다.** 결함이 아니라 표준 관행이지만, BC-초기화와의
  상호작용은 정량화 대상 (진단 fit-matrix가 측정).
- **설계 관찰 B (cosine-only BC × 표본 조준)**: BC axis 손실은 cosine(방향 불변량)이라
  `|mean|`을 키울 유인이 없다. 조준은 `N(mean, σ²)` 표본이고 σ = e^{-1.0}≈0.37/성분.
  cone 반각은 12~16°로 같은 자릿수의 각오차와 경쟁한다 (slew ω=2 rad/s 저역통과가 일부
  완화). `bc_init.json`은 cosine 0.9996만 기록했고 **`|mean|`은 기록이 없다** — 진단이 잰다.
- 두 관찰 모두 **봉인 결과에 소급 적용하지 않는다**. 수정안은 서버 진단 판독 후 별도
  계약·새 평가 namespace로만 (docs/110 §4 문턱 불변).

## 3. 구현물 (전부 `shepherd/` 밖 — BC dataset의 code_tree 봉인 불변)

| 파일 | 역할 |
|---|---|
| `scripts/b0_v3_capturer_diagnostic.py` | ① BC-직후 재구성(원본 checkpoint는 **저장된 적 없음** — 검증 앵커는 `bc_init.json` 지표 6개뿐, 재구성 2회 bit-identical 자기검사 포함, 허위 "원본" 금지) ② 교사 적합도 행렬 {BC/최종 weights}×{BC/최종 norm} + norm 이동량 + \|mean\|·표본각 SNR ③ 봉인 280 위 paired 평가 6 mode(진단 전용) ④ 스텝별 trace JSON |
| `scripts/render_capturer_traces.py` | trace → PNG (torch-free, viz-first 소비 단계) |
| `scripts/b5_limiter_only_manifest.py` + `artifacts/marl/b5_limiter_only/manifest.json` | limiter-only 실험 결과-맹검 봉인 (`manifest_hash` 파일 참조). **새 namespace**: train (53000, `b5lim_train_v1`) / eval (71000, `b5lim_eval_v1`) — pilot의 41000/51000/61000과 전부 분리 (테스트로 강제) |
| `scripts/b5_limiter_only.py` | learned limiter + **scripted clean-fire capturer** (freeze_finisher — scripted 행동은 어떤 policy log-prob에도 미기입, 외부 강제 FIRE 없음) vs hold/c5 대조, paired CRN. 22c의 "hold 151/280 정본 없음" 문제도 이 namespace에서 정본화 |
| `tests/test_b0_v3_capturer_diagnostic.py` · `tests/test_b5_limiter_only.py` | fire_mode 관성 · 렌더러 · 재구성 결정론(torch 표시) · manifest 봉인/격리/집계 |

로컬 검증: torch-free 테스트 전부 PASS (torch 표시분은 서버 venv에서).

## 4. 서버 runbook (torch venv, 순서 고정 — viz-first)

```bash
# 0) 코드 동기화 후 (dirty면 실행기가 거부)
python -m pytest tests/test_b0_v3_capturer_diagnostic.py tests/test_b5_limiter_only.py -q

# 1) capturer 진단 (~40분: recon 수초 + 6 mode × 280 + trace 12개)
tmux new -d -s capdiag "python -u -m scripts.b0_v3_capturer_diagnostic \
  --candidate c0_base --seed 0 --device cuda \
  > artifacts/marl/b0_v3_pilot/diagnostic/diag.log 2>&1"
# 산출: artifacts/marl/b0_v3_pilot/diagnostic/capturer_diag_c0_base_s0.json
#       + bc_recon_c0_base_s0.pt + traces/trace_*.json
# 판독 전 그림 먼저:
python -m scripts.render_capturer_traces artifacts/marl/b0_v3_pilot/diagnostic/traces

# 2) (진단과 독립) b5 limiter-only — smoke → controls → 2 seed (seed당 ~40분)
python -m scripts.b5_limiter_only --smoke
python -m scripts.b5_limiter_only --controls
for s in 0 1; do tmux new -d -s "b5lim_$s" \
  "python -u -m scripts.b5_limiter_only --run --seed $s --device cuda \
   > artifacts/marl/b5_limiter_only/seed$s.log 2>&1"; done
python -m scripts.b5_limiter_only --readout
```

## 5. 가설 분리표 — 진단 셀이 무엇을 지시하는가

| 관측 (서버 산출물) | 지시 |
|---|---|
| `bcrecon_scripted_limiter` N ≈ 최종(14/280)처럼 낮음 | **H1: BC-직후부터 on-policy 실패** (개방루프 BC의 폐루프 붕괴 / 표본 조준 SNR / off-manifold) — trace의 각도 시계열·\|mean\|이 하위 분기 |
| `bcrecon_scripted_limiter` N ≈ scripted(148)급, 최종만 낮음 | **H2: RL 중 파괴** — fit-matrix의 weight축 열화와 대조 |
| `final_weights_bc_norm` 적합도 회복 ↔ `final_norm`에서만 열화 | **H3: normalizer 이동이 주범** (weight는 보존) |
| `bcrecon_..._mean_axis` ≫ stochastic | 표본 조준 노이즈(관찰 B)가 주 병목 |
| b5: learned limiter Δ(N) vs hold/c5 | capturer 고정 시 limiter 학습 신호의 존재 여부 (scripted launcher 의존 — 승격 금지) |

## 6. 금지·한계 (재확인)

- 봉인 280 재사용은 **기제 진단 전용**. 문턱 하향·후보 재선택·`NO_SELECTION` 수정 금지.
- b5 실험은 어떤 결과여도 W6를 열지 않는다 (manifest `readout.promotion: none`).
- BC-직후 "원본" checkpoint는 존재하지 않는다 — 재구성 verdict가 `metric-mismatch`면
  이후 수치는 approximate로 강등해 읽는다 (원본 device=cuda; CPU 재구성은 다를 수 있음).
- W6 본 3-seed campaign·PFSP는 이번 작업 범위 밖 (변경 없음).
