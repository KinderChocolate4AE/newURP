# A-3d 구현 하네스 — bank 생성기 + reset_to 속도 주입 (Opus 4.8 작업 지시서)

> 발주: docs/09 (nn)·docs/17 v0.1 (V-1~V-6 비준됨). 이 문서는 **docs/17 §1~§2를 코드로 옮기는 작업 지시서**다. 스펙 충돌 시 docs/17이 정본. 담당 범위 = 아래 산출물 A·B·테스트만. **트레이너(teacher-gate/ΔΦ)·config는 범위 밖** (후속 담당자 몫).

## 0. 절대 불변 (위반 = 작업 무효)

1. **frozen 파일 수정 금지**: `shepherd/env.py`, `shepherd/game/*`, `shepherd/agents/*`, `shepherd/train/make_env.py`, `configs/m2_l2_train.yaml`.
2. **판정 경로 접촉 금지**: `eval_heldout_m3.py`, `analyze_gate_a.py`, judgment m3 파라미터, `m3_eval_bundle`의 frozen 경로.
3. 기존 공개 함수 시그니처 변경 금지 (`spawn_bank.spawn_from/verify_t0/load_t0` 포함 — A-3d bank는 별도 로더를 쓰므로 건드릴 필요 없음).
4. **커밋 금지** — 산출물 = 파일 + 테스트 로그 + 구현 노트(md). 커밋·push는 검수 후 발주자가.
5. docs/ 수정 금지.

## 1. 선행 독해 (순서대로)

`docs/17_a3d_sbe_design.md`(정본 스펙) → `shepherd/train/spawn_bank.py`(스타일·APEX 상수) → `shepherd/env_m3.py`의 `reset_to`(주입 지점) → `shepherd/scripts/a3c_recoverability_oracle.py`(**kinematics 복제·scripted 공격자 호출·union 평가의 재사용 가능 예시** — `roll()`/`ev_state()`) → `results/a3_robust_bank.json`(witness 스키마) → `shepherd/sim/analytic.py`(적분기 의미론: v′=clip(v+aΔt); p′=p+v′Δt — **속도 갱신 후 위치**).

상수(m2_l2_train.yaml과 일치 필수): dt 0.05, a_lim_max 30, limiter_v_max 80, kill_radius 2.0, repel_margin 1.0, θ 0.9, 링 = 중심 [8,0,0]·r 5.0·슬롯 4개(`make_env.py의 _ring(4, c, r)`와 동일 각도 배치 — 재현해서 anchor로 사용, import 말고 복제 후 주석으로 출처 명기).

## 2. 산출물 A — `shepherd/scripts/a3d_sbe_bank.py`

**목적**: robust witness 3본에서 t−k 스폰 합성 (docs/17 §1) + 4조건 검증 게이트 통과분만 `results/a3d_sbe_bank.json`에 수록.

