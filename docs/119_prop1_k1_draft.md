# 119 — prop1 K1 초안: 정리문 (무차원 (χ, η) 형) + Lemma 1–2 전체 증명

> **상태: AI 초안 (2026-10-01) — Hyunjun 손증명·비준 전. K1 (≤10/31) 의 완료
> 조건은 본 문서의 검증이 아니라 Hyunjun 의 손증명 확인 + 채택안 결정이다**
> (docs/87 §3A: "정리문 + Lemma 1–2 손증명"). docs/10 v0.1 (M2 상수) 을 승계하되
> 현행 캠페인 무차원 좌표로 올렸다.
>
> **기록 정정**: G3 (R2a collapse 판정, ≤10/30) 는 **2026-09-05 조기 완료**
> (`PARTIAL_3D`, 종결 감사 2회, C044~C046 + G3 registry 등록 9/7). 10월 잔여
> 데드라인은 K1 뿐이다. (2026-10-01d 노트의 "G3·K1 착수" 표기는 K1 한정으로 읽는다.)

## 0. 핵심 번역 — docs/10 의 1D 명제는 (χ, η) 좌표에 그대로 얹힌다

`r2a_lattice.dims_from`: a = χ·2ρ/τ², v = η·ρ/τ. 따라서

- 회피 여유 **w = ½·a·τ² = χ·ρ** — docs/10 의 구조 조건 **A1 (w > ρ) ⇔ χ > 1**.
- 무-shaping plateau **v_soft = ρ/w = 1/χ**.
- shaping-forcing gate 창 **θ_fire ∈ (1/χ, 1]** ⇔ **χ > 1/θ_fire**.
- standoff 조건 x_fire ≥ v̄τ + ρ + ε ⇔ **x_fire/ρ ≥ η + 1 + ε′**.

즉 1D 명제는 "χ 가 1 (정확히는 1/θ_fire) 을 넘는 regime 에서 shaping 없는 방어가
구조적으로 0 이 되는 기전"의 해석적 골격이고, R2a 가 측정한 χ50 경계는 그 3D
대응물이다 (단 §4 캐비앗: 3D 는 λ cone DOF 가 추가 좌표 — PARTIAL_3D).

## 1. 세팅 (docs/10 §1 승계, 무차원 표기)

시간 이산, 1D. 공격자 x_t ∈ ℝ, |v_t| ≤ v̄, |a| ≤ a_max. 원점 도달 = 침투.
finisher K = 1, 발사 비가역, 전개지연 τ. 시각 t 발사 시:

- net 구간 N = [c − ρ, c + ρ], 명목 endpoint c = x_t + v_t·τ (env `net_center`).
- 공격자 endpoint 도달집합 (무-마스킹) R = [c − w, c + w], **w := ½·a_max·τ² = χρ**
  (env `R_lat` 와 동일한 선언 모델 — 속도 포화 |v| ≤ v̄ 가 물리면 R 이 이보다 좁을
  수 있으나, 모델 정의로 고정한다; §4-1).
- 판정 (S5 robust): capture ⇔ 실현가능 endpoint 전부 ∈ N (v_worst = 1).
  soft 대용 v_soft = |R′ ∩ N| / |R′|, R′ = kill-radius 마스킹 후 집합.
- fire gate (FSM 하드): 발사 허용 ⇔ v_soft ≥ θ_fire.
- limiter: kill 반경 r 의 no-go 구간 n 개. u_L⁰ = hold (마스킹 없음).
- miss-is-free: 빗나간 발사는 공격자 무비용, k → k − 1.
- boxed_in (R′ = ∅) 은 clean crossing 아님.

**가정.**
- **A1 (기하)**: χ > 1 (⇔ w > ρ).
- **A2 (게이트)**: θ_fire ∈ (1/χ, 1].
- **A3 (정보·반응)**: 공격자는 commit 을 관측하고, bang-bang ±a_max 로 τ 동안
  R (마스킹 시 R′) 내 임의 endpoint 를 실현할 수 있다.
- **A4 (escort 실현가능)**: shaping 시 limiter 가 상대 위치를 유지할 수 있다
  (또는 corridor 변형 — §4-2).
- **A5**: 공격자 목표 = 침투. 방어 가치 = 침투 저지 확률.

## 2. Lemma 1 (무-shaping plateau) — 전체 증명

**주장.** u_L = u_L⁰ 이면 모든 t, 모든 공격자 정책에 대해 v_soft(t) = 1/χ (상수)
이고 v_worst(t) = 0.

**증명.** 마스킹이 없으므로 R′ = R. N 과 R 은 **같은 중심 c = x_t + v_t·τ** 를
갖는 구간이다 — c 는 공격자의 현재 상태 (x_t, v_t) 만으로 정해지고, N 의 중심은
env 규약상 정확히 그 명목 endpoint, R 의 중심도 등가속 적분의 대칭성으로 같은 c
이다. 동일 중심 구간의 교집합 길이는

|R ∩ N| = 2·min(ρ, w) = 2ρ   (A1: w > ρ),  |R| = 2w,

이므로 v_soft = 2ρ / 2w = ρ/w = 1/χ. 이 값은 t, x_t, v_t 에 전혀 의존하지 않으므로
모든 시각·모든 정책에서 상수다. v_worst = 1 ⇔ R ⊆ N 인데 w > ρ 이면 c + w ∈ R,
c + w ∉ N 이므로 R ⊄ N, 즉 v_worst = 0. ∎

**손증명 체크 포인트 (Hyunjun):** ① "R 의 중심 = c" 가 등가속 적분에서 대칭인
이유 (±a 대칭) ② A1 없이는 min(ρ, w) = w 가 되어 plateau = 1 — 조건의 역할 확인.

