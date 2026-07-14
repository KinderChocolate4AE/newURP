# 12 — A-캠페인: capture-unlock 레버 사다리 (v0.2 — S-1~S-5 비준 + S-6 폴백 등재, 2026-07-14)

> 입력: 09 (y) Gate A/B FAIL · P4 (s)/(t)/(u) · docs/11 v0.2. 이 문서는 **진단 데이터 접촉 전에 커밋**되는 사전등록이다 — 임계값·브랜치 규칙·사다리 순서는 이 커밋으로 고정.

## 0. 방침 개정 [S-1]

(y)의 "A 1~2회 제한 → 실패 시 B" 기본선을 **A-전력 레버 사다리 캠페인**으로 개정 (Hyunjun 결정 2026-07-14 — novelty의 본체는 capture-unlock 성공이라는 판단).

- 시도당 **가설 1개**(동승 스캐폴드는 confound 캐비앗 명기), 실패도 기전 증거로 계측 — "음성=자산" 프레이밍과 정합: 캠페인 증거 테이블(§6)은 실패 시 그대로 벽 논문의 evidence 섹션이 된다.
- **하드 트립와이어 = 2026-08-31**: 이후 신규 A-학습 런 금지 → B 프레이밍(M2 레버 + findability 벽 + 기전 증거) 확정. 예산: ~6주, 시도당 ~1주 → A-2 ~ A-5.
- 교수님 공유 = 통보형: "A 전력, 트립와이어 8/31, 실패 시 B" (질문형 A/B 상의 아님).

## 1. 불변 원칙 (docs/11 계승)

1. **M2 동결 계약 불변.** M3 env 변형은 비동결이나, frozen 4종·기존 파일 diff 0 유지.
2. **판정 경로 불변**: eval = frozen 상수 + P1 held-out CRN(77M, 학습 seed 서로소) + `analyze_gate_a` — Gate A/B·strong·paper-grade 정의(docs/11 §4) 무변경. M3b 진입 조건(§5)도 무변경.
3. **신규 보상항 = 스캐폴드 전용**: 커리큘럼 스테이지에서만 활성, S3/frozen 판정 J = docs/11 §1 그대로. "커리큘럼 성공 ≠ main claim" 원칙 유지 — 레버는 findability를 공략하고, 주장은 frozen에서만 나온다.
4. best-ckpt 선택 지표·참고점수식 무변경 (docs/11 §3).

## 2. Step 0 — 실패 모드 진단 (학습 런 아님) [S-2]

도구: `shepherd/scripts/a2_fire_mode_diagnosis.py` (numpy-only, torch 불요).
입력: (y) 아티팩트 `results/m3a_heldout/m3a_full_seed*.json` (+ `results/m3a_full/seed*/eval_curve.json`).

**사전등록 판정 규칙 (데이터 접촉 전 고정):**

| 조건 | 모드 | 브랜치 |
|---|---|---|
| fire_ep_frac < 0.05 | NO_FIRE (무발사 붕괴) | NF |
| else boxed_at_fire ≥ 0.5 | BOXED_FIRE (boxed-발사) | BF |
| else | CLEAN_MISS (비-boxed 미스) | CM |

- 종합 = seed-모드 최빈값; **합의 = ≥70% seed 일치**, 미달 시 MIXED(primary = 최빈, 동률 시 표기 순서 NO_FIRE > BOXED_FIRE > CLEAN_MISS).
- 부가 산출: **S2 붕괴 폭** — train-eval clean < 0.1 최초 지속 지점의 램프 분율 → (half_angle, θ) 환산. 캐비앗: s2 진입 = eval 라벨 기준(케이던스 ~20k 스텝 근사) — 진단 전용.
- 서버 실행 (TMPDIR=/data 권장, (y) ops 캐비앗):
```
python -m shepherd.scripts.a2_fire_mode_diagnosis \
    --heldout-glob 'results/m3a_heldout/m3a_full_seed*.json' \
    --curves-glob 'results/m3a_full/seed*/eval_curve.json' \
    --out results/m3a_heldout/a2_fire_mode.json
```
- 결과 JSON은 커밋해 회수 (Hyunjun push).

