# 21 — A-3e 사전등록 초안 (v0.1, 2026-07-18 — [R-1] 비준 반영; E-슬롯 비준 대기)

> **성격**: docs/20 [R-1] = A-3e 선택에 따른 사전등록 결정지. 신규 결정 = [E-1]~[E-6]; 그 외 전부 docs/19 v0.3 동결 사양의 재사용(측정기·게인·4조건·V-5′·exit·번들 조성 규칙·SHA-256). 비준(+3자 검토 1회 권장, docs/20 [R-3]) 후 구현·동결 커밋 → 실행. **불변**: 판정 J·게이트 정의·평가 경로·σ 램프·학습 금지(동결 전)·트립와이어 2026-08-31·bank v2 재생성 금지(소진).

## 1. 배경 (자기완결 요약; 상세 = 09 (iii)·docs/20 §1)

bank v2 독립 validation(n=100/셀·σ-물질화·4조건)에서 **admissible = d1 2셀뿐**(v16/d1 PFC .94·Δ̂ .91 LCB .86 / v20/d1 .95·.91·.86; reset_clean 0·p₀₁ 0). k≥2는 전멸 — 전부 [B] σ-하 PFC .61–.81 < .8 (v16/d2 = .79 near-miss; v24/d2는 [C·D] zero .39 추가) → **BANK FAIL 선언**(규칙 기계 적용). 벽 재정밀화: 행동 필요성(D 생존)이 아니라 **폐형식 후방합성(off-manifold·정지구성·이력무) 상태의 σ-강건 도달성**이 k=1 너머에서 붕괴. A-3e = 이 가설의 최소비용 검증 노선: **d1(가능 확인된 유일 지평)에서 학습 성립 여부를 판정하고, 성공 시 학습 정책의 실궤적 스냅샷(on-manifold)으로 d2를 재구축**한다.

## 2. [E-1] 스코프·클레임 경계

- **bank-v2-d1** = 기존 bank v2의 validation-admissible 부분집합 그대로: v16/d1 12 + v20/d1 12 = **24 draws**(신규 생성 아님 — 재생성 1회 원칙과 무충돌; 파일은 bank v2 원본 + admissible 필터 기록으로 구성, 원본 불변 보존).
- **클레임 경계**: P1′ 성공 = **mechanistic·D1 한정**("동결 판정 J 그대로, action-necessary k=1 전임자에서 재성형-후-발사를 학습 가능"). d1 = 2셀이라 스테이지 규칙상 정상 진행이나, 사다리가 d1뿐이므로 method-competence·가족 일반화 클레임 금지. A-3b spawn-luck 천장((kk))의 직접 후속 질문임을 명시.

## 3. [E-2] d1-only 번들

- **dev-v2d1 = {jitter rng 75,000, reset seed 12.0M} / sealed-v2d1 = {95,000, 13.0M}** — 0-e 예약분 그대로(취소된 번들은 미생성이라 오염 없음). 조성 = 19 v0.3 §8 규칙의 d1 사영: 셀 균등(v16:v20 = 50:50), 셀 내 draw 라운드로빈(비복원 순환), 스테이지 = **{d0(앵커: witness 슬롯 자체, σ=0), d1(bank-v2-d1 물질화, σ=.005)}**, SHA-256 manifest(대상 목록 19 v0.3 §8 그대로 + admissible 필터 기록), sealed 불가침 테스트 4종(경로 거부·symlink/복사·--force 부재·metadata 변조 검출) 구현 포함.
- **zero-캐시**: dev-v2d1 생성 직후 스테이지별 zero-arm outcome을 episode ID 단위 1회 계산·동봉(19 v0.3 §7 exit 기계의 입력).

## 4. [E-3] P1′ — d1 학습 파일럿

