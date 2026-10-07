# 2026-10-07e — P0a = **AXIS3_NULL** (backend ω=10 에서 turn-limit 사실상 안 묶임) · P0b AUC 0.887 (창 감지 가능 → arm C-① 충분 쪽)

harvest `4d381c3` (`artifacts/fs1/p0/probe.json` + `rows.npz` + `fig_timeline.png`).
선언 = 노트 2026-10-07d (결과 전, 기준·계보·특징 고정). smoke (2 ep, scratch) 와 일관.

## P0a — ③축 (회피 충실도) 1점

- **판정: `AXIS3_NULL`** — w_bk slot 중앙값들의 중앙값 = **1.0 step** (기준 ≥ 4). 12 slot
  전부 1~2 step, base 와 사실상 동일.
- tick 수준: 6905 window tick 중 **rb_wbk ≠ rb_base = 1개** (m1.4 mix5050 ep11) ·
  rb_w8 ≠ rb_base = 14개. witness pruning 중앙값 18% (p_feas 1.0 → pf_wbk 0.821) —
  **필터는 live 인데 (합성 검증: ω2 면 86% pruning) 판정이 안 뒤집힘**.
- 기전: ω=10 rad/s × τ≈0.43 s ≈ 246° — net 비행시간 안에 헤딩을 거의 자유롭게 재배향
  가능 → isotropic 완벽-회피자 가정과 실질 동치. **1~2 step 창은 판정 보수성의 산물이
  아니라 (이 ω 영역에선) 세계의 성질** — ρ 가설 (≈1.6 지배, μν·충실도 불포함) 추가 지지.
- margin 지도: near-flip (base=0 ∧ pf_wbk<0.05) = 189 tick (2.7%), fin12_fb 슬롯에
  연속 run 으로 군집 (fig_timeline 주황) — ω 를 더 조이면 (둔한 공격자 영역) 열릴 영역의
  preview. ③축은 "ω ≳ 10 에서 평평" 단면 확정이지 죽은 축 아님 — E7 격자 포함 여부는
  **포함하지 않는 쪽** 권고 (이 세계의 공격자 스펙에선 레버가 아님; docs/126 §4 E7 조항).
- 계보 규율 준수: w_bk/w8 수치는 별도 계보 — 기존 isotropic 판정치와 합산·비교 판정 금지.

## P0b — 창 감지 가능성

- **slot AUC 중앙값 0.887** (기술 문턱 0.8 상회; 10/12 slot ≥ 0.8, 최저 0.771, 최고 0.986).
  특징 7 (d·closing·p_feasible·limiter 거리 4), ep 짝/홀 split, 양성 30~63/slot.
- 함의 (docs/126 배분 규칙): **"감지 가능성 높음" → arm C-① (판정기-증류 발사 머리) 충분
  쪽**. 창 생성 비중↑ 필요성은 낮게 평가. 단 **arm C 착수는 ③ 게이트 사슬 미결재 — 이
  수치는 배분 입력일 뿐 착수 아님.**

## 종합 (3축 지도 갱신)

③축: 현 공격자 스펙 (ω=10) 에서 닫힘 — "net 보강 없이 학습 가능 영역" 은 이 축에서 안
나옴. 남은 레버 = ①축 (E7: τ_deploy·θ_cone·range, ρ 자체를 키우는 손잡이) + ② 감지 기반
발사 (arm C-①, P0b 가 입력 준비 완료). 다음 결정 = 사용자 ③ 게이트 사슬 결재.
