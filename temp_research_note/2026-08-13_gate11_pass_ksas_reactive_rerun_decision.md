# 2026-08-13 — 게이트 11 PASS (전체 시스템 상사성 복원) · KSAS 2p 계보 결정: 반응형 재실행 (진행 중)

세션 daily log. 오늘 마무리된 것 2건 + 착수한 것 1건. (Notion 중단 중 대체 기록,
판정형 제목 관례.) 개별 판정 노트가 이미 있는 항목(F-0a/0b, 게이트 7 r2, 게이트 10
Tier1/Tier2 r3·r4, Π 분류)은 여기서 한 줄로만 참조한다.

---

## 1. 게이트 11 — **PASS**. k_f·τ 가 유일한 숨은 시간상수였다

게이트 10 Tier 1 이 남긴 유일한 미해결(**T1-T.system FAIL**, 원인 = 동결 scripted
attacker 의 하드코딩 전진 P-게인 `a_fwd = 4.0·(v_ref − v_fwd)`)을 수리하고 재검증.

**절차 3단 (docs/77 III-D 순서 그대로, 결과 열람 전 고정):**

| 단계 | 결과 |
|---|---|
| ① baseline regression — 리터럴 4.0 → `attacker_ladder.FWD_GAIN` (기본값 동일) | **bit-exact**: 게이트10 `--tier1` 재실행이 승격 전과 **전 수치 동일** (T1L dev 0.0 / T1T dev 5.50e-01·8.08e-02·4.57e-01·8.68e-01·2.91e-01·1.86e+00, mask_mis 8·10·7·12·15·12) → 물리 불변 확인 |
| ② S-L 회귀 (α=2, β=1) | **6/6 exact PASS** (dev 0.0) |
| ③ **S-T 재falsify** (α=1, β=2, `FWD_GAIN' = FWD_GAIN/β`) | **6/6 exact PASS** — state_dev **0.0** · dv **0.0** · mask·engaged 불일치 **0** |

- 게이트 10 에서 state_dev 최대 1.86 · mask flip 7–15건이던 실패가 **완전히 소멸**.
  시간축에 dt·τ·jink_freq·각속도 4종이 동시에 얽힌 계에서 exact 0.0 이 나온 것은
  무차원화 정렬이 맞다는 강한 신호. **추가 hidden constant 없음.**
- **승격 방식 안전성**: `AttackerSpec` 필드가 아니라 **모듈 상수**로 올렸다 —
  v3 분포 해시(`v3_distribution_hash`)는 명시 상수 payload 만 담으므로 동결 계약
  무영향. 확인 후 진행.
- **게이트 10 의 T1-T.system FAIL 은 보존**한다 (수리 기록이지 은폐 아님).
  정본 표기: *"full-system T1-T failed (hidden k_f·τ); after explicit
  parameterization, S-T passed exactly."*
- ⇒ **상사성 Level 2 (registered scripted encounter similarity) 확보.**
  Level 3 (learned-policy) 는 범위 밖 유지.
- 산출물: `results/phase3/gate11_system.json` · `gate11_baseline_regression.json` ·
  `shepherd/scripts/gate11_system_similarity.py`. 커밋 `3087615`.

**Phase III [G] 라인 현황**: 게이트 7 ✅(①-B1) → 게이트 10 ✅(종료) → **게이트 11 ✅**
→ 다음 = T_lead/B2 (III-E). 대기 중 별도 사전등록 3건: nu τ-지평선 재시험 ·
T̃_reach 축 sweep · eta 상한 censoring 회피 설계.

---

## 2. KSAS 2p 계보 결정 — 외부 편집 리뷰 수용, **반응형 재실행 (선택지 b)**

하네스 `ANDES/URP/gpt_crossval_harness_v3_ksas_scope.md` (내부 게이트 언어를 전부
자연어로 치환한 자족 프롬프트) 로 받은 외부 판정. **핵심: 2페이지는 좁게, arXiv v0
는 한 단계 넓게.** 채택 7건은 `docs/72` 상단에 정본화. 요지:

1. **계보 = 반응형 재실행**. 근거: 구성적 하계는 **측정한 공격자 계열에만 유효**한데
   A2 는 `route_gain=0` = limiter 무반응. "안 피하는 표적에게서 얻은 0.83" 으로
   성립을 주장할 수 없다. 변경은 **공격자 반응 항만**.
2. 학습 결과 불탑재 유지 **+ 종말 봉쇄 결과(①-B1)도 본문 핵심에서 제외** —
   2페이지에 adversarial witness/상하계 certificate/사전등록 격자를 들이면 산만하고
   "협력 전체의 negative result 인가" 논쟁을 연다. **Discussion 한 문장 예고만**,
   수치(69–98%, 600 states, ΔU=0) 미탑재.
