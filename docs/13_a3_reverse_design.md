# 13 — A-3 설계: L-reverse 후진 커리큘럼 (v0.3 — 파일럿 FAIL(09 (ff)) 반영, A-3b 수정안 §8 비준 대기)

> 입력: 12 §4 사다리(NF 열 A-3) · 09 (cc) A-2 kill 증거(벽 (0.1335, 0.1501]·발사-EV 수리 무효·쌍안정 스위치-오프) · P4 (s)/(u) 실측(capture-grade clean 상태 실존, ρ 0.05~0.2m·p_feas~1e-3·release-채널 기하).
> **단일 가설: clean 발사는 학습 가능한 행동이다 — 나쁜 스폰 분포 아래서 발견이 안 될 뿐.** 검증 = 아는 지점(실측 clean 상태)에서 역류.

## 0. A-2와의 구조적 차이

| | A-2 (killed) | A-3 |
|---|---|---|
| 커리큘럼 축 | 콘 폭 (넓게→좁게) | **스폰 분포 (말단→기점)** |
| 콘 폭 | 사다리 k/8 | **상시 frozen(0.067) 고정** — 폭 사다리 폐지 |
| 보상 스캐폴드 | graded λ1·λ2 완화·w_gf | **없음 (0개)** — 판정 J 그대로 학습 |
| 가설 | 발사 EV/gradient 부족 | 표현·발견(기하) 문제 |

- 보상 무개입 = A-2 대비 confound 제거. 스폰 분포가 유일한 스캐폴드, **eval 경로 스폰은 frozen 불변** (STRICT lock, 테스트).

## 1. 스폰 세트 T0 [R-1]

- 출처: `results/p4_probe/probe_s*.json`의 `refined_best` (4본: s12v16, s16v20×2, s20v24) — capture-grade witness (v_soft 1.0·¬boxed·worst 1.0·p_feas ~2.4e-3).
- 재구성: 기하 파라미터(공격자 x·v, limiters 4 위치, 그물 ρ/phase/c) → env 스폰 좌표(공격자 pos/vel·limiter p0·finisher pose) 매핑기 구현.
- **재검증 assert (비준 조건)**: 재구성된 스폰에서 frozen env로 v_soft·boxed·clean 재계산 → capture-grade 재현 안 되면 해당 상태 제외 (전부 탈락 시 A-3 설계 무효 → 09 기록 후 재설계).

## 2. R-스테이지 (후진 확장)

| stage | 스폰 | exit (train-eval) |
|---|---|---|
| R1 terminal | T0 + σ_pos 0.5m·σ_vel 5%·수율 소량 지터 | clean_cross ≥ 0.5 지속 2-eval |
| R2 | σ_pos 1.0m | clean ≥ 0.3 지속 2 |
| R3 | σ_pos 2.0m + 공격자 접근-역방향 Δx 5m 후퇴(v nominal 접근) | clean ≥ 0.2 지속 2 |
| R4 | σ_pos 4.0m + Δx 15m | clean ≥ 0.1 지속 2 |
| R5 nominal | **frozen 스폰 (layout 그대로)** | frozen-heldout clean 최근-3 비영 |

- 전진/백오프/cap 기계 = A-2 adaptive 커리큘럼 재사용 (지속 2-eval 전진·비-ok stall 3 백오프·예산 cap freeze = stall 스테이지 증거). 예산: S2상당 구간 cap 300k.
- 함정 명시: R5 전이 실패(privileged 스폰에서만 성능) = 분포-연결 실패 — 그 자체가 "2단 행동 필요"(L-2stage) 신호로 기록.

## 3. 학습 실행 [R-2]

- **arm = scratch 기본** — warm은 radial·무발사 습관 상속 위험(A-2 쌍안정이 그 습관의 견고함을 실증). docs/11 §3 규칙 ④(비교 우위 없으면 scratch) 정합.
- warm 1-seed **참고런** (diagnostic-only, 선택 판단에 사용 금지).
- 레시피 = recipe-v2·mix 0.5 동일. 파일럿 = scratch 3-seed × 400k (+warm 1-seed).
- obs-norm: scratch는 fresh 통계 (privileged 스폰 분포로 초기화됨을 기록 — R5 전이 시 norm drift 캐비앗).

