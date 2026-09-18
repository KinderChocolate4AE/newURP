# 2026-09-14c — B2 구현: 배선 완료, 그런데 봉인 문서가 **전제한 것 두 개가 실제로는 없었다**

지위: 구현 기록 (docs/102 는 봉인 — 건드리지 않음). 실행 전.
산출: `b2_manifest.py` · `b2_run.py` · `b2_forced_fire.py` · `b2_readout.py` ·
`tests/test_b2_contract.py` + `mission_rollout.py` 의 공용 배선 2 건.

---

## 1. 만든 것 (핸드오프 순서 그대로)

| # | 파일 | 역할 |
|---|---|---|
| 1 | `shepherd/scripts/b2_manifest.py` | 격자·arm·CRN·예산을 파일로 못박음. `manifest_hash 2f887776be47f538` · B0 v3 `5e7b5b486b9d8a4a` · 56 cell · 168 unit · 50,400 scenario · **100,800 ep** (docs/102 §2.1 과 일치) |
| 2 | `shepherd/scripts/b2_run.py` | manifest 소비 전용 러너. arm 은 limiter controller 만 바꾼다. incremental save · resume · `.done` marker · ntfy **실제 구현**, smoke 가 resume 까지 시험 |
| 3 | `shepherd/scripts/b2_forced_fire.py` | 별도 계정 (`diagnostic_forced_fire`) · 별도 디렉터리 · 별도 schema. 2-pass (축좌표 기록 → t\* 선택 → 강제 1 발) |
| 4 | `shepherd/scripts/b2_readout.py` | 집계가 일어나는 **유일한** 곳. raw count identity 를 원 카운트로 검사 |
| 5 | `tests/test_b2_contract.py` | 16 tests — manifest 불변식 · partition 경계 케이스 · arm pairing |

GO smoke (docs/102 §7): 1·2·3·4·5·7 = PASS (`b2_run --smoke`), 6 = PASS
(`b2_forced_fire --smoke`, 아래 §4). 성능 gate 는 넣지 않았다.

추가 안전장치 (합의): arm 쌍은 scenario id 일치 **+ 초기 world-state hash 일치**까지
검사한다. id 만 같고 초기화 경로가 갈리는 실수를 잡는다.

## 2. ⚠ 봉인 문서가 "이미 있다" 고 전제했지만 없던 것 — reference fallback

docs/102 §1 은 `reference fallback` 을 *"world 기본 (B0 v3 `mission.kinetic_fallback`),
양 arm 에서 동일하게 작동"* 이라 적었다. **코드에는 kill chain (contact → veto → Pk) 만
있었고 조종 전환이 없었다** — NET_SPENT 이후에도 limiter 는 arm 의 컨트롤러(hold/arc)를
계속 썼다. 즉 "PN takeover" 는 문서에만 있었다. (docs/95 런북이 geom-probe 의
resume 을 "코드에 있다고 가정" 했다가 틀린 것과 같은 계열.)

배선한 곳: `mission_rollout.run_episode(kinetic_fallback=...)` **한 곳** — 러너마다
적으면 arm 마다 다른 fallback 이 되어 "limiter control 만 다르다" 계약이 깨진다.
기본값 None = 기존 경로와 bit-identical.

**내가 고른 것 (검토 필요)**: `controller="intercept"` · `baseline_commit=True` —
단 **KINETIC 단계 한정**이고 NET 단계 commit 은 계속 off. 근거는 B0 v3 kill chain 문안이
`tau_kill` 을 명시한 것 (tau_kill 지연은 **commit 경로에만** 존재하고 contact resolver 는
즉시 해소한다). commit 을 끄면 소진 후 limiter 는 근접 접촉으로만 죽일 수 있어
P_U ≈ P_N 이 되고 secondary system metric 이 사실상 공허해진다. manifest `fallback`
필드가 이 배선의 유일한 정의원이다.

## 3. ⚠ partition 이 **조용히 틀릴 뻔한 지점** (실측으로 잡음)

s=901 RULE_COOP: `HARD_KILL`, net 미소진, 접촉 기록 0 → 초안 규칙으로는 **H_fb
(정당 fallback)** 로 분류됐다. 실제로는 NET_PRE 중의 kinetic kill = **H_illegal** 이다.

