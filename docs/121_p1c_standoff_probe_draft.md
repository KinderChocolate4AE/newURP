# 121 — P1c standoff 축 probe 설계 초안 (미봉인 — P2 판독 후 결재·봉인)

- **일자**: 2026-10-03 · **상위**: docs/117 수순 (P2 완주 → P1c → 근거 시 B0 v4)
- **동기 (사용자 지적, 2026-10-03)**: 현 세계는 접근 거리가 짧아 limiter 조형의
  활주로가 없다. 정합 증거: B2 rule +0.002 · b5 무신호 · steering probe 09-13d
  "margin 센티미터" · P1a sense 30≡∞ 포화 (전 접근 구간이 종말 감지권 안).
  반대편 제약: 스폰이 멀면 교전 외 시간이 시뮬레이션을 낭비.

## 0. 선행 결정 (2026-10-03 사용자 승인) — 종말 감지권(sense_range) nominal 제거

- **P1c 부터 nominal 공격자 = 전지 관측 (sense ∞)**. 근거: 30 m 는 닻 없는 magic
  constant 이고 (curve_sweep 단일점 유래), 현 스케일에선 죽은 파라미터지만
  standoff 확장 순간 숨은 driver 가 된다 — 6DOF 철회와 동형 논리. ∞ 는 근거가
  필요 없는 **한계 사례**이며 방어자-보수적 (전부 보는 공격자를 이긴 조형이
  더 강한 주장; null 에 "감지 핸디캡" 반론 차단).
- 소급 금지: 봉인 세계·결과 (KSAS/B2/R2a T1=30, 진행 중 P2 포함) 불변. P2 는
  P1a 측정상 30≡∞ 라 실질 동일 세계다. `sense_range` 코드 파라미터는 ablation
  노브로 유지하되, 유한값 주장은 실측 센서 근거를 갖춘 별도 축으로만 복귀.

## 1. 질문

**standoff (교전 진입 거리) 를 늘리면 limiter 조형의 여지가 실제로 열리는가** —
defender 동결 (hold vs c5) 상태에서, c5−hold 격차와 조형 margin 이 standoff 의
함수로 어떻게 변하는가. 이것이 "거리를 늘리면 조형 가치가 생긴다" 가설의 측정
근거이며, B0 v4 (layout 개정) 의 go/no-go 입력이다.

## 2. 설계 골자 (결재 대상)

- **진입 게이트 방식**: 죽은 시간을 시뮬레이션하지 않는다. episode 는 공격자가
  선언된 진입 게이트를 통과한 상태에서 시작하고, **진입 상태 분포** (거리·방위·
  횡속도) 를 randomize 한다. 단거리 pop-up 은 분포의 근거리 꼬리로 포함.
- **standoff 격자**: 진입 거리 스케일 {1× (현행), 2×, 4×} — 각 스케일에서 동일
  cell suite · paired CRN. (구현: spawn_dx / adversary_start_x 스케일링이
  χ·η 무차원화와 어떻게 상호작용하는지 봉인 전 확인 필요 — spawn 은 layout
  이지 χ 좌표가 아님을 검증.)
- **arms**: hold / c5 (defender 동결, scripted launcher) × 공격자 {route 0.5
  nominal, route 0.8} × sense ∞.
- **판독 지표 (사전 등록)**: ① standoff 별 c5−hold ΔN (paired) ② 조형 margin
  proxy (steering-probe 계열 — prefix 개입의 경계 이동 폭) ③ 교전 시간 중
  limiter-가시(=조형 가능) 구간 비율. 분류: 격차가 standoff 와 함께 열리면
  `STANDOFF_OPENS_SHAPING` → B0 v4 결재 입력; 안 열리면 "조형 가치가 활주로에도
  둔감" — 그 자체가 foundation 결과 (P2 결과와 함께 해석).
- **예산**: scripted only — 3 스케일 × 2 arm × 2 공격자 × 280 ep ≈ 3,360 ep.

## 3. 봉인 전 확인 사항

1. P2 판독 반영 (P2_POSITIVE 면 learned arm 1개를 P1c 에 얹을지 — 단일축 규율상
   기본은 scripted 만).
2. spawn 스케일링의 세계 계약 저촉 여부 — extra_cfg 의 layout 키만 바꾸면 B0 v3
   재개봉인가, 평가 scenario 의 자유 변수인가 (docs/94 계약 정독 필요). 저촉이면
   P1c 자체를 v4 pre-check 로 명명.
3. margin proxy ② 의 정확한 정의 (steering probe 재사용 vs 단순화).
