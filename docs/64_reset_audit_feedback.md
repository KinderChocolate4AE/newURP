# 64 — 리셋 전 전수 감사 종합 피드백 (Task 1·2·3) + 3자 리뷰 의뢰

**2026-08-08 · HEAD 0e94111 (감사 시작 f5c75b6 → 도중 P94 GREEN 2커밋 유입) ·
원천 = `artifacts/audits/` 7파일 (보고서 3 + registry tsv 3 + 종합 1).
이 감사 주간의 코드/문서 수정 0건 · 삭제 0건 — 본 문서는 진단·피드백이며,
docs/61 은 동결 상태 그대로다 (r2 비준, f4fa6bf).
★ 리뷰 6 판정 도착 (2026-08-08) — 판정 로그·통합 실행 큐 = `docs/65`.
본 문서 §9 의 큐는 docs/65 §8 로 대체됐다.**

---

## 0. 문서 지위와 리뷰 스코프

- 목적: MARL 재개 전 리셋 시점에서, **기존 연구의 claim·학습 신호·코드 기반이
  실제로 어디까지 서 있는지**를 전수 감사한 결과를 3자 리뷰어가 판정 가능한
  형태로 정리한다.
- 리뷰어에게 요청하는 것 = §8 의 판정 7건. **새 실험 설계·threat 재튜닝·
  docs/61 수정 제안은 스코프 밖** (docs/61 r2 는 비준·동결, 핸드오프 §3·§6).
- 배경 규율 (이미 잠김 — 재론 대상 아님): P95 실패 = TRAIN taxonomy 실패
  (MARL 실패 아님) · docs/63 결정 항목의 baseline 튜닝 사용 금지 · 3단계 분리
  서사 (P88 exists → P94 matters naturally → MARL exploits).

## 1. 감사 범위·방법 (요약)

| Task | 대상 | 산출물 |
|---|---|---|
| 1 | claim ↔ evidence ↔ code 전수 (claim 30 + gap 5) | `claim_evidence_code_audit.md` + `claim_registry.tsv` |
| 2 | reward/COMA/legacy 의존 — gradient 도달 경로 추적 | `reward_coma_dependency_audit.md` + `learning_signal_dependencies.tsv` |
| 3 | dead code/zombie flag/unreachable branch (스크립트 134 + 모듈 + config) | `dead_code_zombie_audit.md` + `code_liveness_registry.tsv` |

방법 한계 (리뷰어 인지 사항): 정적 참조 그래프 + grep + 코드 열람 중심.
동적 실행은 provenance pytest 1회 (508 passed / 1 failed = 알려진 로컬 cp949
산물 / 61 skipped = torch 부재 — 기대치와 정확히 일치, 회귀 신호 없음).
감사 도중 동시 세션이 P94 GREEN 커밋 2개를 push 했고 (23:48), 판정식 커밋
(f5c75b6)이 결과 커밋(6dccf93)에 선행함은 git 이력으로 확인했다 —
사전등록 규율 준수.

## 2. 총평

- **판정식 코어는 건강하다.** capture rule(env.py:320) · spent_fail(env.py:356) ·
  boxed R4 SPLIT · R1 swept+NK veto+Pk · R2 억제 · repel_margin=1.0 ·
  angular-gap +z tie-break 전부 문서 서술과 코드가 일치. docs/52 이후 문서는
  철회·강등·허용/금지 문장 규율이 일관 적용돼 과장 scan hit 가 2건뿐이다.
- **위험은 코어가 아니라 두 곳에 있다**: (i) 정정이 본문 한 곳에만 반영되고
  병렬 문구가 살아남은 문서 잔존물 (§4), (ii) **학습·평가 스택이 v2/v3 측정
  사슬과 다른 계약 위에서 돈다**는 구조적 균열 (§5). 후자가 이번 감사의
  최대 발견이다.
- claim 판정 집계: **ACTIVE 19 · DOWNGRADED 5 · RETRACTED 3 · PENDING 2 ·
  CONFLICT(gap) 4.**

