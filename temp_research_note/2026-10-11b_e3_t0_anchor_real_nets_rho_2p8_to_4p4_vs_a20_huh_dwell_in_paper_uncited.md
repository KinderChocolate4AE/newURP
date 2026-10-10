# 2026-10-11b — E3 (T0 외부 anchor + 서지): 공개 net 의 τ≈0.2 s 급은 a = 20.45 상대로 ρ 2.8–4.4 (FS1 1.92 보다 위, 전이 대역 근처) · 위협 a 에 따라 ρ 가 수십 배 변함 · Huh dwell 0.5 s 는 논문에 있으나 인용 없는 설계값

- 방법: 데스크 리서치 서브에이전트 (웹 검색 + 1차 자료 읽기), main 이 서지만 Crossref 로 재확인. **수치는 아래
  출처 등급 그대로만 쓴다** (P = 1차: 제조사 사양서·논문 원문 / S = 2차: 언론·딜러). 지어낸 값 없음,
  못 찾은 것은 "공개 자료 없음".
- 정의 정리: R_max·tanθ = 사거리에서 net 반폭 r_net → **ρ = r_net / (½·a·τ²)** (net 반폭 / 탈출 반경).
  FS1: r_net = 8.22·tan12.2° = 1.777 m, r = 0.920 m → ρ 1.93.
- **τ 정의 주의 (D5 와 같은 문제)**: 우리 τ = 발사 → 포획 판정까지 공격자가 도망칠 수 있는 시간. 발사체형 net
  에서는 "펼침 시간" 이 아니라 **표적 도달까지 시간 (비행 + 펼침)** 이 맞다. 제조사의 "0.2 s 에 펼쳐짐"
  은 비행 시간을 빼먹었을 수 있으므로 그 ρ 는 **상한 (낙관)** 으로만 읽는다.

## 1. 실물 net → ρ (a = 20.45 기준)

| 시스템 | 근거 | τ | r_net | ρ | 등급 |
|---|---|---|---|---|---|
| FS1 (본 연구) | — | 0.30 | 1.78 | **1.93** | — |
| Han et al. 2026 (UAV 탑재 net, FEM + 야외 시험) | 3×3 m, 75 m/s, 표적 약 10 m 첫 접촉 t = 0.228 s (도달 시간 = 우리 τ 정의에 가장 가까움) | 0.228 | 1.5 | **2.82** | P (저자 caveat: 실험 지속시간이 시뮬보다 김) |
| BlueBird Chipa (휴대 발사) | ≤ 25 m, 3×3 m, "약 0.2 s" | 0.2 | 1.5 | 3.67 | P (제조사 주장) |
| Teneta MITLA-1 (휴대 발사) | ≤ 25 m, 3.5×3.5 m "in 0.2 s" | 0.2 | 1.75 | 4.28 | S |
| NetGun UltraNet 2.0 | 15 m/s, 3–4 m 에서 펼침 | 0.20–0.27 (펼침) / 0.6 (9 m 도달) | 1.5 | 2.06–3.67 / **0.41** | P |
| ParaZero DefendAir | 15–30 m, "1 s 에 완전 전개" | 1.0 | 2.5 | **0.24** (< ρ₀) | P (net 크기는 S) |
| Xu et al. 2025 (지상 발사 FEM 만) | 5.2×5.2 m, 최대 면적 0.13–0.17 s (그림 추론) | — | — | 거리 미제시로 보류 | P |
| SkyWall 100 / DroneCatcher / Net Gun X1 / Fortem / Dropster / SkyNet | τ 공개 자료 없음 | — | — | — | — |
| Pliska 2024 · Rothe 2019 | 매달린 net (발사 지연 개념 없음) | — | — | 적용 안 됨 | P |

- 읽기: 공개된 τ≈0.2 s 급 net 은 a≈20 위협 상대로 **ρ 2.8–4.4** — 우리 등록 경계 ρ* 2.81 의 바로 위,
  E1 전이 사다리가 덮는 구간이다. 즉 FS1 (τ 0.3) 은 상용 주장보다 보수적인 세계이고, **전이 구간이 실물 사양이
  놓이는 바로 그 자리**다 (E1 의 실무 의미). 단 위 0.2 s 는 대부분 제조사 주장 + 비행시간 미포함 가능성 → 상한.
- DefendAir (τ 1 s) 와 UltraNet 9 m 도달 (0.6 s) 은 ρ < ρ₀ (1.24): 모델 안에서 보장-포획 발사 순간이 없다.

## 2. 위협 등급 → a, V

| 등급 | a (m/s²) | V (m/s) | 근거 |
|---|---|---|---|
| DJI Mavic 3 Pro | 6.9 (g·tan35°, 도출) | 21 | P (사양 틸트각) |
| DJI Phantom 4 Pro | 8.8 (g·tan42°, 도출) | 20 | S |
| Pliska 2024 표적 데이터셋 | 최대 11 | 최대 8 | P |
| 표준 쿼드 (Foehn 2021) | 17.4 (도출) | — | P |
| 레이싱 FPV (TWR ≈ 4) | ≈ 39 (도출) | ≈ 28 | P (Foehn 2021, Kaufmann 2023) |
| 극한 레이싱 (Song 2023) | 117–123 (실측 12.58 g) | 30 | P |
| Shahed-136 / Switchblade 300·600 / Lancet | **횡가속 공개 자료 없음** | 51 / dash 45 / sprint 51 / 급강하 ~83 | S·P 혼재 |

