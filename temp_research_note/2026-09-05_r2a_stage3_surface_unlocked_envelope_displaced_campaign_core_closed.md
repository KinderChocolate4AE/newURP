# 2026-09-05 — Stage 3 confirmatory: nominal 3-D 경계면 UNLOCK · A2 family envelope 는 전 행에서 밴드 밖으로 displaced · J+R+ 상호작용은 길항 — R2a core 캠페인 종결

protocol `eb3a85e702020167` · 95,200 ep · HARD_KILL 0 · code lineage 단일 b397720 ·
**repo-R1 PASS 후 개봉** (readout 하드 게이트 이행, manifest = repo_r1_manifest.json).

## (a) nominal 국소 3-D 경계면 — **UNLOCKED** (봉인 규칙 충족: 14/14 행 무censoring)

| η | χ50(λ 4.644) | χ50(λ 3.574) | Δ (slice 간) |
|---|---|---|---|
| 2.1 | 0.610 [.600,.629] | 0.555 [.546,.563] | −0.055 |
| 2.4 | 0.585 | 0.531 | −0.053 |
| 2.7 | 0.563 | 0.511 | −0.052 |
| 3.0 | 0.557 | 0.499 | −0.058 |
| 3.3 | 0.544 | 0.479 | −0.064 |
| 3.6 | 0.541 | 0.470 | −0.071 |
| 3.9 | 0.521 [.518,.534] | 0.443 [.441,.450] | −0.077 |

- Stage 2 (λ0 full map) · scout (λ2) 와 전부 CI 내 정합 — 설계→확정 사슬 교차검증 3중.
- slice 간 D_χ = −0.052~−0.077, |Δ| 가 η 에 단조 증가 (λ 효과는 고 η 에서 더 큼).
- **이제 허용 어휘**: "the nominal local 3-D boundary surface χ50(η, λ) over the
  tested domain" (unlock rule 충족). coverage 언어 유지, representative 금지 그대로.

## (b) A2 family envelope — **전 14 행 displaced** (사전 봉인 어휘로 보고)

- p_worst = min{nom, J+, R+, J+R+}: nominal 경계 셀에서 0.25~0.43. **28/28 셀 전부
  p_worst < 0.5** → "local envelope displaced beyond the tested nominal boundary band"
  — worst-case χ50 추정은 봉인대로 scope 밖 (외삽 없음).
- argmin 분포: **R+ (route 0.75) 가 지배적 worst**. J+ 는 중간.
- ★발견: **J+R+ 상호작용은 길항적** — 다수 셀에서 p(J+R+) > p(J+), p(R+), 일부는
  p(nom) 초과 (예: λ0 (0.54,3.9) nom .407 vs J+R+ .503). 가속 clamp + 방향 경쟁이
  두 회피 모드를 간섭시킨다. corner 를 넣어야 한다던 감사 판단이 정확히 적중 —
  없었으면 "고회피 = 더 나쁨" 단조 서사를 무근거로 썼을 것.
- A1 anchor: **전 28 셀 p_A1 = 1.000** (min 밖, 방향 통계 +0.34~+0.64) — 회피
  벡터가 경계 높이의 압도적 결정자라는 a priori 후보 판단의 극단적 확인.

## registry 등록안 (사용자 트랙 — 초안)

- **C044**: nominal local 3-D boundary surface χ50(η, λ) — λ0 slice full map (Stage 2,
  n=4,800/행) + 양 slice 경계 밴드 confirmatory (Stage 3, n=1,360/행, CI 표) +
  λ∈{4.644, 3.574}, η∈[2.1, 3.9]. 조건: sealed A2-nom vector · q_dec 1/6 ·
  capability family · legacy 회랑.
- **C045 = PARTIAL_3D** (등록 가능 상태): (χ,η) 단독 불충분 — λ (단일 cone-기하 DOF)
  추가 필요. 2-D 좌표 잠금 무효, R2b 는 (χ,η,λ) 좌표에서 재설계. 근거 사슬 = Stage 1
  R-rho-DOM 6/6 FAIL → Stage 4 직교 재현 (dose-ordered) → Stage 3 slice 분리
  −0.05~−0.08 confirmatory.
- **C046**: provenance (repo-R1 manifest + seal 체인 4세대 supersession) + caveat:
  legacy 24 m 회랑 · A2-reactive sealed vector · q_dec = 1/6 (governing, 실측 민감) ·
  local A2 family envelope 는 밴드 밖 displaced (worst 경계 위치 미추정) · coverage
  ≠ representativeness.

## H-SIM / H-DOM 최종 문장 (캠페인 종합)

- H-SIM: "implemented dimensional rescaling preserved the normalized hold-arm dynamics
  and capture outcomes exactly over the tested boundary scenarios" (pathwise 8e-15 +
  0/4,800 labels).
- H-DOM(k_f·τ): tested +50% 교란, 6 경계 셀에서 δp 내 robust.
- λ: governing (승격 입증 사슬 완결). q_dec: governing conditioning (pin 유지, 부록
  mini-map 예정). evasion: local A2 family 내 systematic 완화 완료 — worst-case 는
  밴드 밖 (displaced 보고).

## 남은 것 (core 밖)

sensitivity screen (OAT, 봉인 설계 노트) → q_dec 1/12 mini-map (부록) → SIM corner
QA → G3 판정문 (금요일 감사 리듬, 오늘이 금요일 — 사용자 판정) → C044~046 registry
등록 (사용자) → R2b 재설계 (3-D 좌표). KSAS 9/11 은 독립 병행.