## 3. Lemma 2 (보장 회피) — 전체 증명

**주장.** 마스킹 없이 (R′ = R) 어떤 시각의 어떤 발사든, A3 공격자는 확실히
회피한다 (capture 미성립).

**증명.** Lemma 1 에 의해 발사 시점에 R ⊄ N 이고, z := c + w 는 z ∈ R ∖ N 을
만족한다 (w > ρ). A3 에 의해 공격자는 commit 관측 후 bang-bang +a_max 로 endpoint
z 를 실현할 수 있다. 두 판정 의미론 모두에서 miss 다: (i) 실현 의미론 — 실제
endpoint z ∉ N; (ii) S5 robust 의미론 — 발사 순간 v_worst = 0 이므로 판정기가
miss 를 예약한다. ∎

**손증명 체크 포인트:** A3 가 실제로 쓰는 것은 "R 의 끝점 하나를 실현할 수 있다"
뿐이다 — 임의 endpoint 실현가능성 전체가 아니라 약한 형태로도 충분함을 확인
(리뷰어 방어: A3 를 "끝점 실현가능" 으로 약화해도 Lemma 2 는 성립).

## 4. 명제 N (정리문 — K1 확정 대상)

**Proposition (shaping necessity, 1D instance).** A1–A5 하에서:

**(a) 보수 게이트 무-shaping ⇒ 가치 0.** θ_fire > 1/χ 이면 Lemma 1 에 의해
v_soft ≡ 1/χ < θ_fire 로 게이트가 어떤 상태에서도 열리지 않는다. 발사가 없으므로
직진 접근이 공격자 최선반응이고 침투 확률 1, 방어 가치 0.

**(a′) 느슨한 게이트 무-shaping ⇒ 가치 0.** θ_fire ≤ 1/χ 로 발사를 허용해도,
어떤 발사든 Lemma 2 로 확실 miss 다. miss-is-free 에 의해 사후 게임은 재고 k−1
의 동형 게임이므로 k 에 대한 귀납으로 가치 0. **∴ 게이트를 어떻게 놓아도
무-shaping 가치 = 0; 실패는 게이트가 아니라 구조 (χ > 1) 다.**

**(b) 2-limiter lobe-마스킹 ⇒ crossing 강제 + 확실 포획.** r/ρ ≥ (χ − 1)/2 이면
kill 구간 2개를 c ± (ρ + (χ−1)ρ/2) 에 두어 escape lobe L± = c ± (ρ, χρ] 를
마스킹하되 core (c − δ, c + δ), δ = ρ − max(0, r − (χ−1)ρ/2) > 0 을 남길 수 있다.
그러면 R′ ⊆ N, R′ ≠ ∅ 이므로 v_soft = 1 ≥ θ_fire, v_worst = 1: escort 가 유지되는
매 스텝 clean crossing 이 강제되고, 첫 crossing 발사가 **모든** 공격자 정책에
대해 포획이다 (S5 판정이 발사 시점에 동결되므로 A3 반응으로 탈출 불가; 낭비 0).
무차원 standoff x_fire/ρ ≥ η + 1 + ε′ 에서 교전하면 침투 전에 resolve 된다.
접근 거부 시 침투 없음 — 방어 가치 1.

**따름정리 (좌표 번역).** (i) 구조 실패 조건 = χ > 1; B0 v3 의 θ_fire = 0.9 에서
shaping-forcing 창은 χ > 1/0.9 ≈ 1.11. (ii) plateau 1/χ 는 χ 에만 의존하고 η 에
독립 — 1D 골격에서 η 는 (b) 의 standoff/resolve 조건에만 들어간다. (iii) M2 상수
(a=30, τ=0.4, ρ=2) 는 χ = 1.2, plateau = 1/1.2 = 5/6 — docs/10 의 수치를 재현.

## 5. 캐비앗 (docs/10 §4 승계 + 갱신)

1. **R = [c−w, c+w] 는 선언 모델** — 속도 포화가 물리면 보수적이지 않을 수 있다.
   env `R_lat` 규약과의 동일성이 주장의 근거이지 일반 역학 명제가 아니다.
2. **escort vs corridor**: A4 채택안은 Hyunjun 결정 (corridor 변형이 A4 를 제거).
3. **1D 는 3D 의 사영**: R2a 판정이 **PARTIAL_3D** — 3D 경계는 λ (cone 기하 DOF)
   가 추가 좌표이고, 본 명제는 λ 를 포함하지 않는다. "1D 골격 + 3D 측정" 관계로만
   서술하고 1D 가 3D 를 예측한다고 쓰지 않는다. q_dec (결정 cadence) 조건화도
   1D 모델 밖이다.
4. **존재 ≠ 컨트롤러**: (b) 는 shaping 정책의 존재 증명 — 학습 (P2/MARL) 의
   필요성을 정당화할 뿐 대체하지 않는다.
5. **경제 주장 없음** (S6 2층 준수).

## 6. K1 완료 체크리스트 (Hyunjun lane, ≤10/31)

- [ ] Lemma 1 손증명 (§2 체크 포인트 2개 포함)
- [ ] Lemma 2 손증명 (+ A3 약화형으로도 성립 확인)
- [ ] (a)/(a′)/(b) 본문 확인 — 특히 (a′) 의 k-귀납과 (b) 의 δ > 0 산술
- [ ] A4 채택안 결정: escort vs corridor (논문 본문용)
- [ ] 정리문 확정 선언 (이 문서 판올림 + 비준 표기)