3. 3-구간 개명: `baseline-achievable` / `aiming-limited` / `kinematically infeasible`
   (첫 구간을 "성립"이라 부르지 않는다).
4. 겨냥 병목: "7.5% 일치로 **검증**" → **"consistent with"**. headline 은 숫자
   일치가 아니라 *"실용 경계가 운동학적 χ=1 **앞에서** 먼저 나타난다 — 유한 slew 가
   먼저 구속하기 때문"*.
5. **★ τ 정의 모순 수정 (필수)**: "사출 명령부터 포획 유효까지" 라 해놓고 **명령
   이전** 항(탐지 0.10·결정 0.05)을 더하고 있었다 — 시간축 정의상 모순.
   채택 정의 = **"조준이 근거한 관측 시점부터 포획 유효까지"** (aim 이 참조하는
   정보의 나이 + 물리 전개). 세 항이 직렬로 이어지고, 모형이 τ 를 "현재 참상태에서
   τ 뒤 포획" 으로 lump 하는 구현과도 정합. 직렬 가정이 하한 논거의 전제임을 병기.
6. novelty 하향: "문헌 없음" → *"To our knowledge … in the literature considered
   here."* 핵심 novelty 는 부재 주장이 아니라 **latency 를 χ 라는 명시적 성립
   좌표로 만든 것**.
7. **arXiv v0 spine = 확장형**: 성립 경계 **+ 종말 개입 불가능성** →
   *"where capture is feasible, and why cooperation must act before firing commit."*

**rerun 논리 정정 (리뷰어)**: "숫자가 나빠져도 협력 논거가 강해진다" 는 **절반만
참** (포획률 하락의 원인이 협력 필요/제어기 부실/센싱 기하/겨냥 모형 중 무엇인지는
별개). 올바른 이유 = **"어느 방향으로 나오든 threat-model validity 가 크게
올라간다."** 이 문장을 계획서에 못박음.

---

## 3. 반응형 재실행 — 실행 전 검증 2건 + 본실행 착수 (결과 대기)

`curve_sweep.py` 에 `--route-gain` / `--sense-range` 추가. **기본값 (0.0, inf) =
legacy 비반응형 bit-exact 보존** — 기존 곡선 재현 가능.

**실행 전 확인 (감으로 돌리지 않기):**
- **비용 실측**: 30판 계측 → **1.49 s/ep**, 2,700판 ≈ **67분** (legacy 1.25 s/ep).
- **반응 항 작동 검증 (중요)**: 첫 30판에서 레이블이 legacy 와 **완전히 동일**하게
  나와 no-op 을 의심 → 궤적 직접 대조로 확인: **max |Δp| = 1.50 m, 에피소드 길이
  19 → 41 스텝**. 표본이 작아 결과 레이블만 우연히 일치한 것이고 반응 항은 정상.
  (이 확인 없이 돌렸으면 "재실행했는데 아무것도 안 변했다" 는 가짜 결과를 보고할
  뻔했다 — 기록해 둔다.)

**본실행 (진행 중)**: route_gain 0.5 · sense_range 30.0 (등록 v3 nominal),
제어기·스윕·측정은 계보 1 그대로.
- `--mode hold --episodes 2700` → `results/curve_hold_reactive.json`
- `--mode intercept --episodes 2700` → `results/curve_intercept_reactive.json`

**결과 수용 규칙 (실행 전 고정)**: 그대로 받는다.
3-구간이 흐려지면 claim 하향 / 0.83 이 크게 떨어지면 "성립" 대신 "tested reactive
threat 하 baseline-achievable" / **23.8↔25.8 일치가 사라지면 겨냥 병목 headline 도
버린다**.

**재실행 후 남는 작업**: ψ(잔여 조준각) 재계측 (`slew_audit` 계열) · Fig 1 v3 재렌더
(영문·흑백 + χ 보조축 0.66/1.0) · 국내 문헌 1건 검색 · Gavin & Bronz 서지 확정
(문헌 서치에서 확보: Timothée Gavin·Murat Bronz, ICUAS 2026, arXiv:2607.05939) ·
78 m/s² 출처 표기 · 사사/저자 (교수님 상의) · 초록 자수 재확인 (현 394자/400).

---

## 4. 오늘 커밋

`3087615` 게이트 11 PASS · `276a02f` KSAS 리뷰 반영 + curve_sweep 반응형 인자.
(이전: `0d4ec90` 게이트10 r4 · `4733511` r4 봉인 · `442162f` r3 판정 · `264f57a` Π 분류)
