# 63 — scripted baseline (bearing-aware 재배치) 사전 동결 r0 — 비준 대기

**2026-08-08 · docs/61 §6 (리뷰 5 수정 3) 가 예약한 문서. headline comparator
= strongest nonlearned baseline 의 설계를 **MARL/tuning 결과를 보기 전에**
동결한다 ("결과를 본 뒤 만든 baseline" 방지). docs/69 TRAIN FINAL FREEZE
(hash efeffcbf) 후 작성 — 리뷰 7 순서 규율 (P95′ 결과를 본 뒤 rule family
를 유리하게 바꾸는 것 금지) 준수: 본 설계는 P95′ 진단 수치를 사용하지
않는다. r0 = 초안 (Hyunjun 비준 + 리뷰 8 대상). 비준 전 구현·튜닝 금지.**

---

## 0. 지위와 비교 구조

- headline (docs/61 §6, lexicographic): Δ_net = p_net^MARL − p_net^scripted
  의 paired bootstrap 95% CI lower > 0 이 1차. hold 와도 무조건 비교·공개.
- 본 문서가 동결하는 것 = **F1~F9** (관측·rule family·튜닝 예산·선택 기준·
  접근 규칙). 튜닝 **실행**·최종 파라미터 선택은 비준 후, MARL 결과 전.
- 원칙: scripted 는 MARL 과 **같은 world contract** (ratified F-계약 +
  TRAIN 분포 hash efeffcbf) 위에서 돌고, A4c manifest parity 로 "controller
  만 다르고 world 동일" 을 인증한다 (docs/65).

## 1. F1 — runtime 관측 (controller 가 매 스텝 쓸 수 있는 것)

**MARL 정책 관측의 부분집합만** 허용 (privileged 금지, F9):

```
자산 위치 (원점, 상수) · 자기(limiter) 위치·속도 · 공격자 위치·속도
· threat_obs 2축 (a_att, att_speed — MARL 도 받는 관측)
· 아군 limiter 위치 (관측 벡터에 포함된 편대 상태)
```

**금지 (F9)**: `v_shot`/도달가능집합/fire gate 내부량 · 위협 은닉 파라미터
(route_gain·sense_range·sprint/slowdown 설정) · 미래 상태. bearing 은
에피소드 시작 시 기지 (docs/61 §4 스코프 — MARL 과 동일 가정).

## 2. F2/F3 — rule family (구조를 이것으로 제한)

**bearing-aware arc redeployment** — 기존 프리미티브 재사용 (신규 유도
법칙 발명 금지, docs/48 §3.1 한 곳 원칙):

1. **slot 계산**: 공격자 현재 bearing φ_att(t) (자산 기준 수평각) 중심으로
   4 limiter 를 반경 R_d 호(arc)에 등간격 Δφ 로 배치:
   `slot_i = 자산 + R_d·(cos, sin)(φ_att + (i − 1.5)·Δφ)`, z = 0.
2. **slot 추종**: 기존 PD (`scripted.limiter_kp/kd` 선언값 8.0/4.0 재사용,
   재튜닝 금지) 로 slot 호밍, `a_lim_max` 클립 (능력 계약 그대로).
3. **갱신 규칙**: slot 은 매 스텝 φ_att(t) 로 재계산 (reactive) — 예측
   lead 없음 (lead 모델은 family 밖. 확장은 새 사전등록).
4. **commit 비트 = 0 고정** (`_zero_commit` 규약). 파괴적 커밋은 baseline
   의 몫이 아니다 — headline 이 nondestructive p_net 이고, 커밋 사용
   기저선은 이미 별도 존재 (intercept+commit 참조선, docs/47).
5. finisher = 기존 scripted `clean` 발사 (변경 없음). 역할 분리 없음.

family 밖 (금지): 궤적 예측·CPA 계산 · v_shot 소비 · 위협 draw 의존 분기 ·
스텝별 규칙 전환 · z-축 배치 (수평 arc 한정 — 스코프 docs/61 §4 동형).

## 3. F4/F5 — hyperparameter 와 튜닝 예산 (전부 여기서 고정)

| 축 | 값 후보 (grid 전체 사전 선언) |
|---|---|
| R_d (배치 반경, m) | {6, 9, 12} — NK 반경 6 이상, standby 대역 [8,16] 부근 |
| Δφ (slot 간격, rad) | {π/12, π/8, π/6} |
| (그 외 없음) | kp/kd·a_max·finisher 는 선언값 고정 — 자유도 2축뿐 |

- **튜닝 예산 (F5)**: 3×3 = 9 조합 × TRAIN n=100 에피소드 × 1 seed
  (paired CRN — 같은 에피소드 집합). 총 900 롤아웃. 재시도·확장 없음.
- 튜닝 에피소드 대역: `train` layer, episode 5000..5099 (**학습 대역
  0..N·early-stop 검증 대역과 분리** — 대역 선언 자체가 F5 의 일부).

## 4. F6/F7 — 데이터·선택 기준

- **F6**: 튜닝은 TRAIN layer 만. **IID/OOD 는 설계·튜닝·선택 어디에도
  절대 사용 금지** (docs/61 §6). offline 튜닝 지표는 TRAIN 롤아웃의 라벨
  집계만 (F9 분리: offline metric ≠ runtime 관측).
- **F7 (selection criterion, 사전 고정)**: 9 조합 중
  `p_net (NET_CAPTURE + CAPTURE_WITH_CONTACT 비율)` 최대.
  tie-break (순서 고정): ① total defense (1 − penetration) ② 낮은
  limiter 소모 ③ 작은 R_d. headline endpoint 와 정렬된 기준 하나만 쓴다.

## 5. F8 — 최종 동결

선택된 (R_d, Δφ) 와 튜닝 결과 전체(9 조합 표)를 결과 문서로 공개하고,
구현 커밋 hash 를 이 문서 r2 에 기입해 동결한다. **MARL 결과가 나온 뒤
baseline 의 어떤 요소도 변경 금지** (docs/62 §2 소급 규율 동형). scripted
runner 는 A4c manifest parity 를 통과해야 한다 (world contract 동일 인증).

## 6. 비준표 (r0 — Hyunjun 대기, 리뷰 8 병행 가능)

```
[ ] F1 관측 집합 (MARL 관측 부분집합 + F9 oracle 금지)
[ ] F2/F3 rule family (reactive arc + 선언 PD + commit 0 + family 밖 금지 목록)
[ ] F4 grid (R_d {6,9,12} × Δφ {π/12,π/8,π/6}) — 자유도 2축
[ ] F5 예산 (9 조합 × 100 ep × 1 seed, 대역 5000..5099, 확장 금지)
[ ] F6 TRAIN only (IID/OOD 절대 금지)
[ ] F7 선택 기준 (p_net 최대 + tie-break 순서)
[ ] F8 동결 절차 (r2 기입 + A4c parity + MARL 후 변경 금지)
```

*비고: R_d·Δφ 후보값은 외부 앵커 없는 설계 선언값이다 (NK 반경·standby
대역이라는 기하 제약에서만 유도). 결과를 보고 grid 를 넓히는 것은 소급
튜닝이므로 금지 — 9 조합이 전부 나쁘면 그 사실을 그대로 보고한다.*
