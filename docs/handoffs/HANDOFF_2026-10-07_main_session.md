# HANDOFF — main 세션 (2026-10-07, FS1 연구 총괄 교대)

너는 newURP FS1 연구의 **main 세션** (계약 설계·봉인·정본 평가·판정 권한) 이다. branch
`feat/scale-up-v2`, worktree 규칙: **main = `newURP`, JAX = `newURP-jax`** (섞지 말 것).
JAX 세션·학습 방법론 세션의 핸드오프는 이 문서에 반영돼 있다 — 단 **main 의 기결정이 우선**
(아래 §5: 학습 세션 요약의 "A1~A5 무조건 도입" 은 main 에서 이미 일부 보류로 결정됨).

## 0. 상황 1줄

연구는 "동시학습으로 양성" 에서 **"포획 가능성의 3축 지도 (①net 물리 × ②협력 × ③회피 충실도)"**
프레임으로 격상 중 (docs/126 초안, 결재 대기). 모든 scripted·혼합 방어가 전용 착취자에 바닥임을
지도로 확정했고, **E3b phase 2 (동시학습 arm A/B) 의 정본 판정이 지금 server4 에서 돌고 있다** —
첫 작업 = 그 harvest 판독.

## 1. 먼저 읽을 것 (순서)

1. `temp_research_note/2026-10-06a_*.md` — E3/E3b 판독 전체 사슬 + 해석 가드 (**scripted 천장 ≠
   세계 천장**, 사용자 정정 2건 포함) + 1.5a + phase 2 봉인.
2. `temp_research_note/2026-10-07a_*.md` — phase 2 train-side + JAX 세계-역학 분석 접수 + main
   입장 (arm C-② 측정 먼저 등).
3. `docs/126_three_axis_capture_viability_map.md` — **Q1 프레임 격상 초안 (미봉인, 결재 ①~③ 대기)**.
4. `docs/125` (E3b 계약) · `docs/124` (E3 계약·arm A/B 정의·D1~D5) · 필요시 `docs/123` (FS1 정본).
5. 학습 방법론 정본: `docs/handoffs/HANDOFF_2026-10-05b_learning_research_to_main.md` +
   `reports/Frontier MARL 보상 설계.md`.

## 2. ★ 진행 중 (최우선)

- **E3b phase 2 정본 평가**: server4 tmux `e3b2` (10-07 13:28 발사, WORKERS=6). 12 slot =
  {m0.35_n1, m1.4_n1} × {armA=r4′, armB=+κ0.2} × seed{0,1,2}, 각 240판 paired (seed0 =
  270000+cell_idx·1000), 방어 = 동결 learned_det(판정)+learned_sto(보고) vs **전용 judge
  exploiter**. 완료 신호 = origin 커밋 "harvest E3b phase 2 (manifest b74aabfc3e319246)".
- 판독: `python scripts/fs1_e3b_p2_readout.py` (자동 실행됨 — `artifacts/fs1/e3b/phase2/readout.json`).
  게이트: ceil_det ≥ **29/240** (ceil_ref 5 + 24), seed 2/3, arm 별 → `E3B2_LEARNING_OPENS` /
  `E3B2_NULL`. **B−A = 목적함수 변경 효과로만 보고** (창발 아님). train-side 는 judge 97~99% 관통
  → NULL 유력. 판독 시 viz-first (traj PNG) + m1.4 B−A 일관 우위 (+.02~.05) 생존 여부 확인.
- 판독 후: 노트 기록 (판정형 제목, 10-07 일자) + memory 갱신 + **docs/126 결재 ①~③ 을 판정과
  함께 사용자에게 一括 상신**.

## 3. 판정 장부 (전부 정본·봉인, pooling 금지)

