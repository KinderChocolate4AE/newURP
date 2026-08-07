# 사다리 [1]~[3] 완료 — contract parity 복구·manifest 하네스·CWC trace, B3 비준 게이트 도달

**2026-08-08 · 실행 세션 (리뷰 6 비준 직후). 커밋 5d1a3b6 (A1~A5 배선) +
0bd6a4a (docs/66 r0). pytest 515 passed / 1 failed(알려진 로컬 cp949) /
61 skipped — 기준선 일치 + 신규 parity 테스트 7종 흡수.**

한 일 (docs/65 18단계 사다리 기준):

1. **[1] A1~A3 runtime pass-through 복구** — `ratified_system()` (F-flags
   canonical, env_sys — SystemSpec 기본값 불변) 신설. train_m4.build_specs ·
   sweep_m4.measure_baseline · curve_sweep · mobility_factorial · bc_aim 이
   전부 여기서 파생. mission_eval 에 standby/extra_cfg pass-through +
   M4Runner._m4 동일 배관 (학습/평가가 같은 dict 로 세계 생성).
2. **[2] A4a manifest + A5 fresh-state 가드** — build_m4_env 가 실수신
   입력+합성 cfg 에서 resolved contract(hash) 를 스택에 부착, mission_eval
   반환→summary.json 자동 기록. `manifest_mismatch(allow=선언축)` 비교기.
   ckpt 옆 contract_{tag}.json 저장, restore 는 hash 불일치·manifest 부재
   시 거부. tests/test_contract_parity.py 7종 (torch 1종 서버 검증 대기).
3. **[3] B1 CWC semantics trace** — docs/66 r0. **신규 발견: CWC 술어 2개**
   (보상측 = 종료 tick 순간 근접 / 지표측 = 에피소드 접촉 집합, 행 12
   divergence). 같은 tick KILL 은 항상 HARD_KILL 라벨 → CWC 에 destructive
   혼입 경로 없음 → 비준 분기 1 해당, R(CWC)=R(NET) 제안이 정당. (a) 채택
   시 두-술어 divergence 는 보상측에서 무해화.

주의 기록:

- legacy 실측(docs/45 곡선·docs/47 hold 0/297·docs/51 factorial)은 구계약
  산물 — 재실행 수치와 병치 시 한정 병기 (각 _kw 에 주석).
- P40 테스트 3종은 서브셋 실행 시 torch 부재로 fail 하는 것처럼 보임 —
  전체 스위트에선 test_a3e 의 스텁 경유로 정상 (conftest 문서화된 구조).

다음 = **[4] B3 truth table 비준 (Hyunjun, docs/66 §5 요청 4건)** → 승인 후
B2(RewardSpec.terminal 명시 분기) → B4(행 단위 executable test) → [5] C/D
hygiene → [6] P92. push 는 수동 (git push 권한 차단).
