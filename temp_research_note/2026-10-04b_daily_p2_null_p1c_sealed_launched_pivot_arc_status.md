# 2026-10-04b daily — P2_NULL 판독 + P1c 봉인·발사; 10/01 pivot arc 현황 종합 (오늘의 수정사항은 전부 이 md 에 추가 기록)

세션 마감 기록 (notion 대체, 판정형 관례). 오늘(10/04) 이후의 추가 수정사항도
본 문서 §5 에 덧붙인다.

## 1. 오늘의 사슬 (10/04)

1. **서버 git 인증 SSH 전환** — PAT 만료 반복 → ed25519 키 등록, remote SSH 화.
   이후 서버 push (orchestrator 자동 push 포함) 무프롬프트.
2. **P2 harvest pull + 판독 = `P2_NULL`** (`8880aba`, 상세 = 2026-10-04 판독 노트):
   pooled ΔN +7/+39 (문턱 +34, seed 불일치) · seed0 고결합 1 config 음수 ·
   learned_s0 H_illegal 20. integrity 6/6. **PFSP 닫힘, limiter-learning 현 세계
   종결** (docs/117 출구). 보고 전용 핵심 관찰: **c5−hold 격차가 결합 이득과
   함께 커짐** (r02 −5 → r05_j06 +12, r08_j0 +10) — foundation 곡선 1차 측정.
3. **P1c standoff probe 봉인 + 서버 발사** (`38e885d`, manifest `6fc93fde71b38a30`,
   docs/121): k∈{1,2,4} × 공격자 {r05, r08, 전부 sense ∞} × {hold, c5},
   3,360 ep. k>1 = **B0 v3 밖 v4 pre-check 변형** (start_x·episode_len 만 k배,
   episode_len 기준값은 k=1 빌드에서 직접 읽음). 사전 등록: G(4)−G(1) ≥ +28 →
   `STANDOFF_OPENS_SHAPING` (B0 v4 go/no-go 입력). power gate = hold 평균 step
   k=1→4 증가 (P1b 교훈). smoke 44→178 step 실증. orchestrator
   `run_p1c_server.sh` (2-shard → readout → push, tmux 자동 종료).

## 2. pivot arc 종합 (10/01~10/04, 핸드오프 문맥)

| 날짜 | 사건 | 판정 |
|---|---|---|
| 10/01 | capturer RL1/RL2 STOP + 사후감사 (추가 위반 = 전부 draw flip) → **체인 동결, F3 keeper** | docs/117 + 89 r5 |
| 10/01 | W6~W9 재배치: P1 공격자 사다리 → P2 limiter-only v2 | 사용자 승인 |
| 10/01 | **P1a 완료**: route 지배 (229→102) · jink 제2축 · sense 30≡∞ 포화 · λ/bait null · `P2_PREMISE_SUPPORTED` (spread 127) | COMPLETE_P1 |
| 10/01~02 | plant pre-check: P1b 무효 (hold a_cmd≡0, 검정력 0 — 설계 실수 기록) → P1b-2 (c5) → row-9 probe | **ROW9_FLIP_NOISE — PM 추상화 전 행 유지, pre-check 종결** |
| 10/02 | **P2 봉인** (6-config mix, 131,072 step ×2 seed) | manifest `8ba6d0df420d6631` |
| 10/03 | 궤적 뷰어 (P1a 144 ep 재생일치 144/144, `viz/attacker_patterns_viewer.html`) · P2 freeze-check 버그 수정 (`b5e39ab`) | — |
| 10/03 | 사용자 지적: **접근거리 과소** → P1c 구상 · **sense_range 30 nominal 제거** (전지 관측 한계 사례, 6DOF 철회와 동형 논리) | docs/121 §0 |
| 10/04 | P2_NULL · P1c 봉인·발사 | 위 §1 |

## 3. 현재 상태 / 대기

- **서버**: P1c 실행 중 (tmux `p1c`, 자동 push). 완료 신호 = origin 에 harvest
  커밋 (ntfy 는 서버에서 침묵 — 신뢰하지 말 것).
- **다음**: P1c pull → 판독 → `OPENS` 면 B0 v4 (진입 게이트 + 전지 관측) 결재안,
  `DOES_NOT_OPEN` 이면 standoff 설명 기각 기록 + Track B 전면 이동.
