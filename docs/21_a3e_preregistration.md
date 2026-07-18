# 21 — A-3e 사전등록 패키지 (v0.3, 2026-07-18 — **동결본**; 3자 조건부 승인 20항 반영·Hyunjun 비준 완료)

> **상태**: v0.2가 3자 검토에서 **조건부 승인**(접수본 = `URP/a3e_external_review_2026-07-18.md`; E-1 수정승인 / E-2 조건부 / E-3·E-4 중요수정후승인 / E-5·E-6 수정승인, 필수 체크리스트 20항 + 잔여 자유도 37건). 본 v0.3이 전 항목을 반영하며(대조표 §11), Hyunjun 비준 2건: ① 20항 일괄 수용 ② 4.1 상태 복원 = **계약-정합형**. **본 커밋이 A-3e 동결 커밋** — 이후 수치·규칙·seed는 결과를 보고 변경하지 않는다. 재검토 라운드 없음(리뷰어 조건부 승인 취지).
>
> **불변**: 판정 J·게이트 정의·평가 경로·σ 램프 / bank v2 재생성 금지(소진) / **rewind-v2 1회 생성 원칙(신설)** / sealed 불가침 / 문턱 사후 조정 금지 / 하드 스톱 **2026-08-31**. **B의 정의(재수록)**: active curriculum 개발을 종료하고, synthetic·on-manifold 전임자의 σ-강건 도달성 실패를 중심 증거로 하는 failure-mode/진단 프레이밍으로 전환하는 노선(docs/12 트립와이어 조항).

## 1. 배경·증거 (v0.2 §1–2와 동일 — bank v2 FAIL 표 포함; 여기서는 불변 참조)

측정기·4조건·bank v2 validation 7셀 표·FAIL 판독은 v0.2 §1–2 그대로(변경 없음). A-3e 가설: **학습 성공 실궤적에서 수확한 전임자(on-manifold)는 폐형식 합성 전임자보다 같은 σ에서 강건하다** — 본 문서가 그 검증 설계의 동결본.

## 2. [E-1] 스코프·클레임 (Tier 분리 — 3자 채택)

- bank-v2-d1 = admissible 24 draws 부분집합(v16/d1 12 + v20/d1 12; 원본 불변·필터 기록). 범위 문구 = **"one-step local reshaping + 발사 결합"**(장기 협력 성형 아님).
- **Tier 1**(중간 산물): action-necessary one-step predecessor에서 teacher-gated 발사 하 limiter 정책이 zero 대비 유의한 local capturability 회복을 학습. **Tier 2**(P1′ PASS의 정의): limiter local reshaping + finisher **autonomous fire**(teacher-free)를 결합한 포획 정책 학습. teacher-assisted 결과만으로 "재성형-후-발사 학습" 주장 금지.

## 3. [E-2] d1-only 번들 (수치 동결)

- **dev-v2d1 / sealed-v2d1**: jitter rng 75,000 / 95,000(파생 = base+1,000·k+int(v), build_bundle 기제), reset seed base 12.0M / 13.0M(에피소드 seed = base + 10,000·stage_idx + i). 구성(두 번들 동일): **d0 = 40판**(witness 2본 × 20, σ=0 정확 스폰) + **d1 = 120판**(= 24 draws × 5, 셀 균등 60:60, draw 라운드로빈 (cell, draw-index) 사전순 — 120이 24의 배수라 잔여 0; 일반 규칙 = 잔여는 draw-index 오름차순 1판씩). SHA-256 manifest(번들·bank·필터·생성기 커밋·config·seed 대장·게인·Gate B·(추후) validation verdict + **seed→API 매핑**), sealed 불가침 테스트 4종.
- **outcome 계약(스테이지별 상이 — 3자 충돌① 수정)**: **d0 = fire-bootstrap 지표**(reset-clean 앵커라 arrival_capture ≡ 0 → paired-arrival exit 적용 불가): captured_rate(teacher 없음) 사용. **d1 = paired Δ = P(arrival_capture|π) − P(arrival_capture|zero)**(동일 episode).
- **zero-캐시 = dev 전용**(d1 스테이지, 생성 직후 1회 계산·동봉). **sealed은 사전 zero 롤 금지** — 최종 판정 시 learned policy와 zero를 **동일 episode에 동시 실행**하는 1회 소비로 기록(3자 수정).

## 4. [E-3] P1′ — 3-phase 구조 (F0→L1→J1; 전환·수치 전부 동결)

