# 리셋 전 전수 감사 — 코드는 건강, 계약은 두 세계로 갈라져 있음 (수정 0건)

**2026-08-08 · 감사 세션 (Task 1 claim/evidence/code · Task 2 reward/COMA ·
Task 3 dead code). 산출물 = `artifacts/audits/` 7파일. 코드·docs 수정 0,
삭제 0 (SAFE_DELETE 판정 통과 파일 없음).**

핵심 판정 (상세 = `artifacts/audits/RESET_WEEKLY_AUDIT_SUMMARY.md`):

1. **판정식 코드는 문서와 일치** — capture rule·spent_fail·boxed SPLIT·R1
   swept/NK veto/Pk·R2 억제 전부 서술대로. pytest 508 pass (로컬 기지 결함만).
2. **blocker 5**: ① train_m4/sweep_m4 가 R1/R2 플래그 미전달 (학습 = 구계약)
   ② mission_eval 이 standby/extra_cfg 유실 (V3-FULL 평가 불가) ③
   CAPTURE_WITH_CONTACT 종말보상 0 ↔ 지표 성공 (계약 결정 필요) ④ docs/61
   TRAIN 분포 미배선+비준 대기 ⑤ docs/50:183 철회 문구("하드킬로 도망") 잔존.
3. **COMA 는 전 M4 런에서 gradient 미도달** (coma_mix=0) — coma_D 로그를
   학습 신호로 읽지 말 것. legacy geometry 의 유일한 살아있는 gradient 경로
   = limiter_p0 (Δv_shot 기준선), standby 팔에선 자동 재정의됨.
4. **dead code 삭제 0건이 정답이었음** — ZERO-REF 3건은 전부 plot 시블링
   (그림 원천 가능성 → UNCERTAIN). ARCHIVE_ONLY ~70건 분류 완료.
5. 부수: params.py 레지스트리 오기 4건 (limiter_pressure 가 가장 위험 —
   idx3 은 이제 커밋 비트), rollout_gif 는 _zero_commit 미사용 트랩,
   duplicate 후보 6군 (기저선 규칙 인라인 6곳이 최대 위험).

감사 중 HEAD 이동 (f5c75b6 → 0e94111, 동시 세션의 P94 GREEN 커밋) — 판정식
커밋이 결과에 선행함을 git 으로 확인, 사전등록 규율 유지.

다음 세션 = summary §G 순서 (blocker 수리 → 계약 결정 → P92/P93/P95).
새 실험 설계는 하지 않았다.
