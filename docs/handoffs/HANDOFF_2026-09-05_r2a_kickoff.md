# HANDOFF 2026-09-05 — R2a 착수 (파라미터 맵 우선 전환)

다음 세션 첫 열람용. 이 세션의 결정·산출물·다음 수를 담는다.

## 0. 방향 결정 (사용자, 이 세션)

**arXiv v0 를 후순위로 내리고 순수 연구 진전 우선.** 근거 = "실험·증거가
빈약하다, 정해두고 수확하지 말고 연구를 진전시키다 수확한다". 우선순위:
① (χ,η) 파라미터 맵 (paper-R2a) ← **지금 여기** ② turn-limited 위협계약 v4
③ Δ_coop 협력 (E4-2/T1-R → self-play, 공사 학술대회행) ④ 폐루프-해석 격차 해부.
docs/87 의 R2a 는 원래 arXiv 사슬과 분리돼 있어 이 전환과 충돌 없음. 협력
실험(B0/B2)만 docs/81 사슬상 arXiv 공개 뒤라 — 착수 시점에 docs/81 개정 필요.

## 1. R2a 설계 브리프 = `docs/review_prompt_r2a_parameterization.txt` (r3)

r1 작성 → 외부 감사 1차 "수정 요구" (최소 수정 9건, 전 수치 적대적 재검증
CONFIRMED) → r2 → 감사 2차 (identifiability 정밀화) → **r3 (현재)**. 핵심:

- **가설 분리**: H-SIM (완전 상사 collapse) / H-DOM (선언 교란에 경계 robust).
- **구현 5종**: R-ref · R-tau-SIM · R-rho-SIM (Tier A) / R-tau-DOM (= 고정
  차원 gain 이 유도한 k_f·τ perturbation, k_f=fwd_gain 4.0 [1/s]
  params.py:272) · R-rho-DOM ({λ,α} target, 스폰·σ co-scale 격리) (Tier B).
- **★ identifiability 제약**: 경계 χ50(η) 가 공통 support 밖이면 H-DOM 은
  non-identifiable (D_χ 계산 불능). legacy bracket 에서 R-tau(τ0.45) 의
  χ_min=0.629 > pooled χ50=0.571 이 발단. 해법 = **τ_B 선택 게이트**:
  {0.45, 0.425, 0.40, 0.375} 중 Stage 0 boundary envelope + 1 grid headroom
  을 포함하는 최대 τ_B 자동 선택, floor τ_B/τ_ref ≥ 1.25. 전부 실패 시만
  D-1 (저가속 pin-확장 별도 캠페인, NON_IDENTIFIABLE 판정).
- **판정**: equivalence 3분법 (paired CI ⊂ ±δ_p) + paired CRN (무차원 공간
  추첨, 차원값 역산) + Stage 1 상관 실측으로 n 재산정 (독립 n=400 은 기대
  PASS 61.5% 뿐). margin 은 Stage 0 에서 경계 기울기로 연동 역산. 전역 =
  D_χ = max_η simultaneous band (censored 행 제외·보고) + R_cell. 84셀 80%
  규칙 폐기 (예산 모순 + 포화 셀 세탁).
- **순서**: Stage 0 (frozen 재집계, exploratory 선언) → τ_B 게이트 →
  lattice 봉인 (hash) → Stage 1 (kill screen + viz-first + pathwise + dt
  수렴 + n 재산정) → Stage 2 (R-ref 84셀) → Stage 3 (경계 밴드 confirmatory)
  → Stage 4 (직교 λ test — R-rho-DOM 실패 시에도 λ 자동 승격 금지).
- registry 예약: C044 / **C045 ∈ {PASS_2D, PARTIAL_3D, FAIL,
  NON_IDENTIFIABLE}** (R2b 하드 의존성) / C046.
- 봉인 전 잔여 결정 = 브리프 §9 (envelope h, pathwise atol, worst-case
  exact rule, **SIM co-scale 하네스 실현성 — dt=τ_B/6, k_f=1.20/τ_B 주입
  가능 여부를 ledger 로 검증**, D-1 문안).

## 2. 다음 세션 첫 작업 (의존 순서)

1. **Stage 0**: `results/curve_hold_reactive.json` (n=2,700, cp949 인코딩
   주의) 재집계 → 행별 χ50(η) (isotonic primary) + envelope B(η) + τ_B
   게이트 예비 판독. 0비용 로컬. **exploratory/design 지위 명시** — 산출물
   hash 는 봉인에 들어간다.
2. `r2a_lattice.py` (~60줄): 격자·pin·**invariant/perturbation ledger**·
   공통 support mask·τ_B 선택 규칙 → RED-first `tests/test_r2a.py`.
3. lattice 봉인 문서 (τ_B 판정문 포함) → Stage 1.
   선행 의무: repo-R1 (provenance pass) + H-4 (랩서버 가용 — **사용자만
   가능**, 미해결).

## 3. 이 세션의 다른 산출물 (전부 커밋됨)