- **병렬 필수**: **K1 손증명 (사용자, ≤10/31)** — docs/119 §6 체크리스트.
  K2 ≤11/15. G3 는 9/5 조기 완료 (PARTIAL_3D) — 미착수로 착각 금지.
- 달력: 오늘 W4 말 — r5 의 W6~W9 배치분을 ~5주 선행 소화. buffer 큼.
- foundation 자산 확보분: P1a 공격자 지도 · P2 4-arm × 6-config 곡선 (결합-의존
  조형 가치) · plant transport 결과 · 궤적 뷰어.

## 4. 유지 중인 판정·규율 (불변)

`NO_SELECTION` · `STOP_F1/CLBC1/F2/RL1/RL2` · b5 종결 · `P2_NULL` · PFSP 닫힘 ·
B0 v3 재개봉 금지 (변경 = v4 + 새 hash) · 어휘 ("cooperation" 금지 →
limiter-control opportunity) · 결과 전 봉인 + fresh namespace + gate 소급 변경
금지 · seed 사다리 최신 = 241000 (P1c).

## 5. 오늘의 추가 수정사항 (이후 발생분 기록)

- **Track B 학습·PFSP 순서 합의 (사용자 승인)**: "PFSP 닫힘" = docs/117 P3 (현 세계
  limiter-only 위 PFSP) 한정 — docs/104 §6.4 A2 league/PFSP 는 살아 있음 (G4/G5 뒤).
  순서: ① P1c 판독 → ② F1-E D2 scripted 3정책 (limiter 없음, viz-first) → ③ 학습
  상위 switch (PPO WAIT/NET/KINETIC, 하위 scripted, 고정 공격자 pool, DP oracle 회수)
  → ④ limiter 학습 추가 (MAPPO/HAPPO, P1c OPENS 시만) → ⑤ PFSP (진입 = ③·④ policy 가
  scripted threshold switch 를 seed-일관 초과). 근거: PFSP 는 학습 가능성이 아니라
  적응형 공격자 강건성 도구; 빈 self-play 금지. 요격률 저조의 상당 부분은 28 boundary
  cell 선택 효과 — 실제 병목은 조형 이득 ≤ +12/280 (P1c 가 활주로 축 측정 중).
- **P1c 판독 = `STANDOFF_DOES_NOT_OPEN`** (harvest `2ead989`, integrity 5/5):
  G(1..4) = 0/+9/+10, Δ=+10 < +28. 궤적상 c5 limiter 는 k=4 에서도 layout 근처에만
  머물러 늘어난 거리를 쓰지 않음 (layout-고정 스케일링 모형 한정). B0 v4 결재 없음,
  limiter 학습 보류, **Track B F1-E D2 로 이동**. 상세 = 2026-10-04c 판독 노트.
  뷰어 `viz/p1c_standoff_viewer.html` (재생일치 70/72).
- **P1c 메커니즘 정정** (`fdffae7`): c5 = 자산 중심 r_d 9 m 호 위 bearing-only 골키퍼라
  늘어난 접근거리를 구조적으로 못 쓴다 → "짧은 활주로" 가설은 **기각이 아니라 미시험**.
  판정 `STANDOFF_DOES_NOT_OPEN` 은 유지 (layout-고정 c5 한정).
- **P1d (docs/122) 보류**: 전진 교전 scripted limiter 로 활주로 가설을 재는 계약 초안,
  **미봉인·미실행**. fwd 규칙은 scripted 기준선으로만 남김 (`b0e67a5`).
- **★ Track B 순서 합의 (위 첫 항목) → FS1 동시학습 결정으로 대체 (사용자, 10/04)**:
  scripted 규칙 쌓기는 음성만 반복 → 검증된 방법론 (Gavin & Bronz 2026: MAPPO + PFSP
  동시학습) 을 통째로 도입해 양성부터. 정본 = docs/123. 근거·예산 격차 = 노트 2026-10-04d.
  선행 판정은 번복하지 않으며 FS1 은 새 세계·새 계약 (pooling 금지).
