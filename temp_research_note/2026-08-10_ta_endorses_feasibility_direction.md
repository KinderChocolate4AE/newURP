# 2026-08-10 — 정용주 조교, feasibility-first 방향 지지 · iso-Π 답신 초안 검증 (보정 2건)

## 판정

**KSAS 추계 논문을 feasible/infeasible 방법론으로 쓰는 방향이 조교 레벨에서 지지받음.**
정용주 조교 (LiCS) 답신 (8/10 16:46): "좋은 논리적 접근" · "추후 더 advanced 된 논문을
위해서도 이 작업이 큰 의미" · "되는 상황을 정해놓고 하는 연구보다 본질적으로 접근하는
태도 훌륭". docs/72 (KSAS fall paper plan) 방향과 정합.

## 조교 질문과 답신 논리

질문: *"feasible/infeasible region 을 찾을 때 파라미터가 몇 개씩 필요한가?
아니면 이게 알아나가야 할 부분의 일부인가?"*

답신 골자 (docs/74 §3.8·§3.9 + lattice_spec.py 와 교차검증 완료):

1. 원시 파라미터 → Buckingham-Π 로 무차원군 12개 완비 도출 (길이 ρ_net, 시간 τ).
   basis 는 등가 — 공간은 사실, 좌표계는 판단.
2. 지도의 점 지정 = **4개** (chi, kappa, mu, N). 나머지 8개는 nominal conditioning 고정.
3. **"4개로 충분한가" 자체가 검증 대상** = iso-Π reduction validation:
   - Tier 1 (완전 상사): 12개 전부 같은 쌍 → 결과 동일해야 함. 실패 = 숨은 차원 상수
     또는 Π 미완비 → 버그 검출기.
   - Tier 2 (reduction): core 4 고정 + conditioning 하나씩 교란 → 허용오차 내 collapse
     시 해당 group 무관 실증. 8개 전부 성립해야 4D 단면 충분 주장 확립.
   - 실패 시 escalation 순서 사전 고정 (eta→alpha→lam→nu→sig_*), 축 추가는
     Phase III-B 새 protocol_hash (§5.1).

## 답신 초안 보정 (발송 전 반영 권장)

1. **mu 방향**: 초안 "공격자와 방어자의 최대가속도 비율" → 실제 정의는
   **mu = a_lim / a_att (방어/공격)**. 어순이 역수로 읽힐 수 있음.
2. **"임의로 고른 값" 톤다운 주의**: kappa 는 docs/46 실측 (채널 (i) 이 κ 를 따라
   켜짐) 근거가 있는 **가설 기반** 선택. "임의" 표현은 본인 메일이 지적한
   "답 정해두고 학습 돌린 것" 비판을 자초하는 단어 — "물리적 가설에 근거해 선택,
   iso-Π 로 반증 가능" 프레임 권장.

## 남은 것

- iso-Π 게이트 10 의 **허용오차 수치 + paired 통계량 미봉인** — 런 돌리기 전 선언
  필요 (결과 보고 tolerance 고르면 게이트 무의미).
- 답신 발송 (보정 2건 반영 후).
- 서버 coarse pilot 본실행 4 샤드 · MARL 9 런 완주 대기 (미열람 유지) — 8/9 note 승계.
