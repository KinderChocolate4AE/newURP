# 72 — KSAS 2026 추계 2페이지 논문: 목차 확정 + 결정 기록

**2026-08-08 · `docs/KSAS2026_추계_골격_v0.docx` 승계. 이 문서가 목차·결정의
정본이며, 골격 v0 은 초안 이력으로만 보존한다.**

제목(가안): 공중발사 네트 요격의 성립 경계 — 전개 지연과 겨냥 각속도,
그리고 협력 조향 필요 영역

---

## 0. 확정된 결정 3건

| # | 결정 | 근거 |
|---|---|---|
| ① 수치 계보 | **legacy/A2 계보로 통일.** 곡선 = hand-tuned baseline n=2,700 (A2 scripted attacker). 본문·캡션에 계보 명시 | 경계식 (1)(2) 는 기하·운동학이라 위협 계약 무관 → 손실 없음. 추가 계산 0 |
| ② 학습 슬롯 | **B안 기본값.** 학습 결과는 수치로 넣지 않고 "회수해야 할 목표를 정의한다" 서술로만 | LL v3 = 0/300 (1 시드·1 운용점), LS 미완. `docs/65 §4` learnability 규율 |
| ③ Fig 1 | **삭제.** `w<ρ / w>ρ` 2-케이스 도식은 식 (1) 과 정보량 동일 | 2페이지 예산. 轉(둘째 경계)이 아니라 承(첫째 경계)에 지면을 쓰는 배치가 됨 |

---

## ★★ 외부 리뷰 반영 (2026-08-13) — 결정 ①·② 갱신

하네스 `gpt_crossval_harness_v3_ksas_scope.md` 로 받은 외부 편집 판정. **채택.**

**핵심 판정: 2페이지는 좁게, arXiv v0 는 한 단계 넓게.**

1. **결정 ① 계보 → 반응형 재실행으로 교체 (선택지 b)**. 근거: 구성적 하계는
   **측정한 공격자 계열에 대해서만 유효**한데 A2 는 `route_gain=0` = limiter 에
   반응하지 않는다. 비용 실측 **67분/2,700판** (1.49 s/ep) 이라 알고 있는 최대
   약점을 제거하지 않을 이유가 없다. 변경은 **공격자 반응 항만** (route_gain 0.5,
   sense_range 30.0 = 등록 v3 nominal); 제어기·스윕·측정은 계보 1 그대로.
   `curve_sweep.py` 에 두 인자 추가 (기본값 0.0/inf = legacy bit-exact 보존).
   - **재실행 결과는 그대로 받는다**: 3-구간이 흐려지면 claim 하향, 0.83 이
     크게 떨어지면 "성립" 대신 "tested reactive threat 하 baseline-achievable",
     23.8↔25.8 일치가 사라지면 **겨냥 병목 headline 도 버린다.**
   - rerun 의 올바른 이유는 "나빠져도 협력 논거가 강해진다"(절반만 참)가 아니라
     **"어느 방향으로 나오든 threat-model validity 를 크게 높인다"** 이다.
2. **결정 ② 유지 + 강화**: 학습 결과 불탑재. 추가로 **"쏘는 순간엔 이미 늦다"
   (Phase III 종말 봉쇄 결과) 도 본문 핵심에서 제외** — 2페이지에 새 개념
   (adversarial witness / 상하계 certificate / 사전등록 격자) 을 들여오면 산만하고
   "협력 전체의 negative result 인가" 라는 불필요한 논쟁을 연다.
   **Discussion 마지막 한 문장 예고만**: *"A subsequent certificate analysis
   further indicates that limiter repositioning initiated only after firing commit
   is generally too late within the 0.30-s deployment window, motivating pre-commit
   shaping as the relevant cooperative mechanism."* 수치(69–98%, 600 states,
   ΔU=0) 는 넣지 않는다.
3. **3-구간 명칭 변경** (첫 구간을 "성립"이라 부르지 않는다):
   `baseline-achievable` / `aiming-limited` / `kinematically infeasible`.
4. **겨냥 병목 표현 하향**: "두 독립 계측이 7.5% 로 일치해 **검증**" → **"consistent
   with"**. 이유: 두 값이 같은 캠페인·같은 위협/제어기에서 나왔고, 4.3° 는 분포가
   아니라 중앙값 대표값이며, 식이 1차 근사다. headline 은 숫자 일치가 아니라
   **"실용 성립 경계가 운동학적 χ=1 앞에서 먼저 나타난다 — 유한 slew 가 먼저
   구속하기 때문"** 으로.