- **공통**: 3-seed scratch(train_seed 0–2), eval cadence = **20,480 steps**, 게이트 eval = 해당 스테이지 dev 번들 전판(d0 40 / d1 120). 매 eval 진단 로깅 의무: **P(fire|clean)·P(fire|nonclean)·P(capture|reset nonclean)** + teacher 보조 진단 3종.
- **F0 (fire bootstrap)**: 스테이지 d0, **limiter = hold(액션 0 고정)**, teacher 미사용, fire head 학습. exit = **captured_rate ≥ 0.45, 2-eval 연속**(A-3b R0 비준값 재사용). min 2 / **max 6 evals(122,880)**; 미달 = FAIL(사유: fire bootstrap 실패).
- **L1 (limiter acquisition)**: 스테이지 d1, **fire head freeze**(실발사 = teacher gate; non-clean 발사 차단 — d0 always-fire bias 격리), limiter 학습. gate = **Δ^teacher_d1 > 0.10, 2-eval 연속 → teacher 영구 해제 + L1 종료**(해제 후 재투입 금지 — 3자 권장안 채택). **max 8 evals(163,840)**; 미달 = FAIL(사유: limiter local shaping 실패; **fire unfreeze 없이 즉시 종료** = 추가중단①).
- **J1 (teacher-free joint)**: 스테이지 d1, teacher 완전 제거, fire head unfreeze(**fire-head optimizer state fresh 재초기화**, lr 스케줄 = 기존 그대로), limiter 계속 학습. stage exit = **Δ^free_d1 > 0.10, 2-eval 연속**; 정체는 stall 기록(하위 스테이지 없음 → 후퇴-재투입 없음, cap까지 진행). **max 8 evals(163,840)**.
- **총 cap = 450,560 steps**(= (6+8+8)×20,480; 최소소요 = 6 evals = 122,880 — "공식으로 유일 산출" 요구 이행). backoff/stall 1회 = eval 1회 소비.
- **best-ckpt(J1 후보만; 실행 전 동결)**: primary = dev Δ^free_d1 → tie-break1 = min P(fire|nonclean) → tie-break2 = 이른 ckpt. (구 nominal 스코어 폐기 — d1 목적과 정렬.)
- **P1′ 판정 = sealed-v2d1 1회 소비**(policy+zero 동시): seed별 Δ̂^free_d1 — **PASS = ≥2/3 seed > 0.10 ∧ 전 seed ≥ 0**; pooled = 진단; McNemar = seed별 보조. 소비 즉시 sealed 소진 선언 — ckpt 재선택·추가 fine-tune·재평가 금지(추가중단④). 명칭 = **sealed holdout pilot**(모집단 confirmatory 아님 — 3자 충돌⑤).

## 5. [E-4] 수확 → rewind-v2 (전 자유도 동결)