- `7ba0752` results/ 캠페인 계보 라벨 (README 표 + test_results_lineage.py
  가드 3종, mutation 검증). **핵심 정정: v0/T1 세계 = legacy 24 m 회랑
  (선언 regime, docs/87 §4) — "v0 = 300 m scale_v2 세계" 로 읽지 말 것.**
  scale_v2/v3 은 MARL/train branch 세계.
- `4115d74` cone 여유 법칙 단일 정의원화 (convention=inscribed 기본, 동결
  E1e 재현기는 tan 명시) + fig1_ksas/fig2_ksas (동결 수치 assert) + 그림
  4파일 추적. 테스트 31/31.
- `b79153a` docs/85 F-1 tooling debt 기록.
- KSAS 원고 (`그물 발사를...폐루프 성능.pdf`) 수치 전수 대조 **PASS**:
  458/807 은 정밀 경계 31.766 기준 정확 (31.8 반올림 재계산 시 458/808 —
  본문 기호 표기 권장), sin-정정 반영 확인 (6.79/1.43/0.808/31.8), η-tercile
  0.878/0.776/0.636 일치. 경미 지적 2: ① 상계를 기호(a*_geom)로 ② "이상적
  겨냥(예측점 축 위)" 전제 1문장 누락 (08-28 노트 §5 요구분).

## 4. 사용자 트랙 잔여 (마감 순)

- **KSAS 9/11 마감**: registry C042 정정 행 (3계층 32.37→31.77) + **C043
  신설** (η-tercile — 아직 미등록 확인됨) + PUB-01 결정 기록 + freeze tag +
  제출 (docs/87 W1 체크리스트).
- H-4 랩서버 확인 (Stage 1 이후 서버 실행의 전제).
- docs/84 개정 3건 (turn-limited·BMD·η-tercile 승격) 은 arXiv 후순위화로
  자연 보류 — arXiv 재개 시 W3/W4 절차 그대로.
- `figures/draft_fA·fB` = 생성기 없는 고아 초안 (f1/f2_ksas 로 대체) — 삭제
  가능.

## 5. 열 때 주의

- 감사 브리프는 **txt** (사용자 지시 "md 생성 X") — 개정도 txt 로.
- 결과 JSON 인코딩: 기존 산출물 cp949, 신규는 utf-8 명시 (docs/87 §0).
- 30분+ 실험은 랩서버 tmux+ntfy, 로컬 직렬 금지 (memory: long-run-policy).
- 새 regime 첫 결과는 수치 전에 궤적 뷰어부터 (memory: viz-first-policy).

---

## 6. 같은 날 후속 — Stage 0 완료 · r4 (B+C, a_min^P=6) · 봉인 커밋 · Stage 1 착수 승인

- **Stage 0 판독**: transition 은 step (χ<0.49 p≈1 / >0.73 p=0), χ50(η) 0.60→0.54 약한
  감소, pooled isotonic 0.565. slope 연동 δχ 역산 (§6.1) 폐기.
- **r4-C**: δp 0.10 / δχ 0.05 별도 estimand (δχ = R2b regime 분류 보존 변위). map grid
  (0.41…0.85 step 0.04 × η 2.1…3.9) 와 boundary micro-grid (χ50⁽⁰⁾±0.10 step 0.02) 분리.
- **r4-B / B′**: 계약 2종 별도 hash, pooling 금지. R2a-L (a≥11, τ 0.375 directional only) /
  R2a-P (a≥6, τ_B 0.45 confirmatory). a_min^P 는 H_support ≥ max(δχ, 2Δχ_micro)=0.05
  규칙으로 {7,6} 중 기계 선택 (7→0.043 reject, 6→0.057 accept). a∈[6,7] hidden-branch
  감사 통과. ledger 는 주입 차원값에서 무차원군을 계산해 SIM invariant / DOM target 만
  이동을 assert (R-tau-DOM target = {k_f·τ} 비어 있지 않음).
- **봉인 hash**: Stage 0 `3878260e937f9b05` · R2a-L `a854a57a643a17fd` · R2a-P
  `e43036f00679ff77` (`artifacts/r2a/`). 브리프 §10 r4 부록이 설계 기록.
- **다음 순서 (사용자 승인)**: seal → repo-R1 (provenance pass) → H-4 랩서버 (사용자) →
  **Stage 1**. Stage 1 의 첫 실질 gate = **Tier A pathwise** (CRN 고정 정규화 궤적 atol 일치).
  불일치 시 n=400 kill screen 결과를 보지 말고 원인 분류 (하네스 버그 / 숨은 차원상수 /
  IC 스케일링 / 이산화) 부터. viz-first 선행. 하네스 주입 실현성은 ledger `inject`
  목록 (dt, tau_lock, tau_kill, omega_aim, omega_att_slew, k_f, R_max, spawn dx/r_lat/x0,
  kill_radius) 으로 검증 — 주입 불가 항목은 DOM target 으로 재분류하고 봉인 갱신 (새 hash).
- 노트: `temp_research_note/2026-09-05_r2a_stage0_boundary_sharp_tau_gate_hinges_on_chi_step.md`.
