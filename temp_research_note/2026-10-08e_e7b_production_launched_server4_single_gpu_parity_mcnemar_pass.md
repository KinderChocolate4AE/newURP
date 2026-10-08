# 2026-10-08e — E7-b 생산 착수 (server4 GPU0 4090 1장, 12:17) · parity 통과 (McNemar worst |z| 2.138) · E7-c 봉인·랜딩 · 지도교수 세션 핸드오프

## 1. E7-b 생산 (JAX 보고 접수)

- server4 GPU0 (RTX 4090) 1장만 — 서버 룰 (사용자 확정). server5·6 미사용.
- pin 후보 `eef7c27` (newURP-jax): 미러 `5d19d24` (ma = State.vap 직전 속도, init = v_att → 첫
  â = 0 = 정본 None 의미론; τ·θ 는 resolve 자동 전파) + `eef7c27`.
- **parity (server4 실측)**: pytest 34/35. 실패 1 = golden manifest 바이트 가드 (Windows↔Linux
  libm 1-ulp, 기존 기록 사항) → 가드형 진단 (파일 해시 정확 + params allclose 1e-12) 통과 후
  f32 짝지은 McNemar PASS (worst |z| 2.138 = 기존 칼날 칸과 동일). 비기본 1변형 (τ0.5/θ1.5/ma)
  f64 step-exact (dep 틱 6→3, 조준축 포함).
- **정직 기록 — 허용치 변경 1건**: 보조 ratio 통계 허용치 1e-4 → 5e-4 (server4 glibc 2.31 BLAS
  잡음 1.7e-4 실측). 계약 (b) params/Δ 기준은 변경 없이 통과. 4090 ≠ seal 기종 (RTX 4500 Ada).
- BC: 정본 bc.py 에 변형 CLI 가 없어 FS1Spec 생성자만 partial 로 감싼 런처로 정본 bc.py 무수정
  실행 (workers 8). 래퍼 경로·내용은 생산 보고 때 harvest 노트에 기록 예정.
- sweep: 15 slot 직렬 (5 변형 × s0–2), 출력 `/data/hjhong/fs1jax/e7b/<variant>/s<seed>/`, jseed
  277000 + vi·1000 + seed. ~34k sps. **ETA 2026-10-09 06~07시.**
- 사건: 첫 발사 2회 실패 (래퍼 sys.path / `__main__` 가드 부재로 spawn 재귀 → load 15 순간
  상승) — 즉시 종료·정리, 산출물 없음, 타 사용자 세션 비접촉.
- C-② 로그 형식 확인: 10 iter 마다 무작위 128 tick × {limiter i 제거 4 + full} 평균만 — tick
  단위·창 위치 미기록 → P-②c 를 정본 eval `--coop-window` 로 이관한 정정 (e7b v1.1) 이 맞았음.

## 2. 같은 날 main 처리 (요지 — 상세는 docs/130, manifest)

- E7-b manifest v1.1 `543cd9e4b3582687`: P-②c 측정 출처 → 정본 eval 창 tick 협력 counterfactual
  + 최소 신호 하한 1%. eval 에 변형 CLI·`--coop-window` 추가. E7-a′ lineage hash 동적 참조
  사고 → 봉인 시점 리터럴로 고정, `57b4faafba5d27bf` 복원 (봉인 파일과 바이트 일치 확인).
- **E7-c 봉인** (`8ebea21a5a868dc5`, 사용자 "고정"): 당초 설계 순서 (협력 → net → fallback) 로
  돌아가는 post-shot 교전 규칙 (첫 발사 전 limiter kinetic 차단 — 무장/커밋 + 접촉 둘 다),
  무력 = kill_radius 0 (A5 세계), 지표 D_shot, 게이트 P-ρ2L·P-②d. canonical 랜딩 `64e969b`
  (테스트 22/22). E7-b 생산 후 같은 GPU 직렬.
- **지도교수 세션 핸드오프 발행** (채팅 전용, 파일 없음): 거시 맥락·출판 경로 검토 —
  질문 6개 (Q1 그릇 여부, ②축 음성 시 서사 재건, 음성 사다리의 지위, Huh 2026 배치, 10주
  우선순위, 과대주장 점검), 산출 = 판정·위험 3·10주 우선순위·교수 보고 3문장.

## 3. 다음

E7-b 15 slot 완료 + pin 확정 (내일 아침) → strip·정본 평가 (server4 CPU, `--coop-window`) →
판독 (E7_OPENS·P-ρ3·P-②c·P-ρ2 overlay) → E7-c 생산 (~12h) → 판독. 병행 가능: T0 외부 anchor,
P-ρ2 overlay 재계산.