- **수확 실행**: P1′ PASS 시 3 training seed **전원**의 best-ckpt(sealed 성적 무관 — dev-선정이므로 sealed 비접촉) × 셀당 **150판 = source당 50판**(reset seeds **700–749**를 source 간 CRN 공유; episode key = (cell, source, reset_seed) — manifest 기록), 스폰 = d1 물질화(지터 rng **300,000+1,000·k+int(v)** — §6 재배치). **전량 실행 후 일괄 처리**(조기 중단 금지 — 3자 4.4).
- **스냅샷 후보**: 성공 에피소드(arrival_capture ∧ clean 발사)의 발사 스텝 F 기준 t = F−k, k∈{2,4,8}, 존재하는 k만 + **pre-commit 시점만 수락**(공격자 = commit 전 memoryless 순수 추격·반발 → p/v가 계약상 Markov 충분; post-commit 스냅샷 드랍·사유 기록).
- **계약-정합 복원 게이트(비준 ②; 스냅샷별 필수)**: 저장 = limiter p/v + attacker p/v(**스폰 계약의 전체 상태** — finisher/FSM = fresh가 계약, bank v2와 동일). reset_to 주입 → **기록 limiter 가속 개방루프 + teacher fire** 재실행: limiter 위치 궤적 atol **1e-3 m** ∧ clean 발사 ∧ arrival_capture 재현 — 미충족 드랍(사유 기록). (리뷰어 원문형 full-sim-state 방식은 reset_to 피니셔-불가침 동결 계약과 충돌하여 계약-정합형으로 대체 — 의도(불완전 복원 스냅샷 배제)는 본 게이트가 담당.)
- **dedup(state-aware — position-only 0.05m 폐기)**: d²(s,s′) = Σᵢ‖Δpᵢ‖²/τ_p² + Σᵢ‖Δvᵢ‖²/τ_v² + ‖Δp_a‖²/τ_pa² + ‖Δv_a‖²/τ_va², **τ = (0.05 m, 0.25 m/s, 0.05 m, 0.25 m/s)**(비실측 선택 — 자기신고), 같은 k 풀 내 d<1 병합(대표 = (cell, source, reset_seed, F) 사전순 최선). **순열 처리 없음 명시**: limiter 인덱스 = 역할·obs 슬롯 고정이라 순열 동치 부재.
- **선택(source-balanced 결정론 — 3자 4.2/4.4)**: k별 목표 12·최소 8. source별 기본 quota 4·**단일 source ≤ 6(50%)**·부족분은 (cell, source, reset_seed, F) 사전순 충당. **기여 source < 2 → 해당 k 결측**(추가중단③; 단일-seed on-manifold 클레임 금지).
- **RT-PFC(시간 정렬 명시)**: t=0 = 스냅샷 시점, a_rec(0) = 스냅샷 직후 실행 기록 액션, 참조 소진 후 = terminal hold(PFC 동일), **norm clip**(성분별 아님), 게인 (1.0, 0.5)·T_k = kΔt. **측정기 게이트(추가중단②; 실패 = "rewind 측정기 구현 실패"로 기록·중단 — 가설 기각 아님·게인 재튜닝 금지)**: **RT-1** no-jitter replay: RT-PFC 실행 ≡ 기록 궤적(atol 1e-3) / **RT-2** 고정 perturbation 세트(σ=0.005, 사전 고정 rng)에서 endpoint 오차 < open-loop replay의 **0.6배**(기존 PFC 락 계수 재사용).
- **rewind-v2 파이프라인**: 생성 screen = **candidate predecessor당 20판**(seeds **750–769**), paired RT-PFC/zero, PASS = 16/4/4 → 독립 validation = **4조건 n=100/셀**, seeds **800–899**, σ-물질화(지터 rng **310,000+1,000·k+int(v)**), 배정 = ⌊100/n⌋+잔여 index순, **12 arms 전 기록**(Gate A석 = RT-PFC; Gate B 8종 유지 — gap>0.4 셀 = **"privileged-feasible but hand-controller-hard"** 표기, 충돌④), 부트스트랩 **777 전 분석 공통(부트스트랩 간 독립성 비주장 명시)** + draw-cluster + **source-policy cluster** 병기(판정은 episode-primary).
- **판정 = k=2 pooled primary(안 A)**: 존재하는 k=2 셀 균등 가중 pooled(2셀 = 50:50)에서 4조건 전부 → **on-manifold 가설 채택**; 셀별 = secondary 보고. pooled 미충족 = 가설 기각(추가중단⑤) → B.
- **synthetic comparator(3자 4.8)**: 기존 bank v2의 k=2 3셀(v16/v20/v24 d2) draws를 **동일 프로토콜(seeds 800–899·동일 σ·판정 2-arm PFC/zero)로 고정 재평가** — Δ_rewind−Δ_synthetic·PFC 차 병기(descriptive; 재생성 아님 = 1회 원칙 무충돌).
- **클레임 경계(3자 4.9 수록)**: pooled PASS가 지지하는 것 = "학습 성공 궤적에서 수확한 two-step predecessor가 사전등록 RT-PFC 하 σ-강건 action-necessary 조건 충족". 일반 강건성·d2 curriculum 전체 복원·nominal 연결·다공격자 일반화는 **비주장**.

## 6. [E-5] seed·rng 대장 (재배치 + enumerate 테스트 락)

- **파생 재배치(3자 지적 — "대역명 안전성" 폐기)**: 수확 지터 = **300,000+1,000k+v** / rewind validation 지터 = **310,000+1,000k+v**(구 78k/79k대는 k·v 대입 시 80k/81k대 침범 위험 → 고대역 이동; 최대 파생 318,024 — 전 기존 파생·seed와 서로소). **동결 커밋에 전 파생값 enumerate + pairwise-disjoint 테스트 포함**(기존 71k/75k/76k/81k/93k/95k 파생 전부 나열 비교).
- **namespace 표(7종; manifest에 seed→API 매핑 포함)**: train_seed(0–2) / episode_reset_seed(700–749 수확·750–769 rewind screen·800–899 rewind validation·12.0M/13.0M 번들·기존 전 가족) / geometry_mc_seed(7–16·100–104·200–209) / spawn_jitter_seed(75k·95k·300k·310k 파생) / trajectory_harvest_seed(= 700–749 명시적 별칭) / arm_random_seed(90,000+7·reset_seed) / bootstrap_seed(**777 전 분석 공통**).