절차 (witness × k ∈ {1,2,4,8} × draw 12):
1. **리미터 도착 프로파일**: 슬롯 i의 anchor = 링 자리 i. 방향 u_i = unit(L*_i − anchor_i)에 ±15° 콘 지터(rng). v0 ~ U[0.3, 0.8]×(30·k·dt) — 구성상 |a| = v0/(k·dt) ≤ 24 < 30 assert. **이산 감속열**: a_i = −(v0/(k·dt))·u_i 상수, v_j = v0·(1−j/k)·u_i. 시작 상태(t−k): vel = v0·u_i, pos = L*_i − Σ_{j=1..k} v_j·dt (적분기 의미론 그대로 합산 — 폐형식 유도 후 **반드시 전방 롤로 확인**, 잔차는 시작 pos에 1회 가산 보정 허용).
2. **공격자**: t−k pos = [x*+v*·k·dt, 0, 0], vel = [−v*, 0, 0]. 전방 검증은 `scripted_adversary_action`(committed=False, v_nominal=**v\*** 핀, repel_margin 1.0, ω 8.0) k스텝 롤. tol: 위치 5cm·속도 2%. 미달 시 x 오프셋 1D 슈팅 ≤ 3회.
3. **repel 사전검사**: 롤 전 구간에서 공격자-각 리미터 거리 > kill_radius×1.2. 위반 → 방향 재추첨(≤10회, 소진 시 해당 draw 폐기 카운트).
4. **검증 게이트 (수록 조건, 全 충족)**: ① 결합 전방 롤(리미터 데모 가속 + scripted 공격자)이 t=0에 witness 상태 재현 (리미터 pos 5cm·vel 0.1m/s, 공격자 tol 상동) ② t=0 상태 clean (witness의 union_seed로 `ev_state`) ③ robust: fresh seeds 7..16 (10개)에서 clean 빈도 ≥ 0.9 ④ 데모 전 스텝 |v| ≤ 72 (=0.9·v_max)·|a| ≤ 24. 게이트 결과를 엔트리에 기록.
5. **출력 스키마**: `{"meta": {constants, tol, seeds, generated_per_cell, kept_per_cell}, "entries": [{"witness": src, "k": int, "draw": int, "spawn": {"limiters": 4×3, "limiter_v": 4×3, "att_p": 3, "att_v": 3, "att_speed": float}, "demo_accels": k×4×3, "verify": {"roll_err_m": f, "clean_t0": b, "robust_frac": f}}]}`.
6. CLI: `--bank results/a3_robust_bank.json --out results/a3d_sbe_bank.json --witness N --k K --draws 12` — **45초 제한 환경 대비 witness·k 단위 분할 실행 + 기존 out 파일 merge** (a3c oracle의 merge 패턴 복제). numpy-only, torch 금지.
7. 마지막 print: cell별 `kept/generated` 표 + 총 수록 수. **전멸 cell은 경고**(설계 무효 신호 — 발주자 보고 사항).

## 3. 산출물 B — `env_m3.py` `reset_to` 확장 (최소 diff)

- spawn dict의 **optional** `"limiter_v"` (4,3): 있으면 `a.v = row.copy()`, 없으면 현행 zeros 유지. shape 검증 + docstring 한 줄 갱신. **그 외 어떤 줄도 변경 금지** (diff = 수 줄이어야 함).

## 4. 테스트 — `tests/test_a3d_bank.py` (t-free, pytest)

① 이산 도착 수학: 합성 1건을 순수 kinematics로 전방 롤 → t=0 리미터 pos/vel tol 재현 ② env-레벨: `reset_to`(limiter_v 포함) 후 backend `.v` 반영 + limiter_v 미지정 시 zeros ③ t=0 clean 재현 1건 (witness seed, env 경유) ④ 게이트 드롭: tol 위반 인위 케이스가 수록 거부되는지 ⑤ 스키마: 생성 JSON 로드·필수 키 존재 ⑥ **회귀**: `tests/test_a3_reverse.py` 17개 + `test_env_m3.py` green 유지 (touched 파일이 env_m3.py이므로 필수).

## 5. 실행·보고 (완료 기준)

1. `python -m py_compile` 대상 2파일. 2. 신규 테스트 + 회귀 스위트 실행 로그. 3. bank 스모크: witness 1 × k∈{1,2} × draws 4 실행 → kept/generated 출력 첨부 (**kept 0이면 중단하고 보고** — 스펙 재협의 사항). 4. 구현 노트 md 1장: 폐형식 유도(이산 합), 슈팅 수렴 통계, 게이트 탈락 사유 분포, 남긴 TODO. **파일 위치**: 코드/테스트는 리포 경로 그대로, 노트는 리포 밖 산출물 폴더.

## 부록 — 환경 주의 (해당 시)

Cowork 세션 마운트에서 작업한다면: **Edit 툴로 리포 파일 수정 금지**(torn-write 이력) — 파일 전체를 heredoc/스크립트로 기록 후 md5 2회 재독 검증. Claude Code(Windows 로컬)라면 표준 편집 무방. pytest는 `-p no:cacheprovider` 권장. torch 불필요(전부 numpy).