- 같은 net 이라도 위협에 따라 ρ 가 수십 배 바뀐다 (예: Chipa = Mavic 상대 10.9, 레이싱 FPV 상대 1.93).
  → F2 (τ, a) 평면의 실무 의미가 크다. 단 a 방향은 E4/E6 전까지 해석선만 (노트 10-11a).
- **V ≥ 41.1 m/s (창이 어떤 ρ 에서도 4 step 에 못 닿는 영역)** 에 고정익 배회탄 (Shahed, SB dash/sprint,
  Lancet 급강하) 이 들어간다. 회전익은 극한 레이싱도 30 m/s 라 밖. → F2 캡션·논의 1문장 근거.
  **정정 (같은 날)**: 이 한계는 V = R_max/(4·dt) 라서 **R_max 8.22 m 에서만** 성립한다. 사거리 25 m net 이면 한계는
  약 125 m/s → 51 m/s 급 고정익도 창이 열린다. 서술은 반드시 "사거리가 짧은 net 에서는" 조건을 붙인다.
- 추가 확보 대상 DOI (Crossref 확인): Yu, Judasz, Zheng, Botta 2022 *Design and Testing of a Net-Launch Device for Drone
  Capture* (AIAA SciTech, 10.2514/6.2022-0273) · Zhang et al. 2024 *UAV Hunter* (Drones 8(10):573, 10.3390/drones8100573).
  사용자가 PDF 를 받아 넣어 주기로 함 (Huh 2026, Yu 2022, Han 2026 우선).

## 3. 서지 검증 (G6) — Crossref 로 main 재확인

| 문헌 | 결과 |
|---|---|
| **Huh, Lim, Jang, Byun, Yu, Nam 2026** | *Multi-Agent Reinforcement Learning for Multi-UAV Pursuit with Full Planar Motion and a Limited Detectable Region*, Machines 14(4):413, doi:10.3390/machines14040413 ✓ |
| Han, Liu, Xiong, Hu, Lu, Sun, Zhang 2026 | *Dynamics and Experimental Validation of a UAV-Borne Flexible Net for Intercepting Low, Slow, and Small Targets*, Drones 10(7):478, doi:10.3390/drones10070478 ✓ |
| Xu, Peng, Wu 2025 | *Optimization Design of Flexible Net Capture System for LSS UAVs Based on Improved Multi-Objective Wolf Pack Algorithm*, Drones 9(3):190 ✓ |
| Pliska, Vrba, Báča, Saska 2024 | *Towards Safe Mid-Air Drone Interception: Strategies for Tracking & Capture*, IEEE RA-L 9(10):8810–8817, doi:10.1109/LRA.2024.3451768 ✓ (제목 Crossref 확인) |
| Rothe, Strohmeier, Montenegro 2019 | *A concept for catching drones with a net carried by cooperative UAVs*, IEEE SSRR 2019, pp. 126–132 ✓ |

- **Huh capture 정의 (§3.1, 식 (1)) — 서브에이전트가 PDF 원문에서 인용, main 직접 재확인 못 함 (MDPI 403)**:
  capturable region = "effective engagement envelope of the net-gun device", d ∈ [3, 10] m (사거리 근거 = ref [31]
  DroneCatcher 웹사이트), θ_c = 10° (식은 θ_c/2 → ±5°), "Capture was considered successful if at least one pursuer
  maintained the evader within C_i for 0.5 s."
  - **dwell 0.5 s 는 논문에 있다 (P-6 서지 확인 해소). 그러나 그 문장에는 인용이 없다** → 출처 없는 설계값.
    상위 lock 의 "dwell provenance 미확인" 플래그는 "논문 내 무인용 설계값" 으로 정정.
  - 본문 내부 불일치: ±5° 면 10 m 에서 반폭 0.87 m 인데 본문은 "approximately 2 m" (전폭 1.75 m 를 쓴 듯).
  - dwell 은 포획 판정 유지 시간이지 net 전개 시간이 아니다 → Huh 를 ρ 축에 찍는 것은 "dwell 을 τ 로 읽을 때만"
    (ρ 0.34) — 본문에서는 위치짓기를 **τ → 0 극한** (노트 Q1 리포트 §4.4) 으로 하고 이 숫자는 쓰지 않는 것을 권고.

## 4. 못 찾은 것 (gap list 에 남김)

SkyWall 비행시간·전개 시간 · DroneCatcher/X1/Fortem net 크기·전개 시간 · Yu, Judasz, Zheng, Botta 2022 AIAA
SciTech (doi:10.2514/6.2022-0273, Vicon 실측 — τ 실측 근거로 가장 적합, 유료) · 고정익 배회탄 횡가속 전부 ·
DJI 공식 최대 가속도 · MITLA/Chipa 0.2 s 의 독립 실측.

## 5. 반영

- docs/131: G2 → "부분 해소 (공개 τ 표, 상한 해석)", G6 → "해소 (Crossref), Huh dwell = 무인용 설계값".
- E1 의 실무 의미 문장 근거 (상용 net 이 전이 구간에 놓임) · F2 의 실물 점 후보 (Han 2026 = 유일한 1차 학술 τ).
- 사용자 확인 권고: Yu et al. 2022 AIAA (학교 구독으로 접근 가능하면) — τ 실측값 1개가 anchor 의 질을 크게 올린다.