5. **★ τ 정의 모순 수정 (필수)**: 현재 "사출 명령부터 포획 유효까지" 라 해놓고
   **명령 이전** 항인 탐지 갱신 0.10 · 결정 루프 0.05 를 더하고 있다. 시간축
   정의상 모순. 채택할 정의 = **"조준이 근거한 관측 시점부터 포획 유효까지"**
   (aim 이 참조하는 정보의 나이 + 물리 전개 시간) — 세 항이 직렬로 이어지고,
   모형이 τ 를 "현재 참상태에서 τ 뒤 포획" 으로 lump 하는 것과도 정합한다.
   병렬 가능성 여부도 한 줄 언급 (직렬 가정이 하한 논거의 전제).
6. **novelty 문장 하향**: "문헌이 없다" → *"To our knowledge, deployment latency
   has not been explicitly formulated as a capture-feasibility condition in the
   net-interception literature considered here."* 핵심 novelty 는 부재 주장이
   아니라 **latency 를 χ 라는 명시적 성립 좌표로 만든 것**에 둔다.
7. **arXiv v0 spine = (ii) 확장형**: 성립 경계 **+ 종말 개입 불가능성** →
   *"where capture is feasible, and why cooperation must act before firing commit"*.
   이후 확장 = T_lead → 실제 shaping 가능성 → MARL.

---

## ★ 위협 범위 = T1 까지 (adversary ladder = `docs/80`, 2026-08-13 봉인)

재실행 공격자의 정확한 범주 = **T1 reactive-local** — "reactive, but not strategic":
방어자 위치를 보고 궤적은 바꾸지만 **lateral avoidance reflex 하나뿐**인
limited-basis adversary. 없는 것: 속도 변조(sprint/slowdown 은 asset 거리 트리거지
방어자 압력 무관) · 경로 재계획 · 체류/후퇴 · net-capturer 와 limiter 구분 · 예측 ·
압력 비례 이득. (closed-loop 항 3개 중 lam repel 은 0.75 m 접촉반사, commit dodge 는
커밋 이후라 전략적으로는 route_gain 하나.)

- **KSAS 범위 = T1 까지.** T2 를 넣으면 2페이지가 attacker design paper 가 된다.
- **표현**: "성립" 금지, "반응형 위협 일반" 금지 → **"tested local reactive threat
  family"**. 재실행은 "안 보는 표적으로 하계를 주장한다" 는 비판만 제거하며,
  **간극을 좁힐 뿐 닫지 않는다** (속도 변조·예측 공격자는 더 잘 피한다).
- **★ null 해석 함정**: 결과가 legacy 와 비슷해도 "reactivity does not matter" 금지.
  최대 허용 = *"the tested angular-gap reactive mode did not materially shift the
  observed boundary under this configuration."* 근거: 30판 예비에서 궤적은
  갈라졌는데(19→41 스텝) 레이블은 동일했다.
- T2(richer reactive)는 **arXiv v0 robustness** 로 이관 (docs/80 §5). 확인 2항목:
  성립/겨냥 경계 유지 여부 · 종말-창 결론(①-B1) 유지 여부.

## ★ A안 전환 조건 (반드시 지킬 것)

학습 결과를 **수치로** 탑재하려면 (슬롯 A) 아래가 **선행 필수**다.

```
포획 확률 곡선을 v3 위협 계약으로 재렌더해야 한다.
  - 현 곡선 = legacy/A2 계보 (n=2,700, hold 배치, hand-tuned)
  - 학습     = v3 계보 (dist hash efeffcbf, contract e275ca1)
  - 규율     = legacy/v2/v3 수치 혼합 금지 (HANDOFF_2026-08-07b §6)

비용: scripted 2,700 rollout 재실행 (랩 서버 — long-run policy).
      MARL 실행과 별도 예산.
```

**즉 "학습 수치 한 줄 추가" 는 한 줄이 아니라 곡선 전체 재생산이다.**
곡선을 v3 로 못 바꾸면 A안은 불가 — B안 유지가 유일한 정합 경로.

부수 조건 (A안 시): headline = IID 10000..10299 (n=300) paired, `docs/63 r2`
동결 comparator (scripted bearing-aware c5). 그 외 데이터셋 인용 금지.

---

## 1. 기승전결 목차 (확정)

축: *"τ 를 넣으면 경계가 생긴다"* (예상 가능) 가 아니라
**"경계가 둘이고, 먼저 무너지는 쪽은 도달이 아니라 겨냥이다"** (비직관).

