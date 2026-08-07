# 학습 전 마지막 설계 게이트 닫힘 — 결정 A·TRAIN FINAL FREEZE·docs/63 r2 비준 (남은 건 구현·튜닝뿐)

**2026-08-08 · 실행 세션 3부. 커밋: 4418481(docs/69 결정 A + FINAL FREEZE) ·
edb0b91(docs/63 r0) · 5802fc9(r1, 수정 4건) · b6ea0fb(r2 = 비준·동결).
전부 push 대기.**

1. **결정 A 이행 (docs/69)**: 무명 design bins — 분포·draw·hash(efeffcbf)
   불변, ordinal claim 만 폐기. G1/G2/G3 표기 규율 + GAIN_BIN_NAMES 매핑
   (코드 키는 hash 동결 때문에 legacy identifier — C4 선례). hash 불변
   검증 완료. **TRAIN DISTRIBUTION FINAL FREEZE 선언.**
2. **docs/63 사이클 (r0→r2, 하루 완결)**:
   - r0: reactive arc family + 3×3 grid(R_d×Δφ, 자유도 2축) + 900 롤아웃
     예산 + TRAIN-only + p_net 선택.
   - r1 (조건부 승인 4건): bounded wording(논문 고정 문구 2개) · 튜닝/평가
     표본 분리 · **24-permutation 최소비용 slot assignment** ·
     capability parity (코드 확인: 관측 = 공유 global 벡터라 ally 위치
     적법 + v_shot 도 관측이라 family-제한으로 재근거 / MARL commit live
     ↔ scripted commit 0 → 참조선 병기 + isolates-nondestructive 문구).
   - r2 (최종 수정 1건): **sole primary headline set = IID 10000..10299
     (n=300)** — TRAIN 20000 대역 제거, lexicographic 1~3 전부 이 set.
     selection(TRAIN 5000..5099)→freeze→held-out IID 구조 완결.
     n=300 = fixed budget (power 보장 아님) wording.
3. **현 상태**: MARL 앞 사전등록·비준 게이트 전부 닫힘. 18단계 사다리
   재편 후 잔여 = 구현 트랙만:
   ① arc controller 구현 (+_zero_commit, 24-perm assignment, A4c manifest
     parity 테스트) ② 9조합 × 100판 튜닝 (900 롤아웃 — **랩 서버 권장**,
     long-run policy) ③ F8 r2 기입 동결 ④ G smoke (fresh-state manifest)
   ⑤ MARL TRAIN → headline(IID) → attribution → OOD → A4.

주의: 튜닝 실행 전 어떤 IID/OOD 롤아웃도 금지 (F6). scripted 튜닝 결과를
본 뒤 docs/63 의 어떤 요소도 변경 금지 (F8·리뷰 7 순서 규율).
