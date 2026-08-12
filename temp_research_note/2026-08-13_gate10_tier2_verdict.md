# 2026-08-13 — 게이트 10 Tier 2 판정: core-only 충분성 미확정 · alpha/lam 교란은 confound(설계 결함) · sig_as 는 clean governing

계약 = `docs/78` r3. tranche = shared frozen validation (ep 10..14). 상태수 = chi 0.4/0.8/1.6
각각 72/120/108. 6군 단일 headline 금지 규율에 따라 group×class×chi 로 보고한다.

## 1. 결과표 (두 교란 f∈{0.8,1.25} 중 나쁜 쪽, bar = med 0.02 / p95 0.05)

| group | class | chi 0.4 | chi 0.8 | chi 1.6 | 판정 |
|---|---|---|---|---|---|
| nu | P | INCONCL (n=27) | **PASS** (전 Q 0.0) | **PASS** (전 Q 0.0) | 조건부 nuisance |
| sig_sb | Z | INCONCL (n=27) | **PASS** (전 Q 0.0) | **PASS** (전 Q 0.0) | 조건부 nuisance |
| sig_as | P | INCONCL | **FAIL** (U_cheap p95 0.26/0.38) | **FAIL** (U_cheap p95 0.96) | **clean governing** |
| alpha | P | INCONCL | FAIL (V0 med 0.11) | FAIL (V0 med 0.037) | **confound — 무효** |
| lam | P | INCONCL | FAIL (V0 p95 0.82) | FAIL (V0 p95 0.25) | **confound — 무효** |
| eta | Z | INCONCL (n=22, drop 37) | INCONCL (n=38, drop 61) | INCONCL (n=37, drop 58) | 미결 |

chi 0.4 은 전군 INCONCLUSIVE (informative n=22~28 < 50). 교란 f 는 `sig_dt`(G) 제외 6군.

## 2. ★ 설계 결함: alpha·lam 은 conditioning 이 아니라 **core 를 움직인다**

m4_config 가 명시한 연동 정의를 실측 확인:

```
range_max · tan(half_angle) = 8.22 × tan(0.2121) = 1.7701 = rho   (완전 일치)
```

즉 **ρ 는 독립 파라미터가 아니라 cone 의 max-range 반폭**이다. 따라서:

| 교란 | ρ_eff | chi_eff/chi |
|---|---|---|
| alpha ×0.8 | 1.408 | **1.257** |
| alpha ×1.25 | 2.232 | **0.793** |
| lam ×0.8 | 1.416 | **1.250** |
| lam ×1.25 | 2.213 | **0.800** |

**core (chi, kappa) 가 ±25% 이동한다.** 관측된 부호가 이를 확증: alpha ×0.8 →
mean_sign(V0) **−0.96**, ×1.25 → **+0.91** 로 완전 반대칭 = 순수 scale 효과.
⇒ **alpha/lam 의 FAIL 은 "추가 governing 좌표" 증거가 아니라 core 를 건드린 결과**다.
r3 §C-3 의 P-FAIL 해석을 이 두 군에는 적용할 수 없다 (무효 판정).

**부수 결론**: (alpha, lam) 은 독립 2군이 아니다 — 실제 자유도는
**(scale ρ_eff, shape lam)** 이며 shape 하나만 conditioning 후보다.
등록 Π 목록의 이 중복은 이번에 처음 드러났다.

## 3. sig_as = clean governing (U_cheap 한정)

V0·L1·LN 은 전부 0 변화 (asset 은 이 셋에 안 들어감), **U_cheap 만 p95 0.26~0.96**.
물리적으로 자명하고 정합: R_NK 는 unblockable-mass 상한의 admissible domain 을
정의하므로 NK 존이 커지면 지울 수 없는 witness 가 늘어난다.
⇒ **sig_as 는 U_cheap 에 대해 governing coordinate, V0/L1/LN 에 대해서는 nuisance.**
Q 별로 결론이 갈리는 첫 사례 — 지도 결론에 "U_cheap 은 R_NK 조건부" 를 명시해야 한다.

## 4. nu · sig_sb 의 PASS 는 **regime-conditional** (과대해석 금지)

둘 다 전 Q 에서 정확히 0.0 이다. 그러나 원인을 보면:
- **nu** (limiter_v_max) 는 `_assignable` reachability 에만 들어가는데, 하한 쪽
  지평선이 `T = t·dt` (경과시간, 18 s 급) 이라 **reachability 가 애초에 비구속**이다
  (Π 노트 §D 의 미등록군 `T_reach/τ` 문제). 게이트 7 의 τ-지평선이었다면 구속됐을 것.
- **sig_sb** (limiter 배치 반경) 가 0 인 것은 **limiter 가 이 regime 에서 어떤
  witness 도 막지 못하기 때문** — 게이트 7/B1 (n_sigs=0) 과 같은 사실의 재확인.

⇒ 두 PASS 는 "진짜 nuisance" 가 아니라 **"해당 채널이 이 regime 에서 비활성이라
무관"** 이다. 문구: *"nuisance within the tested regime, where the corresponding
channel is inert"*.

## 5. 지금 답할 수 있는 것 / 없는 것

- **답할 수 없음**: "C 는 core (chi,kappa,mu,N) 만으로 충분히 매개변수화된다."
  6군 중 clean PASS 0, clean FAIL 1(sig_as), 무효 2(alpha/lam), 미결 3(eta + chi0.4 전군).
- **답할 수 있음**: (i) sig_as 는 U_cheap 의 governing 좌표다. (ii) ρ 는 cone 기하의
  종속량이라 등록 Π 에 중복이 있다. (iii) nu·sig_sb 는 이 regime 에서 무관하다.
- **chi 승격 불가 유지**: "chi is a governing similarity coordinate" 는 Tier 2 가
  core-only 충분성을 못 세운 현재 상태에서 아직 금지.

## 6. 다음 (docs/78 r4 로 봉인 후 실행)

1. **cone shape 교란 재설계**: ρ_eff = range_max·tan(alpha) **고정**한 채
   `lam` 만 ×0.8/1.25 (alpha 는 tan(alpha') = tan(alpha)/f 로 동반). 이것이 유일한
   진짜 cone conditioning 이며 alpha/lam 을 대체한다 (2군 → 1군).
2. **eta INCONCLUSIVE 해소**: 상태수 확대 (CAP 120 → 300, ep 10..19) — admissibility
   탈락률이 높아(37~61) informative 가 50 미달.
3. **chi 0.4 해소**: 동일 (상태 72 → 확대).
4. **nu 재시험 (선택)**: 하한 reachability 를 τ-지평선으로 둔 조건에서 재평가하면
   비구속 artifact 가 제거된다 — 단 이는 pilot 정의 변경이므로 별도 사전등록 필요.

산출물: `results/phase3/gate10_tier2_chi{04,08,16}.json` (+ .log).
