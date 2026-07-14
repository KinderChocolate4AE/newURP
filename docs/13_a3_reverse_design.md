# 13 — A-3 설계: L-reverse 후진 커리큘럼 (v0.2 — R-1~R-5 비준·구현 완료 2026-07-14, 09 (ee))

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