| 실험 | 판정 | 핵심 수치 |
|---|---|---|
| run3 pilot (r3, μ0.35) | `FS1_NULL` | D_pool −27 · D_ladder −171 · **천장: kfirst50 조차 전용 exploiter 에 3/240 (1.3%)** |
| E3 stage 1 (15 cell μ×ν) | `E3_BAND_EMPTY` | 고정 scripted 천장 0~2% 전 격자 (μ1.4 포함) — 사전예측 μ*∈[0.5,1.0] 기각. **고정-scripted 조건부** (사용자 정정: 암기 교란 미분리) |
| E3b phase 1 (혼합/무작위) | `E3B1_FLOOR_EVERYWHERE` | M1/M2 1~5/240 — 분포-exploiter 가 패배집합 **교집합** 경로 발견 (혼합 산술하한 논증 오류 기록) |
| 1.5a 점유율 (보고용) | 양성 | robust 포획창 (worst≥1∧¬boxed) 이 적응 공격자 12종 전부에 18~22/24 ep 존재, 폭 1~4 step |
| E3b phase 2 | **판정 중** | §2 |

가설 사다리: ①μν ✗ → ②episode 예측불가성 ✗ → ③상태-조건부 (1.5a 로 과녁 실재) → ④학습 (판정 중)
→ ⑤세계 설계 (E7). **ρ 가설** (= 콘 단면 1.5 m / 회피 종점 구 ½aτ²=0.92 m ≈ 1.6 이 지배, μν 불포함)
은 **사전 등록 예측 지위** — phase 2 가 첫 비자명 검정, E6/K1 (사용자 손증명 ≤10/31) 이 독립 유도.

## 4. manifest 사슬 (hash = 파일 참조, 재봉인 금지)

eval v1 `f4271b12` + v2 `f9e819e0` · r4 반복 r2 `a38993a8` (**미실행 보존**) · E3 v1→v1.1→v1.2
`567ab158` (실행 커밋 `0df35f3`; v1 pin 실행불가 교정 — **봉인 전 pin dry-run 은 이제 manifest
전제 조항**) · E3b p1 `aad0416b` (pin `42f8835`) · E3b p2 `b74aabfc` (pin `180b0ef`) ·
occupancy (보고용). 전부 `scripts/fs1_*_manifest.py` build/load 관례. 판정 평가 = **server4 고정**.

## 5. 학습 스택 기결정 (D1~D5, 2026-10-05 — 학습 세션 요약과 차이 주의)

- **채택 (r4′ = `--stack r4p`)**: A5 거리 shaping potential 화 (실측 0.169/ep) · A2 obs t/T 66-D ·
  A3 PFSP f_var. **보류**: A1 critic 공격자-행동, A4 HAPPO — parity 재검증 비용, stage-2/phase-2
  1차 결과 후 재심 (학습 세션 "무조건 도입" 과 다름 — main 결정이 정본).
- arm B = fire-tick κ·v_shot_soft 0.2 (단일 손잡이, non-potential). **제외 확정**: dense E_req ·
  PBRS viability Φ · 역할 분리 보상 · influence 보너스 (순환성). B1~B3 (λ_GAE·COMA·TAR²) = 진단
  게이트 credit 판정 시 순서대로. C (붕괴 시 entropy→MMD magnet). **D 측정 전용**: Shapley/
  difference reward 는 로그로만 (G&B 대비 방법론 차별점).

## 6. JAX 트랙 (상세 = 이 폴더의 JAX 핸드오프 원문 참조 가능)

- parity seal v2 `14b9d56f20b1cfb9` (`e8806d9`), 테스트 32/32, episodic ~33k sps. 커밋 체인:
  `16cf927`(r4′+armB) → `28e350c`(패딩) → `0817f5b`(μν·fin12_fb CLI) → `0df35f3`(golden) →
  `42f8835`(mix/rand) → `180b0ef`(merge). (d) 사건: 1차 p=0.0225 → 분리실험 (범인 = 상대혼합/
  truncation) → episodic 수정 → PASS p=0.2103.