- 3-seed scratch(train_seed 0–2), 트레이너 = 기존 a3d sbe 커리큘럼에서 **스테이지 exit를 19 v0.3 §7 동결형으로 교체 구현**(전진 = Δ̂_d(policy−zero, 동일 ep)>0.10 2-eval 연속 / 후퇴 = UCB95(Δ_d)<0.05 ∧ stall 3; Wilson 게이트 폐지). teacher 보조 진단 3종(fresh-seed robust-clean·persistence·v_soft 마진) 로깅 등재(비구속).
- step 예산: **최소소요×1.2 룰**(T-3)로 구현 시 산출·동결(d0+d1 2스테이지 × exit 2-eval × 케이던스 기준; 수치는 구현 커밋에 명기 — A-2/A-3b cap 실수 재발 방지 항목).
- **P1′ 판정(V-5′ P1 규칙 그대로)**: sealed-v2d1에서 seed별 paired Δ̂ — **PASS = ≥2/3 seed Δ̂>0.10 ∧ 전 seed Δ̂≥0**; pooled = 진단; 클레임 = "pilot evidence". McNemar = seed별 보조. **FAIL → A-3e 종료·B 전환**(수확 진입 금지).

## 5. [E-4] 성공 궤적 수확 → rewind-v2

- **수확 하네스**(P1′ PASS 시): 각 seed의 best-ckpt(기존 사전등록 스코어)로 d1 물질화 스폰(수확 전용 지터 rng **78,000+셀**) × reset seed **700–749** × 셀당 200판 롤아웃. **성공 에피소드**(arrival_capture ∧ clean 발사)에서 발사 스텝 F 기준 **t = F−k (k ∈ {2,4,8}, 존재하는 k만)**의 전체 상태(리미터 p/v·공격자 p/v) + 이후 실행 액션 시퀀스를 스냅샷. 상태 근접 dedup(리미터 위치 L2 < 0.05m 병합) 후 **per-k 목표 12·최소 8**(기존 수치 재사용); k별 미달 = 해당 k 결측 기록(전 k 결측 → §7 중단).
- **RT-PFC**(recorded-trajectory PFC — 신규 측정기, 수식 동결): a = clip(a_rec(t) + K_p(p_rec(t)−p) + K_d(v_rec(t)−v), ‖a‖≤30), 참조 = 수확 에피소드의 기록 궤적(명목), 게인 = **동일 무차원 (c_p, c_d) = (1.0, 0.5), T_k = kΔt**. Gate A 좌석을 PFC 대신 RT-PFC가 승계(특권 = 기록 궤적·시간 인덱스). Gate B 8멤버·zero·random·demo 불변.
- **rewind-v2 파이프라인(생성→검증, bank v2와 동형)**: 생성 screen = paired(RT-PFC/zero) 20판, seeds **750–769**(신규), PASS = 16/4/4 동일 → **독립 validation = 4조건 n=100, seeds 800–899**(신규), σ-물질화(지터 rng **79,000+1,000k+v**), 판정식·부트스트랩(777)·배정식 전부 19 v0.3 §6 그대로. 셀 = (원천 witness 가족, k). **d2급(k=2) admissible ≥1 = on-manifold 가설 채택** → d2 사다리 복원·다음 사이클(단 §7 시한 내). admissible 0 = 가설 기각 → B(증거 행 추가).

## 6. [E-5] seed·rng 대장 증보 (전 대역 서로소, 테스트 락)

- episode_reset: **700–749 수확 / 750–769 rewind screen / 800–899 rewind validation [전부 신규]**; 12.0M dev-v2d1 / 13.0M sealed-v2d1(예약분 승계).
- jitter_rng: 75k(dev-v2d1)·95k(sealed-v2d1)·**78k대(수확 물질화)·79k대(rewind validation) [신규]**.
- 불변 재사용: 게인 (1.0,0.5)·부트스트랩 777·train_seed 0–2·arm rng 90k+7·reset_seed.

## 7. [E-6] 중단·전환 규칙 (전부 사전 고정)

- ① P1′ FAIL → **즉시 B**(docs/20 §3) ② 수확 결측 전 k → B ③ rewind validation k=2 admissible 0 → B ④ **하드 스톱 2026-08-31**: 그 시점의 도달 단계가 어디든 중단·B 확정. 각 중단은 docs/12 §6 증거 행으로 기록(실패 = 벽 논문 evidence).

## 8. 검토·비준 절차

[E-1]~[E-6] 비준(수정 지정 가능) + [R-3] 3자 검토 1회 여부 결정. 비준 후: 구현(번들 d1-사영 + exit 기계 + 수확/RT-PFC/rewind 파이프라인 + 테스트) → 동결 커밋 → P1′ 실행(서버). 3자 전달 시 본 문서 + 09 (iii) + validation json이 패키지.