## 3. MARL 재개 전 blocker 5 (종합)

| # | blocker | 근거 위치 | 성질 |
|---|---|---|---|
| 1 | 학습기·legacy 스윕이 R1/R2 이전 **구계약**으로 돈다 — `contact_resolver`/`miss_terminates` 미전달 → 기본 off. docs/53-54 가 그 구계약을 "구현 비정합"으로 판정했다. v2/v3 측정 사슬은 전부 F-flags on → 학습과 측정의 세계가 갈라짐 | train_m4.py:448-454 · sweep_m4 | 재배선 |
| 2 | `mission_eval` 이 `standby`/`extra_cfg` 를 버린다 → 평가 경로 전체(evaluate/sweep/curve/factorial)가 V3-FULL 을 평가 못 하고 **조용히 legacy 기하로** 돈다 | m4_env.py:123-125 | 재배선 |
| 3 | `CAPTURE_WITH_CONTACT` 종말보상 = 0 (else 분기) ↔ 지표는 비손실 성공 계수. v3 는 limiter 근접 설계라 발생 빈도 상승 위험 | env_sys.py:464 ↔ m4_env.py:147 | **계약 결정** (§8-Q2) |
| 4 | docs/61 TRAIN 분포 100% 미배선 — `draw_threat_v3`/`episode_len_train=1100` grep 히트 0. P92·P93·P95 미실행, docs/63 미작성 | — | 기존 큐 (계획대로) |
| 5 | docs/50:183 — 철회된 "하드킬로 도망간다"(정정 9)가 **논문 후보 문장**에 잔존 | docs/50 §5(B) | 문서 정정 |

## 4. 문서 잔존물·모순 (Task 1)

1. ★ **G04** docs/50 §1.3(철회 기록) ↔ 같은 문서 §5(B):183(철회 문구 잔존) —
   문서-내 모순. 이대로 논문에 들어가면 데이터에 없는 하드킬(0건)을 주장.
2. **G05** docs/48 §5 "발사 규칙은 특권적" ↔ §10.2 "틀렸다" — 원문 미표시.
3. **G03** docs/56·58 의 `CONTACT_NEUTRALIZATION` 은 env terminal 라벨이 아님
   (실제 = `HARD_KILL` + source="contact") — 분석 카테고리로만 사용해야.
4. **G02** contact→engagement rename: 선언(docs/57 §2.1) 후 미실행.
5. **G01** `capture_thresh` docstring ↔ 실제 rule 불일치 (DEAD, params 등재
   유지 — env 동결이라 수정 대신 문서화).
6. params.py 레지스트리 오기 4건 — 최위험 = `scripted.limiter_pressure`
   "env ignores idx3" (M4 에선 커밋 비트로 재사용, 서술이 현행과 반대).
   그 외 `attitude.e_net_init`(변경이 조용히 무효) · `headline_u0`/`coma_u0` ·
   `ViabilitySpec.seed`.
7. 스코프 규율 2건: R1/R2 기본 off → "환경이 handoff 를 갖는다" 는 항상
   F-flags arm 한정 / knife-edge·NK 42/42 인용 시 "legacy small-scale regime"
   한정 필수 (docs/59 재스코프).

## 5. 학습 신호 실태 (Task 2)

- gradient 도달 항 = **7개**: Δv_shot(headline) · λ1·clean · −λ2·wasted ·
  −λ3·근접 재계수 · terminal(라벨별) · −c_lim·소모증분 · (aux 한정) BC cosine.
  전부 단일 공유 J → GAE 1회 → 두 actor 가 같은 advantage 소비.
- **COMA 는 전 M4 런에서 gradient 미도달** — `coma_mix` 가 l2_mappo.yaml 에
  없어 기본 0.0. `coma_D` 는 계산·로그 전용. **`train/coma_D_mean` 을 학습
  신호로 인용한 과거 해석이 있다면 전부 오독이다.** (DORMANT_BY_CONFIG;
  나중에 켤 경우 standby 이동 기준점에 대한 counterfactual 의미 재선언 필요.)