## 4. 파일럿 중간 게이트 (사전등록) [R-4]

통과 = (i) ∧ (ii), 또는 (iii):
- (i) R1 통과 ≥2 seed — **실패 시 표현 가설 기각 위험**: 정답 근방 스폰에서도 clean을 못 쏘면 스폰이 아니라 행동 표현 문제 → L-2stage 직행 신호 (사다리 A-4/A-5 순서 조정 검토).
- (ii) R3 이상 도달 ≥1 seed.
- (iii) frozen-heldout clean 비영 ≥1 seed (즉시 통과).

## 5. 판정·다음

- 본선(통과 시): 10-seed → eval_heldout_m3 → analyze_gate_a — **Gate A/B·M3b 진입 조건 불변** (docs/11 §4·§5).
- 실패 시: 증거 테이블 행 추가 → A-4 (S-6 재검토 or L-release 추가) or L-2stage — (i) 결과가 순서 결정.

## 6. 구현 과제 (비준 후)

1. **스폰 주입 (리스크 1순위)**: M3 조립 루트에 학습-전용 reset 옵션 (백엔드 상태 오버라이드 — RotorPy vehicle state set 경로 확인 필요; eval 경로 접근 불가 STRICT lock + 테스트).
2. probe→spawn 재구성기 + 재검증 assert (§1).
3. Curriculum `reverse` 모드 (adaptive 기계 재사용, 폭 대신 스테이지 인덱스).
4. config `m3a_a3_pilot.yaml` + 테스트 (재구성 lock·주입-eval 격리·스테이지 전이).

## 7. 비준 체크리스트 (Hyunjun R-슬롯)

- [x] **R-1** T0 재구성·재검증 절차 + 탈락 규칙 (§1) — 2026-07-14 비준; **샌드박스 실측 4/4 PASS**(spawn_bank CLI, v_soft 全 1.000)
- [x] **R-2** scratch 기본 + warm 참고런(선택 금지) (§3) — configs 2본(diff = warm_start·wandb만, 테스트 lock)
- [x] **R-3** R-스테이지 파라미터 (§2) — m3a_a3_pilot.yaml에 사전등록값 그대로
- [x] **R-4** 파일럿 중간 게이트 + (i) 실패 시 L-2stage 신호 (§4)
- [x] **R-5** "보상 스캐폴드 0, 스폰 분포만" + eval 스폰 frozen STRICT (§0·§6) — 구조 보장: reverse 모드 overrides() 상시 None + 스폰 경로 소스-lock 테스트

## 8. A-3b 수정안 (09 (ff) 교란 실측 반영 — 비준 대기)

파일럿 FAIL의 원인 = 설계 파라미터 교란 2건(σ 0.5 ≫ clean 창 0.05~0.2m → 스폰-clean 0/10; T0 3/4가 union-표본 비강건). **robust witness 실존 실측**(x20v24u0: fresh seeds 8/8 clean, v_soft 고정 1.00) → 노선 유지, 재파라미터화.

| 항목 | A-3 (killed) | A-3b |
|---|---|---|
| T0 | probe 자기-seed capture-grade 4본 | **robust bank**: robust_clean_frac ≥ 0.9 (E_seeds[clean], 10 seeds) — probe 재실행으로 ≥3본 확보 목표 |
| σ-사다리 | 0.5 → 4.0 m | **0.02 → 0.05 → 0.1 → 0.2 → 0.5 → ...** (창 폭 이하 시작, 기하급수) |
| exit | 절대 clean ≥ 0.5/0.3/... | **상대화**: exit_clean = 0.5 × 스테이지 스폰-clean 베이스라인(probe 사전 측정) |
| L-2stage 신호 | R1 실패 시 | **A-3b R0 실패 시에만** (표현 테스트 성립 후) |