- 산출물: server6 `/data1/hjhong/fs1jax/` (e3/stage1 30 run · e3b/phase1 6 · e3b/phase2 12 +
  judge 12). **격리본 보존** (server5 `.../stage1_prelaunch_quarantine_1808/` — 폐기 금지,
  10-05 18:08 사전 발사 사건). JAX 는 서버 점유 0, 지시 대기.
- 세계-역학 합의 (후속 설계 전제): 판정 = 보장-포획 하한 / "회피" = 탈출옵션 1개 상시 유지 /
  kill-radius 삼분법 + **분할** (전부 덮으면 boxed_in) / 1~2 step 창의 기하 필연 (조준 예산 ~4°) /
  창 감지·창 확장·동결 내성 = 세 처방.

## 7. 결정 대기 (사용자 상신 항목)

- **docs/126 결재**: ① Q1 프레임 격상 (봉인) ② P0a/P0b 착수 — P0a = turn-limit witness (**판정-
  모델 변형 선언 + dead param omega_att_max 소생**, 기준: 창 중앙값 ≥ 4 step → ③축 유효) /
  P0b = 창 열림 상태 회귀 (감지 가능성 → arm C 배분) ③ 게이트 사슬 (P0 → phase2 판정 →
  arm C-① (oracle-증류 명찰) → 감사 → arm D 조건부 → E7 (ρ vs ceiling 머니커브)).
- arm C-② (coma_D shaping) 는 **측정 먼저** — C-① run 에 로그 공짜 탑재, 보상 승격은 별도 심사.

## 8. 규율 (불변)

결과 전 봉인 + 사전 선언 기준 + 재판정 금지 · pin 실행 가능성 dry-run · pooling 금지 ·
viz-first · 어휘 ("cooperation" 금지 → limiter-control opportunity; 창발 주장은 무증류 arm 로그만;
"세계 천장" 주장은 학습 증거 없이 금지) · 격리본 불사용 · 커밋 science()/docs()/fix() +
Co-Authored-By (현재 Claude Fable 5) · 노트 = temp_research_note (판정형 제목, 달력 일자) ·
B0 v3 SEAL·선행 판정 번복 금지.

## 9. 운영 메모 (함정)

- ssh: `~/.ssh/config` BOM → 사본 만들어 `ssh -F <사본>`. server4=판정 (i9), server5/6=JAX GPU
  (RTX4500Ada, 상수 bit-exact 검증됨). 서버 간 ssh 키 없음 → 전송 = 로컬 경유 tar czf 파이프.
  **대형 ckpt 는 teams-only strip 후 전송** (phase2 2.4G→78M 전례). 전송 중단 시 **원격 tar 잔존
  프로세스**가 디렉터리를 오염시킬 수 있음 (10-07 사건: mv 가 nested 됨 — 발사 전 개수 검증이 잡음).
- 공용 서버: WORKERS=6 (사용자 상한), BLAS 1스레드, 30분+ 는 tmux, ntfy 는 침묵 가능 → origin
  harvest 커밋이 신뢰 신호. python 은 `.venv-l2` (server4) / `.venv-jax` (server5/6).
- 로컬: PYTHONIOENCODING=utf-8, `.venv` CPU torch. 커밋 전 `git branch --show-current`.
- 평가 도구: `shepherd/fs1/eval.py` (방어: learned_det/sto·fin12·fin12_fb·kfirst50·c5_fb·fwd_fb·
  mix5050·kfirst_rand; `--stack/--mu/--nu/--ladder/--exploiter NAME=PATH/--groups none`).
  orchestrator: `scripts/run_fs1_e3b_phase2_eval.sh` 등 (cell 별 done 플래그 재개 가능).

## 10. 다음 trigger 요약

harvest 도착 → §2 판독 → 사용자 一括 상신 (판정 + docs/126 ①~③) → 승인분 실행 (P0 하룻밤 →
arm C/D·E7 계약). 사용자 레인: **K1 손증명 ≤10/31** (ρ·0.92 m 구·4° 예산·분할 조건이 재료).