## 7. [E-6] 중단·전환 규칙 (9종; 각 발동 = docs/12 §6 증거 행, 사유 구분 기록)

① P1′ FAIL(F0/J1/판정) → B ② 수확 전 k 결측 → B ③ rewind pooled 기각 → B ④ 하드 스톱 8/31 → B **⑤ L1 미달 = fire unfreeze 없이 즉시 FAIL(사유: limiter shaping)** **⑥ 복원·RT-1·RT-2 실패 = "측정기 구현 실패" 기록·중단(가설 기각과 분리; 게인 조정 금지)** **⑦ source diversity < 2/k = 해당 k 결측** **⑧ sealed 1회 소진(재선택·재평가·추가 fine-tune 금지)** **⑨ k=2 multiplicity = pooled 규칙 외 판정 금지.**

## 8. 실행 순서 (동결)

본 커밋 → 구현(3-phase 트레이너·번들 d1-사영·수확/복원게이트/RT-PFC/rewind + 테스트; **결과 판독 전 커밋**) → P1′(서버, 3-seed) → sealed 판정 → [PASS] 수확 → 복원게이트·dedup·선택 → rewind screen → rewind validation + comparator → pooled 판정 → 판독. 1사이클 ≈ 1주.

## 9. 자기신고 (갱신)

① RT-PFC 실측 0 — RT-1/2 게이트가 측정기-실패를 가설-실패에서 분리. ② dedup τ·quota·판수는 비실측 선택. ③ 계약-정합 복원은 리뷰어 원문형(full sim state)의 대체 — finisher/FSM fresh가 스폰 계약이라는 논거에 의존(그 계약 자체는 bank v2와 동일하므로 comparator 비교의 공정성은 유지). ④ pre-commit 한정으로 k=4/8 결측 가능성 증가 — d2 재구축이 실질 목표임을 재명시. ⑤ near-miss(v16/d2 .79) 기대 편향 존재 — pooled primary가 셀 선택 자유도를 제거. ⑥ 777 공통 사용 = 부트스트랩 간 독립성 비주장.

## 10. 검토 이력

v0.1(E-슬롯) → v0.2(자기완결 3자 검토판) → **3자 조건부 승인**(체크리스트 20·자유도 37·충돌 5) → **v0.3 전 항목 반영 + Hyunjun 비준(일괄 수용·계약-정합형) = A-3e 동결.**

## 11. 3자 체크리스트 20항 반영 대조표

| # | 요구 | 반영 |
|---|---|---|
| 1 | d0 fire-bootstrap outcome·exit 별도 | §3·§4 F0 (captured 0.45) |
| 2 | F0→L1→J1 순서 고정 | §4 |
| 3 | teacher 해제 기준·재투입 금지 | §4 L1 |
| 4 | phase step cap·cadence 숫자 | §4 (20,480·6/8/8·450,560) |
| 5 | best-ckpt 선택식 | §4 |
| 6 | 번들 판수·draw 배분 | §3 (40/120·라운드로빈) |
| 7 | sealed policy+zero 동시 1회 | §3·§4 |
| 8 | source quota·≥2-seed | §5 (4/4/4·≤6·결측 규칙) |
| 9 | position-only dedup 폐기 | §5 (state-aware τ 4종) |
| 10 | Markov snapshot 목록 정의 | §5 (계약-정합: p/v + pre-commit 한정) |
| 11 | restore equivalence test | §5 복원 게이트 (atol 1e-3) |
| 12 | RT-1·RT-2 게이트 | §5 (추가중단⑥) |
| 13 | screen 단위 = candidate당 20판 | §5 |
| 14 | validation 균등 배정 | §5 |
| 15 | k=2 pooled primary | §5 (안 A) |
| 16 | synthetic comparator 병기 | §5 |
| 17 | seed enumerate·충돌 테스트 | §6 (300k/310k 재배치) |
| 18 | rewind-v2 1회 원칙 선언 | 서두·§5 |
| 19 | fallback B 정의 재수록 | 서두 |
| 20 | sealed = "holdout pilot" 표기 | §4 |