- [x] **R-6** robust-witness probe — 2026-07-14 비준·실행: **bank 3본**(x20v24 1.00 / x16v20 0.50→1.00 / x12v16 0.38→0.90; val seeds 200–209 서로소), `results/a3_robust_bank.json` (09 (gg))
- [x] **R-7** σ-사다리·상대화 exit — σ-베이스라인 실측(0.02→~0.35 … 0.5→0) 기반, floor 0.10 = eval 해상도; `configs/m3a_a3b_pilot.yaml`
- [x] **R-8** verify_t0 robust 게이트 — `robust_min`/`robust_seeds` 파라미터로 승격, a3b config는 0.9 × 10-seed; 구-뱅크 탈락 lock 테스트

## 9. A-3b′ 수정안 (외부 감사 리뷰 반영, 09 (hh) — **T-1~T-5 비준·구현 완료 2026-07-15, 09 (ii)**; T-2b는 oracle 실측으로 불발동·보류)

| # | 수정 | 근거 |
|---|---|---|
| T-1 | **forced-first-fire oracle 선행 게이트**: bank×≥100 CRN, 4시점(reset/commit/스텝2대조/resolution) 계측 + dwell-vs-fire 귀속 return; 통과 = commit-clean ≥ 0.8 | 리뷰 최우선 권고; R0 해석 가능성의 전제 |
| T-2a | R-exit 지표 **clean_cross → captured_rate** (문턱 동일) | dwell-게이밍 차단(clean_cross는 무발사로 달성 가능) + 무학습 baseline=0으로 통계 유의성 확보 |
| T-2b | (조건부) **ep_len 스테이지 스캐폴드** R0≈20스텝 | dwell-annuity(≈66) ≫ fire(≈27) 실측 시 인센티브 균형 장치; oracle 결과 후 결정 |
| T-3 | cap 300k → **360k**, total 450k → **520k** | 최소소요 286,720 vs cap 300k = 여유 13k < eval 1회 (기계적 불능) |
| T-4 | 파일럿 = **말단 행동 습득 실험**으로 재프레이밍; v2 = 성공 궤적 스냅샷 되감기 예약; R5→R6 리미터 보간 = confirmatory 전 필수 | config-only 스폰의 구조 한계(리미터 속도 0·이력 무) |
| T-5 | 진단 표(§10) 채택 | 실패 위치별 판독 프로토콜 |

정정 2건(코드 실측): 판정은 pre-move commit 시점(스텝1 발사 = 주입 상태 판정; capture = commit 동결) — 단 스텝1 union은 fresh CRN(robust bank의 존재 이유)이고 **스텝2+ 발사는 창 밖**(R0 = "스텝 1 발사" 테스트로 협소); deterministic eval Bernoulli는 (p>0.5) 엄격 부등이라 초기 무발사 정상.

## 10. 실패 위치별 진단 표 (리뷰 채택)

| 관측 | 최우선 의심 원인 |
|---|---|
| R0 全 seed 실패 | oracle로 선판별: state injection/타이밍 vs fire plumbing vs dwell-annuity |
| R0 일부 성공 | CRN flip·speed draw 불일치·Bernoulli 조기 붕괴(로짓 시계열 확인) |
| R0 통과, R1 급락 | 3-상태 암기·속도/컨트롤러 불일치·RunningNorm 과적합 |
| R1~R2 통과, R3 정체 | config-only 후진 한계(유효 셰이핑 gradient 부재) — v2 신호 |
| R3~R5 오실레이션 | 20판 게이트 잡음·백오프 분포 순환·value-norm |
| R5 통과, R6 붕괴 | 리미터 스폰 절벽·obs/critic OOD (사전 예측됨 — 후진 실패로 오독 금지) |
| train-eval 성공, heldout 0 | CRN 과적합·best-ckpt 선택 불일치(frozen-only sel_score) |
