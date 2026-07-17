# 19 — A-3d Phase 0-e 사전등록 패키지 (v0.1, 2026-07-17 — 3자 검토 → 비준 시 0-e 동결 커밋)

> **성격**: docs/18(RATIFIED) §8 순서 1~3의 동결 내용을 **bank v2 생성 전에** 일괄 고정하는 사전등록 문서. 여기 적힌 수치·규칙·seed는 생성/검증/학습 결과를 보고 변경하지 않는다(재생성 1회 원칙·하드 스톱·트립와이어 8/31 불변). 근거 실행 기록 = docs/09 (yy)~(ddd), 전부 커밋·재현 가능. 3자 검토 1회 후 Hyunjun 비준으로 동결(이 문서가 곧 0-e 커밋의 본문).
>
> 검토자 참고 — docs/18 이후 실행된 것(전부 18 사양 내부): 측정기 구현(+17 테스트, env trace 대조 PASS) → 게인 스캔·동결 → dev 12셀 PFC 재평가 → v16 재리파인 ACCEPT(사전 고정 기준 (aaa)) → witness·coverage 동결 → 생성기 구현(+7 테스트, 스모크 12/12). 신규 결정은 본 문서의 [D-*] 표기 항목뿐이다.

## 1. 측정기 (동결)

- **Gate A = PFC**: a_i(t) = clip(a_demo,i(t) + K_p(p_ref,i−p_i) + K_d(v_ref,i−v_i), ‖a‖≤30); K_p = c_p/T_k², K_d = c_d/T_k, T_k = kΔt; 참조 = bank 엔트리 **명목** 스폰의 데모 적분(코드 = `shepherd/train/pfc.py`, (yy) 테스트 락). **(c_p, c_d) = (1.0, 0.5)** — tune 번들(서로소 seed) 1080판, 사전등록 argmax 규칙, 표면 평탄 .433–.492((zz), `results/a3d_gain_scan.json`). 특권 계측기이며 학습 경로 접속 금지.
- **Gate B family [D-1: 멤버 확정]**: ① brake = −30·unit(v_i) ② λ-brake a=−λv_i, **λ ∈ {2, 5, 10, 20}** ③ attpd(공격자-상대 리드 타깃 PD, obs-전용), **(k_p, k_d, d_lead) ∈ {(2,3,1.0), (4,4,1.0), (8,6,1.0)}** — 총 8 멤버, 이후 추가·변경 금지. 전 셀 기록 의무; **obs-hard 경고 문턱 = PFC − GateB_best > 0.4**(지위 = 비준 (ii): 경고 셀은 학습 bank 유지·confirmatory 클레임 제외).
- 개방루프 demo = 진단 열 병기(리그 연속성). teacher/판정 경로 = frozen 불변.
- **σ 평가 grid(0d-5)**: 학습 램프 불변(d0 0/…/d4 .02). 최종 평가 = 전 스테이지 × **{배정σ, 공통 0.005}**(필수) [+ {0, 0.02} 여유 시], 적용 = 전 arm + learned policy. 진단 전용 — 결과로 σ·admissibility 사후 선택 금지. d4 = robust-마진 계측지 유지.

## 2. witness set·coverage (동결 — (ccc) 재수록)

- witness = {**v16: transplant**(val 1.00 독립 재계산, `results/a3_robust_bank_v2.json`; v1 보존), **v20: x16v20**, **v24: x20v24**}.
- coverage 목표: **v16 → d1·d2 / v20 → d1·d2(d2 = 저신뢰 표기) / v24 → d2·d3·d4**; d1/v24 = C 구조 제외(R≡0 선점, 18 §1). 목표 미달 셀 = 규칙 제외만(문턱·생성식 조정 금지).

## 3. 생성식 (동결 — 코드 = `shepherd/scripts/a3d_sbe_bank_v2.py`, (ddd) 테스트 락)

- 합성 = bank v1 폐형식 그대로(감속-도착·콘 ±15°·|a|≤24·구성 게이트 4종; v1 코드 기본값 바이트-보존 확인). draw rng = default_rng(47000 + 1000k + v + 100000·cand).
- **draw-level paired screen**(수록 관문): seed **400–419**(20), PASS = p̂_PFC ≥ 16/20 ∧ p̂_zero ≤ 4/20 ∧ reset_clean ≤ 4/20(비-clean 면도날의 운용형). 지위 = 스크리닝(인증 아님 — 인증은 §4 validation).
- **시도 상한 48/셀·목표 12·최소 수록 8**(8/12 = 운영 기준, 일반화 근거 아님). 셀별 분포 보고 의무(시도/수락/드랍 사유/수락 v0 통계/데모 다양성) + **zero 포획-len 히스토그램**(d4 en-route 판별).
- **v0 후보 grid = {U[0.3,0.8](v1), U[0.5,0.8], U[0.15,0.5]}, [D-2] 선택 규칙 = first-fit 확정**(후보 0 = v1 분포 = "v1 최근접" tie-break의 try-순서 실현; argmax 모드 폐기 — 근거: 선택 자유도 최소화, 최종 판정은 §4 독립 validation이 담당하므로 목적함수 최적화 불요).
- 실행: **1회**. 셀-병렬 허용(셀별 독립 rng = 결정론 유지). 산출 = `results/a3d_sbe_bank_v2.json`(생성기 meta에 본 문서 참조 기록).