원인: 계약의 접촉 술어는 **이동 전** 상태 (B0 v3 `contact_semantics`, env.py
`limiter_loss` 와 동일) 인데, env 의 engagement resolver 는 **이동 전/후를 모두** 본다.
실측 그 판: pre 0.764 m > kill_radius 0.75 > post 0.501 m → resolver 만 접촉을 봤다.

수정: `partition_bin` 이 세 소스를 본다 — ① 계약 술어(이동 전 스캔) ② resolver 의
engagement event ③ "네트 미소진 상태의 kill" 안전망(commit 경로까지 덮음). 셋 중
하나라도 NET_PRE/NET_PENDING 이면 H_illegal. 단일 정의원은 `mission_rollout.partition_bin`
(`terminal_label` 옆).

> 오늘의 규율대로, 이건 내 계산끼리 대조해서가 아니라 **시뮬레이터가 실제로 쓴 값**
> (`info["contacts"]`, `net_spent_step`) 과 대조해서 잡혔다.

## 4. forced-fire 표본이 **비어 있을 가능성** (실행 전 경고)

smoke 로 돌린 60 ep (경계밴드 5 cell) 에서 **`FIRE = 0` 이 한 판도 없었다** (P(FIRE) = 1.000).
docs/102 §5 의 표본은 "boundary band 28 cell 에서 FIRE=0 으로 끝난 전 에피소드" 이므로,
primary 에서도 이 경향이면 **forced-fire 는 표본이 0 이 된다.**

- 그 자체가 §5.5 판독의 한 줄이다: P(FIRE) 가 낮지 않으므로 낮은 P(N) 은
  gate censoring 때문이 아니다 → **attainability/controller-limited** 쪽.
- 60 ep 은 경향이지 결론이 아니다. primary 가 정한다. 규칙은 바꾸지 않는다.
- 그래서 배선을 놀려두지 않기 위해 smoke 에 **`wiring_only` 경로**를 두었다: FIRE=0 판이
  없으면 발사했던 판을 pass 1 `fire_mode="never"` 로 돌려 같은 2-pass 기계를 시험한다
  (FIRE=0 판에서는 clean 과 never 가 동치이므로 기계가 같다). 레코드에
  `wiring_only=True` 로 못박아 진단 산출물과 섞이지 않는다.
  실측: t\*=31 (a_target 4.11, ax 4.03) · 강제발사 t\* 에서 정확히 발생 ·
  **개입 이전 궤적 bit-identical**.

## 5. docs/102 가 말하지 않아 **승계로 처리한 것** — jitter (검토 요망)

셀 안 scenario 추첨의 jitter 를 docs/102 가 명시하지 않았다. R2a Stage1/Stage2
(chi50 의 출처) · R2b Phase 1 이 전부 `draw_cell_jitter` (chi ±0.01 = lattice step
0.02 의 반폭, eta ±0.15) 를 썼으므로 **같은 규약을 승계**했다. 코드에 숨기지 않고
manifest `crn.jitter` 로 노출했다 — 고정 격자점으로 봉인하려면 그 값을 0 으로 두고
manifest 를 다시 찍으면 된다 (hash 가 바뀌므로 산출물이 섞이지 않는다).

## 6. 실행 순서

```
python -m shepherd.scripts.b2_manifest          # 이미 생성됨 (2f887776be47f538)
python -m shepherd.scripts.b2_run --smoke       # GO smoke 1~5,7
python -m shepherd.scripts.b2_run --run --shard K --n-shards N     # 랩서버 (100,800 ep)
python -m shepherd.scripts.b2_readout
python -m shepherd.scripts.b2_forced_fire --run --shard K --n-shards N   # primary 이후
python -m shepherd.scripts.b2_readout --forced-fire
```

로컬 실측 ≈ 4.3 s/scenario (2 arm) → 50,400 scenario ≈ **60 h 직렬**. 랩서버 샤딩 필수
(로컬 금지). `NTFY_TOPIC` 설정 시 시작/완료/중단 푸시.