- **FS1 run0~3** (상세 = 노트 2026-10-04e):
  - run0 (r0, 9.1e6 step): 양측 성공 경험 0 → 신호 0 (FIRE 확률 붕괴, RL 공격자 자산 미적중).
  - run1 (r1 FCS 분리·homing autopilot·방어 BC, 8.2e6): 방어 1~5% 정체, limiter 무장 0,
    공격자 미끼 전술 창발.
  - run2 (r2 fallback BC·station point·팀별 lr, 1.6e7): 사다리 상대 41→67% 학습 확인,
    RL 공격자 상대 학습·scripted 모두 ≈0/48 — 원인 ROE (합법 kinetic 창 ≈ 0).
  - run3 (r3 ROE A안 K_FIRST +0.5·BC kinetic-first 30%·방어 2:공격 1, 1.1e8 목표, 진행 중):
    **초기 양성** — iter 119 결정적 평가 RL 공격자 상대 학습 9/48 vs scripted 5/48.
    단 사다리 상대는 scripted 48/48 > 학습 33/48. 봉인 평가 전이라 주장 아님.
- **평가 도구 + 평가 계약 v1 봉인** (`2d5454f`, manifest `f4271b12a1d50b39`, docs/123 §8,
  run3 harvest 전): `shepherd/fs1/eval.py` (방어 5 × 상대 그룹 paired, 궤적 그림, 로그 요약),
  `train --exploit` (고정 방어 상대 fresh exploiter, 학습 방어는 결정적 행동). 판정 = 최종 ckpt
  `learned_det` vs 최고 scripted, D_pool·D_ex ≥ +24/240 → `FS1_POSITIVE`, D_ladder ≤ −24 면 NARROW,
  확정 = 3 seed 중 ≥ 2 (사용자 승인, 전부 권장안). 실행 = `scripts/run_fs1_eval_server.sh`.
  운영: JAX 세션과 작업 트리 공유로 커밋이 feat/fs1-jax 에 들어감 → cherry-pick 복구, 이후
  worktree 분리 (main = newURP, JAX = newURP-jax).
- **run3 중간 판독** (iter ~470, 학습 로그 — 판정 아님): RL 공격자 상대 방어율 0.40 (iter 60~119)
  → 0.11 (420~479), 공격 학습 중 scripted 방어도 돌파 (kfirst50 K_FIRST 1595 → 68). iter 119
  "양성" 은 군비 경쟁 정점의 4 판 차 (통계적으로 구분 안 됨). 양측 KL ≈ 0.002~0.005 (early-stop
  문턱의 1/10), 판별기 acc 0.16 (우연 0.125) → 다양성 패널티는 episode 당 ≈ −0.74 의 step 비용.
- **scripted fallback × r_fire 측정** (`8225aa7`, JAX 지적 재측정): 직진 homing 상대로
  `scripted_fin12` 는 net-only (miss handoff 0 회) — fallback 구조적 불가. net 포획은 r_fire ≤ 12 m
  에서만 성립, r_fire 40 은 HARD_KILL 4/24 뿐 → "넓은 r_fire 로 net 후 kinetic" 은 K_FIRST 에 지배
  (ROE A안 근거 보강). 평가 계약 불변 (최강 scripted = kfirst50).
- **★ 사다리 spec 버그** (JAX 세션 보고, main 확인; `9f960b8`, docs/123 §8.1): FS1 train·bc·eval 이
  사다리 공격자를 `AttackerSpec` 기본값 위에 생성 → 24 config 전부 jink 0 (공칭 0.6),
  t0_route0 ≡ a1_pure, (lean) bait_priv ≡ bait_fair, jink 위상 항상 0. **run1~3 pool·BC·"사다리"
  수치 전부 jink 0 변형.** 수정 = `train.ladder_attacker` 한 곳 (공칭 spec + sense ∞ + override,
  위상 `derive_phase`). eval v1 은 봉인 그대로 (`--ladder legacy`) + deviation 명시,
  **v2 addendum 봉인** (`f9e819e0d1171054`): 공칭 사다리 셀 재평가, 다르면 v2 가 governs.
  공칭 사다리 재측정: fin12+fallback 24/24 (net 2 + HARD_KILL 22 — jink 가 net 을 무력화, fallback
  이 대신 막음), kfirst50 24/24, r_fire 결론 불변.