## 4. admissibility 판정 (동결)

- **독립 validation [D-3]**: 생성된 각 셀에서 **n=100판/arm**, reset seed **600–699**(신규 예약, 전 대역 서로소), arms = zero/random/brake/demo-open/**PFC**/Gate B 8종. 판정 = **LCB95(paired Δ = PFC − zero) > ε = 0.4**(동일-seed 짝지음; LCB = 에피소드 부트스트랩 10,000회, rng 777). 미달 셀 = C 제외. **이 시점 이후 생성식·문턱 재조정 금지**(리뷰 금지 문구 준수).
- point 문턱 .8/.2는 screen 전용으로만 서술(n=20/100의 CP 한계 문서화 = 18 §6).
- 추론 단위: admissibility = episode / 학습 판정 = training seed(혼합 금지).

## 5. V-5′·exit·δ_min (동결) [D-4]

- **V-5′(학습 성공 판정)**: 동일 게이팅 번들·동일 ep **paired contrast arr(π) − arr(zero)**, 주검정 = **exact McNemar 단측** + Δ CI(부트스트랩 10k·rng 777), **δ_min = 0.10**(실질성 문턱 — 근거: draw-필터가 zero 바닥을 ≤.2로 누른 상태라 실질 증분 여유 존재; 0.05는 "유의하나 무의미" 표면). 무행동 컨트롤 = 상설 무결성 게이트. competence 리그(zero/brake/demo/PFC/GateB) 분리 보고, 추론 단위 = training seed, 2-tier 클레임(mechanistic vs method) 유지.
- **스테이지 exit 유도식**: exit_d = **UCB95(zero_d; §4 validation n=100) + δ_min** — zero는 정책-무관 상수이므로 학습 중 재실행 불요. 유도된 수치는 validation 직후 **본 문서 부록 A로 추가 커밋**(공식은 지금 동결, 숫자는 기계 대입 — 결과 보고 조정 아님).
- 8항 사전 체크리스트(Feasibility/…/Integrity) = 각 스테이지 학습 착수 전 필수(18 §0 ⓖ). 하드 스톱: 수정 bank·k≤2에서 LCB(Δ_{π−zero})≤0 ∧ brake 하위 지속 → 튜닝 반복 금지·프레이밍 전환.

## 6. 번들 계획 (동결) [D-5]

- **sealed-v1·dev-v1 = 구조 변경으로 폐기 기록**(bank v1 스폰 물질화본 — 파일 보존·삭제 금지, 이후 어떤 판정에도 미사용).
- bank v2 동결 후: **dev-v2 = {rng 75000, seed 12,000,000} / sealed-v2 = {rng 95000, seed 13,000,000}**(균형 30×witness×스테이지, 물질화, 서로소). sealed-v2 = 생성 즉시 **md5 해시를 로그에 기록**, Phase 2 확증 전 롤 금지(러너 거부 유지).
- tune 번들(8.0M) = 게인 선정 전용 소임 종료(admissibility·exit에 미사용).

## 7. seed 대장 (전 가족)

| 대역 | 용도 |
|---|---|
| 0–9 | 학습 seed(torch) |
| 7–16 | bank 구성 robust 게이트(fresh union) |
| 23 / 23000+k / 47000대 / 71k·75k·81k·93k·95k / 90000+7ep / 777 | rng 스트림(probe·refine draw·생성기 draw·번들·random arm·부트스트랩) |
| 61–65 / 71–75 | Φ Z_train / audit |
| 100–104 / 200–209 | witness 탐색 / robust 검증 union |
| 300–319 | (aaa) 재리파인 screen |
| 400–419 | 생성기 screen |
| **600–699** | **admissibility validation [신규]** |
| 500,000 / 1.5M / 2.5M | eval_seed0 가족(게이팅·판정 번들) |
| 7.0M / 8.0M / 9.0M | dev-v1 / tune / sealed-v1 번들 |
| **12.0M / 13.0M** | **dev-v2 / sealed-v2 [신규]** |
| 31M | a3b fire-oracle |

## 8. 검토 요청 (3자)

각 [D-1]~[D-5]에 ① 승인/수정 ② 근거 1–2문장. 추가로 ③ 본 패키지가 docs/18 비준 사양과 충돌하는 곳 ④ 우리가 사전등록에서 빠뜨린 자유도. 비준 시 본 문서가 0-e 동결 커밋이 되며, 이후 bank v2 1회 생성 → §4 validation → 부록 A(수치 대입) → P1.