## 3. 레버 풀 (가설 명시; run-1 시작값은 비준 대상)

| 레버 | 내용 (전부 스캐폴드 — S3/frozen J 불변) | 가설 | 근거 |
|---|---|---|---|
| **L-margin** | binary λ1·1[clean] → S1·S2 동안 graded λ1·σ((v−θ_stage)/τ_m)·1[¬boxed], τ_m=0.05; S3 진입 시 binary 복원 | binary clean은 좁은 콘에서 너무 희소해 gradient 소실 | P4 요건 B ("binary λ1 불충분") |
| **L-release** | boxed_dwell per-step 패널티 −λ_bd(0.02) + release_event 원샷 보너스 +r_rel(0.5, 에피소드당 1회); S1~S2 활성 | boxed 분지 심부(unbox 0.2~1.0m+)에서 탈출 gradient 부재 | P4 (u) 40/40 deep-boxed·release 채널 필요성 실측 |
| **L-fire** | S2 동안 λ2(wasted) 1.0→0.3 인하 후 램프 완료 시 3-eval에 걸쳐 복원; w_gf 1.0→1.5 옵션 | 좁은 콘에서 wasted 기대비용이 발사 시도를 지배 → 발사 소거 | (y) ret −1.0~0.0·clean 붕괴 |
| **L-adaptive** | S2 시간-선형 램프 → 폭-스텝 8개로 이산화, 전진 = 현재 폭 train-eval clean≥0.1 최근-2 지속, stall 3-eval 시 1스텝 백오프, S2 상한 **340k**(정정: 8스텝×지속2×케이던스 20,480 = 327,680 최소 소요 → 300k는 완주 불가; 구현 강제 S-4 부속 수정, 09 (bb)) — 미달 시 stall 폭 기록 후 정지 | 전이 압력이 학습 속도와 미스매치 (시간-선형 램프가 붕괴 지점 정보도 안 남김) | (y) 전 seed s2 정지 |
| **L-reverse** | 후진 커리큘럼: P4 probe의 capture-grade clean-fire 상태 4본 근방 스폰(σ_pos 0.5→2.0m 스케줄, 후진 5단) → release→fire 말단 체인부터 학습; **eval 스폰 frozen** | clean = 비-방사 release 기하 + p_feas~1e-3 → 전방 탐색 발견 불가, 도달가능 상태의 역방향 확장으로만 발견 | P4 (s) 면도날 창 실측 + (u) release 채널 |
| **L-nearcap** | near-capture 항 — **[docs/11 수정 4] 예약 유지**: clean>0 ∧ capture=0 도달 시에만 해제 | — | docs/11 §1 |
| **L-2stage** | 명시적 compress→release 2단 행동 구조(모드 스위치/옵션) — **최후 레버** (행동공간 변경, 무거움) | clean 발사는 단일 반응 정책으로 표현 불가 | P4 (u) 2단 행동 실측 지지 |

## 4. 브랜치별 사다리 (사전등록 순서) [S-3]

| 시도 | NF (무발사) | BF (boxed-발사) | CM (clean-miss) |
|---|---|---|---|
| **A-2** | L-fire + L-margin (+L-adaptive) | L-release (+L-adaptive) | L-margin (+L-adaptive) |
| **A-3** | L-reverse | L-reverse | L-fire 조정 or L-reverse |
| **A-4** | + L-release | + L-margin | + L-release |
| **A-5** | L-2stage | L-2stage | L-2stage |

- MIXED: primary 브랜치 사다리 + A-2에 secondary 레버 1개 동승 허용 (confound 캐비앗 명기).
- L-adaptive는 보상 무변경 스캐폴드라 A-2에 동승 (동승분은 stall-폭 계측기 겸용; A-2 실패 시 stall 폭이 기전 증거).
- 각 시도 착수 전: 코드/설계 diff → **Hyunjun 비준(S-슬롯)** → 런치. 시작값 조정은 비준 시점에 확정.

