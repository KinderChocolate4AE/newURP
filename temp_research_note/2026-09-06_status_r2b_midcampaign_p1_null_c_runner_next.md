# 2026-09-06 — 상태 기록: R2a 종결(PARTIAL_3D) 후 R2b 중반 — P1 null 확정, C arm 러너 구축 대기

세션 상태 스냅샷 (판정형 상세는 개별 노트 참조; 이 노트는 위치와 다음 수만 고정).

## 위치

- **R2a**: 종결·감사 승인 (G3 = PARTIAL_3D). C044~C046 + G3 등록·freeze 만 잔여
  (**사용자 트랙**, 문안 = closure 브리프 §8). Stage 0→3 전 사슬 hash 봉인,
  판정 노트 6편 + 감사 브리프 4편.
- **KSAS**: 제출 완료, micro-edit 단계 (사용자 트랙).
- **R2b**: B0 v2 `cba024d7ee3d9f61` 하 진행 중.
  - Phase 1 v2 (fresh stream r2b_p1_v2, 22,400 ep) 완료 → **P1_NOT_POSITIVE**
    (Δp_net −0.001 [−0.004,+0.001], 행 5/14). treatment 배선 검증됨 (기계 차이
    26.8%). 저 η kinetic 1:1 치환 관측. phase2_trigger False.
  - v1 사고 이력: HARD_KILL sentinel 발화 → quarantine (`phase1_v1_aborted/`,
    manifest 1b20c43a291324be) → B0 v2 개정 (arm-A-only STOP, 2층 estimand,
    C_N semantics). 표준 모범 사례로 기록됨.
  - branch seal `f1bd9a459d97e693`: **FULL_28x100 lite C** (T_proj 8.71h ≤ 14).
- **다음 결정자 = C arm** (봉인 3-way): C_N+ → learned controller 동기 / C_N null
  → 봉인 null-null 문장. 양쪽 다 논문.

## 다음 수 (순서)

1. **C 러너 구축** (다음 세션 첫 작업): p2prime CEM 을 R2b scenario 에 적응 —
   s0=0 full-episode limiter plan (K_SEG 4, 3 seed × 384 lite), 경량 클론 proxy +
   full-fidelity replay 판정, **C_N = NET_CAPTURE 만 성공** (HARD_KILL rollout
   불인정), C_U/C_H secondary, S_C = S_AB_v2[0:100], solver seed ≠ scenario RNG.
   bit-parity smoke 필수. 서버 ~8.7h (8샤드).
2. C 판독 → 3-way 문장 확정 → R2b 종결 감사 → registry (C047+?).
3. 이후 대기열: q_dec 1/12 mini-map (부록) → OAT sensitivity screen → prop1
   (K1 ≤10/31) → fidelity gate (6DOF transportability).

## 재현 정보

seal 체인: R2a-P3 `b7b3f6440e5b83eb` · stage3 `eb3a85e702020167` · B0 v1
`e3fd7800003d34e1` → v2 `cba024d7ee3d9f61`. 최근 커밋 d84cbb3. 테스트
tests/test_r2a.py 28 green. 서버 = /data/hjhong/l2/newURP (.venv-l2, scipy 설치됨),
ntfy 채널 hj_URP_x7k2q9. 인코딩·랩서버·viz-first 규율은 memory 파일 참조.
