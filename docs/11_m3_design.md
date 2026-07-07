# 11 — M3 설계 v0.2 (조건부 비준 반영, 2026-07-07) — 구현 착수 승인

> v0.1 + 리뷰어 조건부 비준(수정 4건 + 게이트 tier) 반영. 입력: L2 게이트 PASS(09 (q)) · P4 (s)/(t)/(u) · 03 §G S9.
> 원칙: **M2 동결 계약 불변.** M3 = 신규 env 변형(비동결). 경제(frontier) 주장은 S9 raid에서만.

## 0. 구조 [비준]

**M3a "capture-unlock"**(corridor·1-attacker·K=1, 보상 기하 교체) → **M3b "S9 raid frontier"**(M>1·K binding, exchange frontier = 논문 main figure). 캡처 없는 raid는 K-경제 퇴화 → M3a가 전제. **M3b는 M3a 성공 전 구현 금지**(§5 진입 조건).

## 1. M3a 보상 (요건 A·B) [비준 + 수정 1·3 반영]

기호: v = v_shot_soft, o = p_feasible, boxed = (n_feasible==0), clean = (v≥θ ∧ ¬boxed).

**(A) v_effective — hard 문자형이 기본(main claim 기준), smooth는 ablation/debug 전용:**
```
v_eff = v · 1[¬boxed]                        # MAIN
v_eff_smooth = v · σ(margin/τ_m)             # ablation 노브 (기본값 금지)
```

**headline — M2-일관 hold-대비 level형, SIGNED 고정:**
```
headline_M3(t) = v_eff(full layout, t) − v_eff(hold layout, t)     # raw signed
```
- **불변식(비준 조건): 음수 유지 — positive-only/max(0,·) 클리핑 금지.** boxed 상태의 매 스텝은 clean 대비 ~v만큼의 headline을 즉시 상실(레벨형이므로 전이 시 advantage에 큰 음의 신호). 안정화가 필요하면 `clip(·, −c_neg, +c_pos)`만 허용하되 **negative side를 0으로 죽이는 것 금지.**
- 시간차형 `v_eff(t)−v_eff(t−1)`은 등가 gradient의 미분형 — ablation 노브로만.

**(B) 역-U 기하 보상 — per-step + fire-시점 분리 [수정 3]:**
```
g(o) = exp(−(ln o − ln o*)²/2σ_g²), o>0; g(0)=0.  o* = 1e-3, σ_g = 1.0
r_geo_step = v·g(o)                          # 상시(작게)
r_geo_fire = v_fire·g(o_fire)·1[fire]        # 발사 시점 보너스
```
- 루프-방지: 정책이 o≈o*를 유지하며 fire를 미루는 게이밍 가능 → run 1에서 fire 지연 관측 시 **사전등록 폴백: w_g(step) 1.0→0.3~0.5 + fire측 유지/증액.**

**전체 J_M3a (run 1 시작값):**
```
J = w_h·headline_M3 + w_g·r_geo_step + w_gf·r_geo_fire + λ1·1[clean] + λ_cap·1[captured] − λ2·wasted − λ3·limiter_loss
w_h=1, w_g=1, w_gf=1, λ1=1, λ_cap=5, λ2=1, λ3=0.5
```
- **near-capture 보조항(`clean·v·정렬근접`)은 1차 구현 금지** — clean은 뜨는데 capture가 안 뜰 때의 2차 처방으로 예약 [수정 4].
- obs: **o·boxed 노출 확인/추가**(M3 env 자유). 행동 공간 무변경(release는 기존 accel로 표현) — release 이벤트는 로깅으로 관측.

## 2. 커리큘럼 (요건 C) [조건부 비준 → 종료조건 강화]

| stage | 학습 상수 | 종료 조건 [수정] |
|---|---|---|
| S1 wide-clean | half_angle ×3(0.20), θ 0.8, σ_g ×2 | clean_cross(train-eval) > 0.2 지속 **∧ boxed_fire_rate < 0.5 ∧ fire_rate > 0** (capture는 대시보드 지표) |
| S2 transition | 선형 복원 → 0.067/0.9/1.0 | frozen 상수 도달 **∧ frozen-heldout clean_cross 최근-3 eval 비영(0 아님)** |
| S3 final frozen | frozen 상수, w_g 0.3, σ_g 1.0 | 판정용 |