| | 절 | 내용 | 분량 |
|---|---|---|---|
| **起** | §1 서론 | (P1) 비파괴 last-mile 요격 수요 · (P2) 선행 4편이 공통으로 네트를 상시 전개 강체(τ=0)로 이상화 + 최근접 연구 차별 4축 1문장 · (P3) 기여 3항 | 3문단 / 0.35p |
| **承** | §2.1 지연 분해와 앵커 | τ = 0.15 + 0.10 + 0.05 = 0.30 s, 제외 항이 전부 키우는 방향 → **하한**. 전개 지연 보고 문헌 0건 → 신규 모델링 기여. Table 1. 못 박기: *경계가 τ²에 걸려 비행시간만 계상하면 협력 필요 영역이 통째로 사라진다* | 2문단 + Table 1 / 0.3p |
| **轉** | §2.2 두 경계 | 식 (1) 도달 경계 → a\*=39.3, 경계 위 네트 포획 0/1,635. **반전**: 겨냥은 공짜가 아니라 ω_max 에 묶인 rate-limited 행동 → 식 (2), 잔여 조준각 실측 중앙값 4.3° → 예측 **25.8** vs 독립 계측인 곡선 붕괴점 **23.8**, 편차 7.5 %. **끝에 §2.3 예고 한 줄** | 3문단 + 식 (1)(2) / 0.45p |
| **結** | §2.3 지도와 협력의 방향 | 3-구간 (EASY 0.83 / BAND_AIM 네트 1.0 % vs 물리요격 15.5 % / SHAPING 0) → *"비파괴 요격이 요구되는 구간에서 규칙 기반 기준선은 파괴적 경로로만 도달한다"*. 이어서 협력의 두 채널 상충: (i) 도달집합 차단(유리) vs (ii) 표적 횡속도 유발 → 아군 조준 파괴 (v⊥ 0.4→7.3 m/s, 겨냥 구속 44.8 %) ⇒ 학습 문제 정의 = **"겨눌 수 있는 상태로 몰기"**. 스코프 1문장 (곡선은 문제 정의이지 시스템 성능 아님) | Fig 1 + 2문단 / 0.5p |
| | §3 결론 | 두 경계가 실위협 브래킷 [11, 78] 을 **관통** → 3-구간 지도 = 비파괴 방어체계 설계 지침. 향후 = 협력 조향의 회수율, 실기 스펙 투입 | 3–4문장 / 0.15p |

**논문 전체를 지탱하는 문장** (§2.3):

> 협력 조향은 공격자의 도달집합을 깎아 유리하게 작용하는 동시에,
> 표적에 횡속도를 유발해 아군의 조준을 파괴한다.

협력을 "필요하다"가 아니라 **"방향을 잘못 잡으면 경계를 왼쪽으로 미는
비자명한 제약"** 으로 세우는 자리. §2.2 끝에 예고를 심고 §2.3 에서 회수.

---

## 2. 그림·표 예산

```
Table 1   Engagement parameters anchored to external measurements (6행)
          + 각주: rho = worst-direction effective net radius
Fig. 1    포획 확률 곡선 (구 Fig 2) — 영문·흑백 재렌더
          경계 2 수직선 · 관측 붕괴점 · Wilson 95 % 띠 · 실기 등급 라벨 · 2계열
          캡션에 계보 명시: rule-based baselines, A2 scripted attacker, n = 2,700
삭제      구 Fig 1 (w vs rho 2-케이스 도식) — 결정 ③
```

## 2.1 용어 규약 (본문에서 내부 용어 금지)

| 내부 용어 | 논문 표기 |
|---|---|
| 손튜닝 / hand-tuned | **규칙 기반 기준선** / rule-based baseline (첫 등장 시 "비학습 제어기" 병기) |
| 판 / 롤아웃 / 에피소드 | **모의 n 회** / 시행 |
| 스택 / 배치(hold·intercept) | **모의 환경** / 기준선 구성 |
| 곡선이 무너진다 | 포획 확률이 50 % 를 하회하기 시작한다 |
| BAND_AIM · SHAPING_NEEDED · EASY | 본문에서는 수치 구간으로 서술 (라벨은 Fig 축 라벨로만) |
| 【P1】·★ 등 초안 기호 | 전량 삭제 (초안 스캐폴딩) |

지면이 남으면 그때 구 Fig 1 을 재검토. 먼저 빼고 시작한다.

---

## 3. 미확정 체크리스트 (골격 v0 승계)

- [ ] 저자 구성·순서 (교수님 상의)
- [ ] 사사 문구·과제 표기
- [ ] 참고문헌 3) Rothe et al. 전체 저자 기재
- [ ] 참고문헌 4) Gavin & Bronz 서지·저자명 확정
- [ ] 참고문헌 5) 국내 대드론/무인기 방어 문헌 1건 (5개 이내 규정)
- [ ] Fig 1 영문·흑백 재렌더
- [ ] 식 (1)(2) Word 수식 개체 전환 여부
- [ ] Key Words 2줄 이내 확인
- [ ] 웹 제출 초록 400자 (4문장: 공백 / τ 분해·두 경계 / 독립 검증 25.8 vs 23.8 / 3-구간 지도)
- [ ] KSAS 추계 공식 마감일 확인 (`docs/22` 기준 "공지 대기", 골격은 8/29 가정)
