# 2026-10-06a — E3 stage 1 해석 가드 (정본 평가 전 기록): ceiling_s 는 scripted 천장이지 세계 천장이 아니다 — BAND_EMPTY ≠ "방어 불가"

사용자 지적 (정본 평가 전, train-side 신호만 본 시점): "방어 학습을 아예 안 시켰다 —
이건 scripted 천장이 열린 것뿐." **수용.** 아래를 판독 전에 못 박는다.

## 1. stage 1 이 확립하는 것 / 못 하는 것

- ceiling_s = **scripted 2종의 착취 가능성 지도**. 전 격자 개방 시 결론은 "이 scripted 들은
  어디서나 착취된다" 까지. **"학습 방어도 불가" 주장 금지** — pilot 의 "아무도 못 막는다" 는
  같은 cell 에서 학습 방어(run3)도 전용 exploiter 에 3.8% 로 무너졌기에 성립했던 것.
- band 하한 20% 의 비대칭: "바닥끼리 비교 방지" 는 *학습도 바닥* 을 전제 — scripted 0% cell
  이야말로 "scripted 는 못 하는데 학습은 하는가" 가 열리는 곳인데 봉인 규칙이 배제한다.
  **설계 한계로 인정, 단 지금 수정 금지**: train-side 수치 (전 cell wr 0.96~1.00) 를 이미 봤으므로
  지금의 선정 규칙 변경 = 결과 의존적 계약 수정.

## 2. 사전 해석 선언

- `E3_BAND_EMPTY` = "봉인된 비교 (학습 − 최강 scripted, D ≥ +24) 가 의미 있는 cell 이 없다".
  거기까지. regime 지도 (Fig 5) 는 "scripted-착취성 지도" 로 명명.
- 후속 = **새 계약 E3b** (P1c→P1d 전례): scripted 전면 개방 cell 에서 **절대 기준** 학습 시험 —
  소수 cell (물리 근거 선정, 예: μ{0.35, 0.7, 1.4}×ν1.0), arm A/B, "학습 방어 vs 전용 exploiter
  ≥ X/240 → `LEARNING_EXCEEDS_SCRIPTED_CEILING`". X·cell·seed 규칙은 **정본 stage 1 판독 후 ·
  E3b 학습 결과 전** 봉인. μ=0.35 (pilot cell) 포함 시 run3 증거와 접점 (단 pooling 금지).
- 사전 등록 예측 (μ* ∈ [0.5, 1.0]) 이 깨지면 그대로 보고 — E6 해석 (K1) 의 수정 입력.

## 3. stage 1 실행 기록 (이어서)

- 학습 완료 (JAX 보고): host = **server6**, 구현 0df35f3 `--stack r4`, 30 run × 1e7 완주,
  21:40~00:2x, seed 규칙 준수. ckpt = `/data1/hjhong/fs1jax/e3/stage1/<cell>/exploit_*/`.
  train-side (판정 아님): 전 cell exploiter wr 0.96~1.00 — 예측 상충, BAND_EMPTY 방향.
  특이 run: m0.5_n1/fin12_fb 중반 붕괴→회복 (평가-train 괴리 후보).
- server4 상태 (00:23): load 16/24 (petchth ~11.5 코어), repo d34a931 (pull 필요), 디스크 여유.
  평가는 WORKERS=8 로.
