# RESET 전 주간 감사 종합 (Task 1 + 2 + 3)

**2026-08-08 · HEAD 0e94111 (감사 시작 f5c75b6 → 도중 P94 GREEN 2커밋 유입).**
개별 보고서: `claim_evidence_code_audit.md` · `reward_coma_dependency_audit.md` ·
`dead_code_zombie_audit.md` (+ registry tsv 3종). 이번 세션 코드/문서 수정 0건,
삭제 0건.

---

## A. MARL 재개 전 반드시 해결할 blocker (5)

1. **학습·legacy-평가 계열이 R1/R2 이전 구계약으로 돈다**
   - 근거: `train_m4.build_specs` (train_m4.py:448-454) 와
     `sweep_m4.measure_baseline` 이 `contact_resolver`/`miss_terminates` 를
     전달하지 않음 → 기본 False/True (= 접촉 무력화 없음 · miss 즉시 종료).
   - 현재 영향: v2/v3 측정 사슬(전부 F-flags on)과 학습이 다른 세계 —
     이대로 학습을 돌리면 무엇을 배웠는지 비준 계약 기준으로 해석 불능.
   - 왜 blocker: docs/53-54 가 그 구계약을 "구현 비정합" 으로 판정했다.
2. **`mission_eval` 이 `standby`·`extra_cfg` 를 버린다** (m4_env.py:123-125)
   - 평가 경로(train_m4.evaluate/sweep_m4/curve_sweep/mobility_factorial)가
     V3-FULL 을 평가 못 하고, v3 attacker 를 줘도 조용히 legacy 기하로 돈다.
3. **`CAPTURE_WITH_CONTACT` 종말보상 = 0 (else 분기) ↔ 지표는 비손실 성공**
   - env_sys.py:464 → RewardSpec.terminal 명시 분기 없음; m4_env._split:147 은
     성공 계수. v3 는 limiter 근접 설계라 발생 빈도 상승 위험. **계약 결정
     필요** (별도 terminal 선언 or 무보상 중립 명시 비준) — 결정 전 학습 금지.
4. **docs/61 TRAIN 분포 100% 미배선 + 비준 대기** — `draw_threat_v3`/
   `episode_len_train=1100` grep 히트 0. P92(배선)·P93(침투 보존)·P95
   (realized-reactivity) 미실행, docs/63(scripted baseline 동결) 미작성.
5. **docs/50:183 — 철회된 "하드킬로 도망간다" 가 논문 후보 문장에 잔존**
   (정정 9 위반 상태). 보고서/논문 집필 전 문서 수정 필수.

## B. 논문 서사상 가장 위험한 살아있는 모순 (10)

1. docs/50 §1.3(철회) ↔ §5(B):183(잔존) — 같은 문서 내 하드킬 모순 (G04).
2. docs/48 §5 "발사 규칙은 특권적" ↔ §10.2 "틀렸다" — 원문 미표시 (G05).
3. `CAPTURE_WITH_CONTACT`: 보상 0 ↔ 지표 성공 (A-3).
4. docs/56·58 의 `CONTACT_NEUTRALIZATION` 은 env 라벨이 아님 (실제 =
   HARD_KILL + source="contact") — 어휘 불일치 (G03).
5. params.py:276 `scripted.limiter_pressure` "env ignores idx3" — M4 에선
   커밋 비트로 재사용됨. 레지스트리 서술이 현행과 반대.
6. params.py 소비자 서술 오기 3건: `attitude.e_net_init`(변경이 조용히 무효),
   `headline_u0`/`coma_u0`, `ViabilitySpec.seed`.
7. `signal_audit` 의 인라인 라벨 `NET_CAPTURE` 가 contact 미검사 — 정본과
   이름 충돌·의미 상이 (duplicate 감사 §4).
8. 학습기 로그 `train/coma_D_mean` — COMA 는 coma_mix=0 이라 학습 신호가
   아니었음. 학습 신호로 인용하면 오독.
9. C001 인용 시 "SHAPING 지표는 SS 도 0/297 (무판별)" 병기 누락 위험.
10. legacy ↔ v2 ↔ v3 수치를 같은 표에 올리는 것 (P78 동형 금지) — regime
    한정 문구 탈락이 곧 과장.

## C. 완전히 죽은 claim (다음 세션에서 재인용 금지)

- "LL 이 하드킬로 도피 / 비손실 0.80 = 하드킬" (정정 9 — 하드킬 0건).
- "성형 채널이 구조적으로/물리적으로 무력·불가능" (docs/52 철회).
- "발사 시점에 kinetic 창이 이미 닫혀 있었다" · "post-fire 로 환원" ·
  "비단조 = 상태별 이질성" (리뷰 4 철회).