- **★ r4 결정 (사용자 "(a), 고칠 거 다 고쳐서 한 번에")** (`433dcbd`, 반복 manifest
  `f6b1fc01e912497e` → r2 `a38993a8541264cd` — 판정 평가 환경 = **server4 고정** 추가 (i9-12900K;
  kfirst50×jink 셀이 마이크로아키텍처 간 반올림에 민감, 사용자 지시). r4 학습 전 개정, docs/123 §9): run3 → **pilot** (확정에 안 셈, r4 와 pooling 금지).
  r4 = r3 + 공칭 사다리 (pool·BC) + 다양성 패널티 off + KL 목표 lr (0.01, ×/÷1.5, [1e-5, 3e-4]) +
  워커 torch 시드. 확정 = r4 seed {0,1,2} 중 ≥ 2 POSITIVE/NARROW (v2 판정 기준). 관측 스택은 보류.
  `scripts/run_fs1_r4_server.sh` (seed 별 BC → 학습 → 봉인 평가, flock git, main() 래핑).
  manifest 본문의 "2026-10-05" 표기는 해시 봉인이라 유지 — 같은 10/04 세션.
- **run3 중단 안 함** (사용자 거부 + JAX 세션 의견 일치): 1.1e8 완주해야 v1 평가가 유효
  (lineage 조건) → pilot 기준점·서버 평가 파이프라인 시운전. 종료 예상 05:35 전후.
- **★ 계획 변경: r4 는 JAX 학습기 완성 후 JAX 로 학습** (사용자: 기존 run 너무 김). 확정 = 학습만
  JAX, **판정 평가는 정본 (torch/CPU) 으로만**. JAX 진행: M4.5 (main 재동기화 — jink 이식 필수,
  golden 을 수정된 생성 함수로 재생성), M5 (PPO, 출력 = 정본 eval 이 읽는 ckpt 형식, parity
  (a) forward (b) PPO 1 회 갱신 (c) PFSP·KL-lr 단위 (d) 짧은 예산 비교 보고). 처리량 ≈ 5~6.6만
  step/s (정본 ≈ 17 배, 1.1e8 ≈ 35 분). 알려진 deviation: f32 허용치 3 건, **학습 batch = 절단 +
  bootstrap** (정본은 완결 episode) → r4 manifest 개정에 학습 전 명시 필요.
- **exploiter 의 JAX 이전은 조건부** (평가 계약의 일부라서): run3 pilot 에서 정본 exploiter 와 JAX
  exploiter (같은 상대·1e7·seed 261100/261200) 를 정본 eval 로 비교 → 겹치면 계약 개정 봉인, 두
  exploiter 는 같은 방식으로. 안 겹치면 정본 유지 (그래도 3 seed ≈ 3~4 h). 판정 평가 판 자체 (≈ 10 분)
  는 정본 고정. exploiter 예산 1e7 은 이번 계약에서 유지, 큰 예산 exploiter 는 보고용.
- **예측·다음 (Claude 의견)**: pilot = NULL 유력, r4 = NULL 유력 · NARROW 가능 (경계 cell 은 적응형
  공격자 유리: 20.5 vs 7.16 m/s²). NULL 이면 ex_kfirst50 셀 = 세계의 천장으로 "학습 실패 vs 아무도 못
  막음" 구분. JAX 로 열린 다음: ① **예산 스케일링 곡선** (1e8/1e9/5e9, 보고용 — 10-04d 의 "null =
  예산 부족" 대안 가설 직접 검정) ② cell regime 지도 (어떤 기동성 비율에서 학습 이득). 연산이 더는
  병목이 아니므로 결과 전 봉인 규율을 더 엄격히.
- **r4 실행 전 남은 순서**: JAX 봉인 v2 (~03:30) → run3 완주 (~05:35) → pilot 정본 평가 → exploiter
  비교 → r4 manifest 개정 봉인 (구현 = JAX commit + parity hash, batch 구조, 예산 1.1e8, exploiter
  방식) → r4 BC (정본 CPU) → r4 JAX 3 seed + 정본 평가. **r4 실행 전까지의 기록은 이 노트 (10/04) 에.**
- **★ run3 pilot 판독 = FS1_NULL (v1·v2 일치)** (harvest `d34a931`, 상세 = 노트 2026-10-04f):
  D_pool −27 · D_ex +6 · D_ladder −171 (v2). **천장 발견: kfirst50 조차 전용 exploiter (1e7) 에
  3/240 = 1.3%** — 이 cell 은 적응 공격자 앞에서 아무도 못 막는다 (학습 실패가 아니라 세계 구조).
  궤적: 학습 방어는 spawn 즉시 전원 무장 → PN 장거리 추격 산개 (iter 119 창발 소멸), exploiter 는
  5~10 m 종말 1 회 회피로 K_FIRST·net 동시 무력화. mode-rank reversal 없음. r4 는 계약대로 실행하되
  학습 우위 주장은 regime 축 (E3) 으로.