- **Δv_shot 의 구조적 한계**: 기준선 = 고정 limiter_p0 (standby 활성 팔에선
  에피소드별 랜덤 standby 자세). limiter 이동이 attacker 궤적을 바꾸는
  **route 채널의 이득은 Δv_shot 에 즉시 반영되지 않는다** (다음 상태 v_shot
  경유만). "MARL 이 shaping 채널을 이용하는가" 검정 해석에 직결 (§8-Q3).
- 이중 벌점 구조: 같은 물리 사건에 c_lim(이벤트 1회) + λ3(상태 재계수,
  R1 on/off 에 따라 지속 시간 상이)가 다른 시간 구조로 부과.
- RunningNorm 누적 무망각 + v2/v3 스케일 (24→300+, len 80→1100) →
  **legacy ckpt/norm 재사용 금지.**
- 위협 반응성 축 (route_gain·sense_range 등)은 **비관측** — 정책엔 암묵
  randomization. 결과 해석 시 명시 필수.

## 6. 코드 기반 실태 (Task 3)

- **SAFE_DELETE 0건.** ZERO-REF 3건 (plot 스크립트)은 참조되는 probe 의 그림
  원천 가능성으로 UNCERTAIN 보존 — "import 0 → 삭제 가능" 금지 규율 준수.
  ARCHIVE_ONLY ~70 (c1 클러스터 49 + docs/52~58 증거 스크립트 10 등).
- 예상 밖 legacy-live (blocker 1·2 와 동일 뿌리 외):
  - `n_segments=1` 낙관 신호가 rollout_gif + m2_default.yaml 렌더 루트에 잔존
    — GIF 를 증거로 읽지 말 것.
  - rollout_gif 인라인 규칙이 `_zero_commit` 미사용 — M4 스택 재사용 시
    스텝 1 전원 하드킬 커밋 트랩.
  - `judge="point_mass"` dataclass 기본값 — 직접 생성 시 조용히 ablation judge.
  - train_m4.py:125 동어반복 — `--limiter-policy` 는 hold 외 선택 불가.
- duplicate 6군 (보고만): 기저선 규칙 인라인 복제 6곳 (실발산 2건 기보유) ·
  hand-rolled rollout 루프 17곳 · **라벨 재구현 4곳 의미 상이** (signal_audit
  의 `NET_CAPTURE` 는 contact 미검사 — 정본과 이름 충돌) · M4 kwargs ~18곳 ·
  SHA-256 유도 4변형 · Wilson 잔여.

## 7. 죽은 claim / 허용 문장 (인용 규율 — 즉시 발효)

**재인용 금지 (근거 소멸)**: "LL 이 하드킬로 도피" (정정 9 — 하드킬 0건) ·
"성형 채널 구조적 무력" (docs/52 철회) · "발사 시점 kinetic 창 닫힘"/"post-fire
환원"/"비단조=이질성" (리뷰 4 철회) · "슬루 병목"·"자기운동 기전" (docs/51
자체 기각) · chord 0.033 논법·"15/17 강건" (docs/54) · "탈출구 봉쇄 = 성공"
(boxed ≠ 포획) · "H_fin 검정됐다" (SL 구조적 0 — 검정 불가였음).

**허용 문장 (강도 상한)** — 전체 표는 `RESET_WEEKLY_AUDIT_SUMMARY.md` §D:

| claim | 허용 상한 |
|---|---|
| knife-edge | "robust-clean **certificate** 가 legacy small-scale regime 의 witness 전부에서 수 cm 폭" — 전체 방어 상한 아님 |
| NK 42/42 | "해당 7판·해당 budget 에서 NK 밖 contact 미발견" (legacy 한정) |
| LS≈SS | "한 운용점·한 알고리즘·발사 정상 조건에서 편대 학습 순이득 미측정" |
| P94 GREEN | "자연 상태 route causal channel 의 측정 가능한 인과효과 실증 — 학습 이용 여부는 MARL+대조의 몫" |
| pre-fire ep35 | "**NK-밖 engagement opportunity 의 첫 witness** (1/7, 무반응 A2·privileged·budget 한정)" [C8 하향 2026-08-08 — "창(window)" 은 시간 지속 함의라 금지, docs/65 §4] |
| V2 | "primary 재현 FAIL / 기전 귀속 PASS" 2줄 고정 |
| C2R 1.000 | "Pk=1 semantics check" (성능 아님) |
| R2 handoff | "전환 기제 검증 / scripted 폴백 무력화 미실증 (0/7)" + F-flags 한정 |

## 8. 3자 리뷰어에게 요청하는 판정 7건

1. **blocker 목록의 완전성·순서** (§3): 학습 재개 전 차단 목록으로 5건이
   충분한가? 누락된 유형 (예: 관측/정규화 축, seed 규율)이 blocker 로 승격돼야
   하는 것이 있는가?
2. **CAPTURE_WITH_CONTACT 계약** (§3-3): (a) 별도 terminal 값 선언 vs
   (b) "접촉 동반 포획 = 무보상 중립" 명시 비준. 어느 쪽이 docs/61 의
   lexicographic endpoint (Δ_net primary) 및 w_kill sweep 축과 정합적인가?
   감사는 어느 쪽도 권고하지 않았다 — 결정 근거를 요청한다.
3. **Δv_shot 의 route 채널 비반영** (§5): 이 보상 구조에서 MARL gain 이
   나왔을 때 / 안 나왔을 때 각각 "shaping 채널 이용" 해석에 생기는 위협은
   무엇인가? docs/61 동결 하에서 **문서화만으로** 해소 가능한 범위와,
   불가능하다면 어느 단계 (MARL 후 귀속 분석)로 미뤄야 하는지 판정 요청.
4. **COMA 오독 정정 범위** (§5): coma_mix=0 실태 확인에 따라, 과거 기록 중
   `coma_D` 로그를 근거로 쓴 서술의 정정 필요 범위는? (등록부 상 학습 신호
   인용은 미발견 — 로그 어휘 자체의 위험 판정을 요청.)
5. **허용 문장 표의 강도** (§7): 과소·과대 판정이 있는가? 특히 P94 GREEN
   허용 문장이 3단계 분리 서사와 정합적인가?
6. **감사 방법의 맹점**: 정적 참조 그래프 + grep 중심 감사가 구조적으로
   놓치는 유형 (동적 dispatch, 데이터 의존 분기, config 조합 폭발)에 대해
   추가 감사가 필요한 곳이 있는가?
7. **재발 방지 규율**: G04/G05 형 잔존 (정정이 본문 한 곳에만 반영)의 구조적
   원인에 대해, "철회 시 전 문서 grep 의무" 수준의 경량 규율로 충분한가?

## 9. 수정·결정 큐 (다음 세션 — 새 실험 설계 없음)

1. **고칠 것**: docs/50:183 (+48 §5 주석) 정정 → train_m4/sweep_m4 R1/R2
   플래그 노출 + mission_eval standby/extra_cfg 전달 → params.py 오기 4건.
2. **결정할 계약** (Hyunjun 트랙): CAPTURE_WITH_CONTACT terminal (§8-Q2) ·
   docs/63 scripted baseline 동결 작성·비준 · engagement rename 시점 ·
   (선택) coma_mix 재선언 — 켤 계획이 있을 때만.
3. **그 뒤 기존 prereg 큐**: P92 (draw_threat_v3 배선) → P93 (침투 보존,
   1100 확정 겸) → P95 (paired reactivity audit) → docs/61 §6 평가 프로토콜
   → MARL.

---

*원천 보고서가 정본이다 — 본 문서와 원천이 다르면 원천 우선:
`claim_evidence_code_audit.md` · `reward_coma_dependency_audit.md` ·
`dead_code_zombie_audit.md` · `RESET_WEEKLY_AUDIT_SUMMARY.md`.*
