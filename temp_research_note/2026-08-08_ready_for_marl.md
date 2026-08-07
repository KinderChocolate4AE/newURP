# 학습 직전 상태 도달 — baseline FROZEN(c5)·CLI 배선·G2 smoke 준비 완료 (다음 = 서버 3단)

**2026-08-08 · 실행 세션 4부(마감). 커밋: b89ee86(F8 SELECTED c5 동결) ·
8275bb5(서버 튜닝 결과 900롤아웃) · bfcfb31(docs/69 승인) · fa6753f(arc
구현+A4c) · fc17ab9(ntfy) · 2935356(CLI+smoke). push 대기 = 로컬 2개
(b89ee86 이후).**

1. **scripted baseline 종결**: 튜닝 9조합×100판 (서버, ntfy) →
   **SELECTED c5 (R_d=9, Δφ=π/6)** — c4/c5 동률에서 preregistered
   tie-break ②(접촉 少) 기계 발동. docs/63 §7 F8 기입 = **BASELINE
   FROZEN** (MARL 후 변경 금지·튜닝 수치 headline 재사용 금지).
2. **문구 정정 (비준 지시)**: commit=0 = controller action family 한정 —
   destructive outcome 불가 아님 (c0 의 HARD_KILL 18 = R1 resolver 산물).
   고정 영문 문구 등재, c5 관찰은 선택 근거 아님 명시.
3. **CLI 배선**: train_m4 `--threat-layer` choices=['train'] — iid(held-out)
   /nominal(규율 2) hard fail, --no-threat-randomization 동시 사용 차단,
   summary.json 에 threat_layer+contract(G1) 기록.
4. **G2 smoke 러너** (`smoke_v3_train.py`): PASS 체크리스트 결과 전 고정
   (HEAD/dirty·layer·dist hash pin·F-계약·1100·fresh policy/optimizer/norm·
   ckpt parent null·finite·label enum·manifest 저장). 성능 비산출·비판정.

★ **다음 세션 = 서버 3단 (사이에 판단 없음)**:
```
python -m shepherd.scripts.smoke_v3_train --out results/smoke_v3_train.json
python -m pytest tests/test_contract_parity.py tests/test_arc_baseline.py -q
python -m shepherd.scripts.train_m4 --threat-layer train --seed 0 \
    --device cuda --output results/m4_v3_train    # (스윕 축/시드는 docs/47 선언)
```
smoke ALL PASS + parity green 확인 후에만 3번째로. 이후 = headline
(hold vs scripted(c5) vs MARL, **IID 10000..10299**) → attribution →
OOD-CPA → A4. 남은 비준 게이트 없음 — 전부 실행 트랙.