- "슬루 속도가 병목" (docs/51 §9.2 — ω∞ 500/500 동일로 기각).
- "이동 해악의 기전 = 자기운동→시선각속도" (docs/51 §9.3 기각. 기전 미상).
- chord 오차 상한 0.033 논법 · "15/17 강건" (docs/54 — 적분기 가정 위반).
- "모든 탈출구 봉쇄 = 성공" (철회 2 — boxed_in 은 포획이 아님).
- docs/52 §4.2 구 2a 의 SHAPING 19/23 (Block 1 무효화 — union 재실행 수치로만).
- "H_fin 이 검정됐다" (SL 은 구조적 0 — 검정 불가였음).

## D. 살아있지만 강도가 제한된 claim (허용 문장 포함)

| claim | 허용 문장 |
|---|---|
| knife-edge | "robust-clean **certificate** 가 legacy small-scale regime 에서 발견된 witness 전부에서 수 cm 폭" — frontier 의 보수적 끝점, 전체 방어 상한 아님 |
| NK 42/42 | "해당 7판·해당 budget 에서 NK 밖 contact 를 찾지 못했다" (legacy regime 한정) |
| LS≈SS | "한 운용점·한 알고리즘·발사 정상 조건에서 편대 학습의 순이득이 측정되지 않았다" |
| P94 GREEN | "자연 상태에서 route causal channel 의 측정 가능한 인과효과 실증 — 학습이 그것을 이용하는지는 MARL+static/active 대조의 몫" |
| pre-fire ep35 | "pre-fire 준비로 NK-밖 창이 열릴 수 있음을 보인 첫 사례 (1/7, 무반응 A2·privileged·budget 한정)" |
| V2 | "primary 수치 재현 FAIL / 사전등록 기전 귀속 PASS" 2줄 고정 |
| C2R 1.000 | "Pk=1 contact-event semantics check" (성능 아님) |
| R2 handoff | "국면 전환 기제는 검증, scripted 폴백 무력화는 미실증 (0/7)" + "기본값은 여전히 즉시 종료 — F-flags arm 한정" |

## E. SAFE_DELETE 완료 목록 — **없음 (0건)**

ZERO-REF 3건(c1_moveA0_plot · c1_persistence_plot · n1_temporal_plot)은 그림
원천 가능성 때문에 UNCERTAIN 으로 보존. ARCHIVE_ONLY(증거 재현) ~70건은 삭제
금지로 분류·구분 완료 — `code_liveness_registry.tsv` 참조. 삭제 커밋 없음.

## F. 예상 밖으로 아직 LIVE 인 legacy path (가장 중요)

1. 학습기(train_m4)·legacy 스윕(sweep_m4) = **R1/R2 off 구계약** (A-1).
2. mission_eval = standby/extra_cfg 유실 → 평가는 legacy 기하 고정 (A-2).
3. `n_segments=1` 낙관 신호 = rollout_gif + m2_default.yaml 렌더 루트에서만
   생존 (episode_len 70·theta 0.8 플롯 포함) — GIF 를 증거로 읽지 말 것.
4. rollout_gif 인라인 기저선 규칙이 `_zero_commit` 미사용 — M4 스택 재사용 시
   스텝 1 전원 하드킬 커밋 트랩.
5. `judge="point_mass"` dataclass 기본값 — 직접 생성 시 조용히 ablation judge.
6. train_m4.py:125 동어반복 — `--limiter-policy` 는 hold 외 선택 불가.
7. l2_mappo.yaml `randomize:`/`env_config:` 는 M4 경로에서 조용히 무시됨.

## G. 다음 세션 권장 순서 (새 실험 설계 없음)

1. **반드시 고칠 blocker**
   1. docs/50:183 (+48 §5 주석) 문서 정정 — 철회 반영.
   2. 재배선: train_m4/sweep_m4 에 R1/R2 플래그 노출 + mission_eval 에
      standby/extra_cfg 전달 + (비준 후) P92 `draw_threat_v3` 배선.
   3. params.py 레지스트리 정정 4건 (limiter_pressure · e_net ·
      headline_u0/coma_u0 · ViabilitySpec.seed).
2. **반드시 결정할 계약** (Hyunjun 비준 트랙)
   1. `CAPTURE_WITH_CONTACT` terminal 값 (선언 or 중립 명시).
   2. docs/61 TRAIN 분포 r1 비준 (§7 체크리스트) + docs/63 scripted baseline
      동결 작성.
   3. contact→engagement rename chore 실행 시점.
   4. (선택) COMA cf 의 의미 재선언 — coma_mix 를 켤 계획이 있을 때만.
3. **그 뒤 실행 가능한 기존 prereg queue**
   1. P92 (분포 배선 게이트) → P93 (침투 보존) → P95 (realized-reactivity).
   2. docs/61 §6 평가 프로토콜 (hold vs scripted vs MARL, paired CRN,
      lexicographic endpoint) — scripted baseline 은 docs/63 동결 후.
   3. 그 뒤에만 MARL 학습.