- eval = 전 스테이지 **frozen 상수 + P1 held-out CRN 하네스.** 커리큘럼 성공 = main claim 금지.
- **o* 스윕 [비준 조건]: S1 한정 {3e-4, 1e-3, 3e-3}, 목적 = "탐색 scaffold 선택"(성능 튜닝 아님).** 선택 지표 = S1 train-eval clean discovery·boxed dwell 감소·o의 목표 근접 체류율. **frozen held-out은 monitoring only — 선택에 사용 금지**(tuning leakage 차단).

## 3. 학습 실행 (M3a) [수정 2·결선 규칙 반영]

- 레시피 = P1 확정 main recipe(blended mix 0.5, recipe-v2 계승).
- **웜스타트 결선(사전등록):** warm(mix0.5 best-ckpt) vs scratch, 3-seed × S1 200k. **선택 규칙(사전): ① clean_cross_rate 우선 ② 동률 시 boxed_fire_rate 낮은 쪽 ③ 그래도 동률이면 frozen-heldout clean 높은 쪽 ④ 유의미한 차이가 없으면 scratch**(L2 boxed-분지 편향 상속 회피). 참고 점수식: clean + 0.5·capture − 0.5·boxed_fire − 0.2·boxed_dwell.
- 본선: 선택 arm × 10-seed × S1→S3(500k+).
- **fire-체인 분해 로깅(필수, eval마다):** v_soft/v_eff/o/n_feasible/boxed/clean/capture/wasted@fire, fire_step, **release_event_before_fire**(o: 0→(0,o_hi] 전이), boxed_dwell_before_fire, |ln o − ln o*|. 학습 지표는 wandb-only 금지(직접 기록). ntfy 훅.

## 4. M3a 판정 (사전등록) [tier 분리 반영]

- **Gate A — clean unlock:** frozen held-out에서 clean_cross_rate seed-군집 one-sided 95% 하한 > 0.
- **Gate B — capture existence:** capture_count_total > 0 — **existence 서술 전용**("capture-unlock" 주장 아님).
- **Strong pass:** capture가 **≥2 train seeds에서 관측** 또는 mean capture_rate ≥ 1%.
- **Paper-grade pass:** capture_rate seed-군집 하한 > 0.
- 보조: L2 헤드라인 지표 non-inferiority(margin −1 이내).

## 5. M3b 진입 조건 + 박스 [비준]

- **진입(최소):** M3a frozen eval에서 Gate A PASS ∧ (capture ≥2 seeds 또는 총 capture 명백 비영). capture 1회뿐이면 M3a 보상 재처방 후 재시도.
- 박스: M∈{3,5}, K∈{1,2,3}, wave 스케줄러 + exchange.py 회계 이식, **2–3주 상한**, frontier 1장 = main figure. 공격자 = scripted 가족 + bait/exhaustion(+선택 exploiter probe).

## 6. 논문용 고정 문구 (리뷰어 제공, verbatim)

1. "headline_M3 uses the signed difference ... Negative Δv_eff is retained so that transitions from clean/high-v_eff states into boxed states create an immediate shaping loss." (레벨형 구현 시 '전이 시 per-step headline 상실'로 대응 서술)
2. "The S1 o* sweep is a scaffold-selection procedure only. ... All final claims are evaluated under frozen constants with the P1 held-out CRN harness."
3. "Warm-start wins the S1 play-in only if it improves clean discovery without increasing boxed-fire or boxed-dwell rates. If warm and scratch are comparable, scratch is selected..."
4. "Capture>0 is reported as an existence headline, not as a statistically stable capture-rate claim. Strong pass requires capture in at least two train seeds or a nontrivial mean capture rate under frozen held-out evaluation."

## 7. 비준 기록 (2026-07-07)

| 항목 | 판정 | 반영 |
|---|---|---|
| M3a→M3b 순서 | 승인 | §0·§5 진입 조건 |
| hard v_eff 기본 | 승인 | §1 signed 불변식 명문화, smooth=ablation |
| o*=1e-3 | 승인 | §2 S1-only 스윕·선택지표 고정 |
| 3-stage 커리큘럼 | 조건부 승인 | §2 S1/S2 종료조건 강화 |
| warm vs scratch | 승인 | §3 선택 규칙(④ scratch 우선 원칙) |
| M3a 판정 | 조건부 승인 | §4 tier 분리(existence/strong/paper-grade) |
| M3b 박스 | 승인 | §5 |

- 설계 결정 노트: headline의 Δ 의미를 **M2-일관 hold-대비 level형(signed)** 으로 확정 — 리뷰어 불변식(음수 유지·boxed 전이 즉시 손실)은 레벨형에서 충족되며, 시간차형은 ablation. (Hyunjun 확인 항목)