## 5. 시도 프로토콜 (각 ~1주)

1. 설계·구현·테스트 (t-free 로컬 green + torch는 서버 실측 — (w-1) 교훈: "수집"≠green).
2. **3-seed 파일럿** (S1+S2 커버, ~350k): **중간 게이트** = (i) S2 stall 폭이 직전 시도 대비 개선(더 좁은 half_angle에서 train-eval clean≥0.1 지속) **또는** (ii) frozen-heldout clean 비영 ≥1 seed. 미달 → 레버 kill, 기전 로그 회수, 다음 레버.
3. 통과 시 **10-seed 본선 500k** → `eval_heldout_m3`(77M CRN) → `analyze_gate_a` 정식 판정.
4. 결과 무관: 09 로그 엔트리 + §6 증거 테이블 행 추가 + fire-모드 재진단(Step 0 도구 재사용).

## 6. 판정·종료·증거 테이블

- **성공** = Gate A PASS ∧ capture ≥2 seeds (docs/11 §4·§5 그대로) → **M3b 진입** (2~3주 박스, frontier = main figure).
- **트립와이어** = 2026-08-31 후 신규 A-런 금지 → B 프레이밍 확정: main = M2 레버(L2 게이트 PASS) + findability 벽(본선 held-out 하드 0) + 기전 증거 테이블.
- 증거 테이블 (시도별 1행, 갱신 = 각 시도 마감 시):

| 시도 | 브랜치 | 레버 | 단계 | 벽/stall 폭 (ha) | fire-모드 | heldout clean | cap | 기전 한 줄 |
|---|---|---|---|---|---|---|---|---|
| A-1 (09 (y)) | — | 원처방(시간-램프) | 10-seed 본선 | 사멸 0.127 / 생존 0.146 (램프 통과) | NO_FIRE 10/10 | 0 | 0 | S2 anneal 절벽 — 무발사 붕괴 |
| A-2 (09 (cc)) | NF | L-fire+L-margin+L-adaptive | 3-seed 파일럿 | 지속 0.1501(k=3) / 즉사 0.1335(k=4), 정적-폭 적응에도 | NO_FIRE (k≥4) | 0/200 ×3 | 0 | 발사-EV 수리 무효 → 표현/발견(기하) 가설 강화 |

## 7. 비준 체크리스트 (Hyunjun S-슬롯)

- [x] **S-1** 방침 개정: "1~2회 제한" → "전력 사다리 + 트립와이어 8/31" (§0) — 2026-07-14 일괄 비준 (09 (aa))
- [x] **S-2** 진단 규칙: 임계 0.05/0.5, 합의 70%, 동률 순서 (§2) — 판독: **NO_FIRE 10/10 → 브랜치 NF** (09 (aa))
- [x] **S-3** 레버 풀·브랜치 사다리·시작값 (§3·§4) — 단 L-adaptive S2 상한 300k→**340k** 구현 정정 (§3 표)
- [x] **S-4** 시도 프로토콜 (§5) — A-2 중간 게이트 정량화: train-eval clean≥0.1 지속 @ **ha<0.1274**(A-1 사멸 폭) or frozen-heldout clean 비영 ≥1 seed
- [x] **S-5** "신규 항 = 스캐폴드 전용, 판정 J·게이트 정의 불변" 원칙 (§1) — lock: tests/test_a2_scaffolds.py (판정 비트-동일)
- [x] **S-6** 수동-평형 폴백 (09 (aa)): "교전/침투 스캐폴드 비용"은 A-2 **미포함** — A-2 파일럿에서 λ2 완화에도 fire 사멸 지속 시 발동하는 사전등록 폴백으로만 등재
- [ ] 교수님 공유 문구(통보형) 확정 (§0)
