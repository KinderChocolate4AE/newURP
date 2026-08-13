# Claim ↔ Evidence ↔ Code 전수 감사 (Task 1)

**2026-08-07 · 리셋 전 주간 감사 세션. 이 문서는 진단이며, 어떤 문서/코드도 수정하지 않았다.**
등록부: `artifacts/audits/claim_registry.tsv` (C001~C030 + GAP G01~G05).

---

## 0. Provenance

```
감사 시작 HEAD    f5c75b612b15a2ffbe696ee6d5f950734f3b172a  (feat/scale-up-v2)
감사 중 HEAD 이동  → 0e941110601a761b9600136b2430ddeabf296933
                  (동시 진행 세션이 23:48 에 2커밋 push:
                   6dccf93 "P94 GREEN" — docs/61 §5.1 + results/threat_v3_p94.json
                   0e94111 temp_research_note 기록)
dirty            tracked 변경 0. untracked 23개 전부 results/*.log·*.json
                  (p2prime_ep*.log 7, scale_v2_baseline* 16) — 결과 부속 로그,
                  코드/문서 아님
pytest -q        로컬 (win32, torch 미설치): 백그라운드 실행 — 완료 시 §9 에 기록.
                  기대치 (memory): torch 부재로 ~61 skip + fire_audit 1 fail
```

★ **주의**: 감사 도중 HEAD 가 움직였다는 것 자체가 provenance 사실이다. C028(P94
GREEN)은 감사 시작 시점에는 존재하지 않았고, 판정식 커밋(f5c75b6)이 결과 커밋
(6dccf93)에 선행함은 git 이력으로 확인했다 — 사전등록 규율은 지켜졌다.

---

## 1. Executive summary

- **claim 30건 + claim/code gap 5건** 등록. 판정: ACTIVE 19 · DOWNGRADED 5 ·
  RETRACTED 3 · PENDING 2 · CONFLICT 4(전부 GAP 행, 경미 2 포함).
- **핵심 판정식은 문서와 코드가 일치한다.** capture rule(`env.py:320`),
  spent_fail(`env.py:356`), boxed R4 SPLIT(`viability.py:186-201`), R1 swept
  resolver + NK veto + Pk(`env_sys.py:407-452`), R2 억제(`env_sys.py:304-316`),
  P84 의 구조 원인(`env.py:346 repel_margin=1.0`), angular-gap +z tie-break
  (`attacker_ladder.py:251`) 전부 문서 서술 그대로 실재.
- **가장 위험한 잔존물 1건**: docs/50 §5(B) 183행 — 정정 9 로 철회된 "하드킬로
  도망간다" 가 **논문 후보 문장** 안에 살아 있다 (G04). 같은 문서 §1.3 이 철회를
  기록하고 §5 가 그 문구를 유지하는 문서-내 모순.
- **문서 위생은 전반적으로 매우 좋다.** 철회는 원문 보존 + 취소선/정정 블록으로
  기록되고, 리뷰 3·4·5 의 허용/금지 문장이 그대로 반영돼 있다. 발견된 문제는
  대부분 "정정이 본문 한 곳에만 반영되고 다른 절의 병렬 문구가 남은" 유형.
- **계약 스코프 주의 2건**: (i) R1/R2 는 기본 off — "환경은 handoff/접촉 무력화를
  갖는다" 는 문장은 항상 F-flags arm 한정으로 써야 한다 (C012). (ii) docs/59 가
  legacy 전 결과를 "legacy small-scale regime 한정" 으로 재스코프했으므로,
  knife-edge(C009)·NK 42/42(C019~21) 를 인용할 때 이 한정이 빠지면 과장이 된다.

---

## 2. ACTIVE claims (요지 — 상세는 registry)

| ID | 한 줄 | 근거 강도 |
|---|---|---|
| C003 | 결손은 조준축 (관측 충분 AUC 1.000 · 발사 비트 무죄 · 개방률 0.61x/0.23x) | intervention |
| C004 | BCa 24.5% 회복 · 게이트↔성적 양방향 동조 (매개 관측) | intervention (n=5 시드) |
| C006 | SHAPING 111/122 접촉 도달 가능 (낙관적 필요조건) | necessary condition |
| C007 | SHAPING 라벨 ≠ 난도 축 (a_lim=0.35·a_att 결합) | 코드 확인 |
| C008 | 성공 = 선택적 압축; boxed ≠ 포획 | 코드 계약 |
| C011 | v_soft ≠ 확률 | 코드 계약 |
| C012 | miss 즉시 종료 = 구현 비정합 → R2 개정 (기본 off) | 코드 계약 |
| C013 | boxed 병목 = resolver 부재 (A 1.000 → C2 0.235) | intervention |
| C014 | V2 = FAIL/PASS 2줄 (수치 대역 밖 / 기전 귀속 성립) | exact + 귀속 |
| C015 | 무력화 1.000 = Pk=1 semantics check | semantics |
| C017 | Pk sweep = sanity + 민감도 (재시도 +0.12~0.13, 상수 아님) | sanity |
| C018 | R1 event = engagement opportunity (판정 B, provenance 3/3) | provenance |
| C019 | miss 7판·budget 한정 회복 증거 없음 (11/11 NK veto) | budget-한정 probe |
| C021 | P2′: "proxy 가 NK-안 유도" 대안 반증 (1축) | adversarial refutation |
| C022 | pre-fire ep35 NK-밖 무력화 1/7 — 캠페인 최초 실증 | witness (1건) |
| C023 | legacy A2: 0.75m 밖 인과효과 0 → shepherding 검정 불가였다 | intervention + control |
| C024 | v2: hold 기저선 불변 — 기존 결론은 regime 한정 | baseline 관측 |
| C026 | v3 게이트 P87~P91 green (P91b FAIL→교정→PASS 분리 기록) | engineering gates |
| C028 | ★ P94 GREEN — 자연 상태 route 인과효과 실증 (감사 중 도착) | paired intervention |
| C030 | R2 전환 기제 검증 / scripted 폴백 무력화 0/7 미실증 | 기제 + 음성 |

## 3. RETRACTED claims — 잔존 여부

| ID | 철회된 주장 | 잔존 위치 | 판정 |
|---|---|---|---|
| C002 | "LL 이 하드킬로 도피" (0/0 퇴화값 오독) | ★ **docs/50:183 §5(B)** — 논문 후보 문장에 그대로 | **잔존 — 유일한 위험 잔존.** 다음 세션 수정 대상 |
| C005 | "성형 채널 구조적 무력" | `review_prompt_shaping_channel.md:48` | historical artifact (리뷰 프롬프트 원문) — 수정 불요, 인용 금지만 |
| C016 일부 | chord 오차 상한 0.033 논법 · "3건 철회 기준" 게이트 지위 | docs/54 §3.2 안에서 자체 철회·강등 완료 | 잔존 없음 |
| (docs/57) | "창이 닫힘"·"pre-fire 환원"·"비단조=이질성" | docs/57 §4 에 취소선+철회 표기 완료 | 잔존 없음 |
| (docs/51) | §8.3 슬루 기전·§8.5 조준 속도 병목 | §9 에서 자체 기각 기록 완료 | 잔존 없음 |

## 4. DOWNGRADED claims

| ID | 강등 전 → 후 |
|---|---|
| C001 | "어느 역할도 못 넘음" → "LL·LS 한정 + 지표 자체가 무판별(SS 도 0/297)" |
| C009 | "clean 배치는 수 cm 폭뿐" → "robust-clean **certificate** 가 frontier 의 가장 보수적 끝점에서 knife-edge (legacy regime 한정)" |
| C016 | "15/17 강건 (오차상한)" → "두 보간 규약 판정 일치 16/17 (민감도 결과)" |
| C020 | "발사 시점에 창이 닫혀 있었다" → "planner·proxy·budget 과 구분 불가" (docs/57 §4.3 문장 고정) |
| C027 | "vertical escape 실재 (z-지배 0.81)" → "route 의 z **요청** 수치 — 실현 기전 증거 아님" |

## 5. PENDING claims

- **C029** docs/61 TRAIN 분포 r1: Hyunjun 비준 대기. P92(분포 배선)·P93(침투
  보존)·P95(realized-reactivity) 미실행, docs/63(scripted baseline 동결) 미작성.
  P94 만 green (C028).
- **G02** contact→engagement rename chore: 선언(docs/57 §2.1) 후 미실행.

## 6. Claim/Code semantic gaps

| ID | gap | 코드 | 상태 |
|---|---|---|---|
| G01 | env.py docstring "captured iff v_soft ≥ capture_thresh" ↔ 실제 rule = (not boxed) ∧ v_worst≥1 at fire. `capture_thresh` 는 저장만 되고 **안 읽힘** | env.py:84-89 vs :320; params.py:220 DEAD 등재 | 문서화 완료 (env 동결이라 수정 대신 등재) — 유지 |
| G02 | "contact" 코드 키 ↔ 비준 의미 "engagement" | env_sys.py 키 전반 (docstring 에는 의미 고정됨 :410-415) | rename chore 미실행 |
| G03 | docs/56·58 의 `CONTACT_NEUTRALIZATION` 은 env terminal 라벨이 아니다 — contact kill 은 `HARD_KILL` + `CommitRecord.source="contact"` | mission_rollout.py:55 LABELS | 표기 통일 필요 (분석 카테고리로만) |
| G04 | docs/50 §5(B) 잔존 철회 문구 | — | ★ 수정 대상 |
| G05 | docs/48 §5 "특권적" ↔ §10.2 정정 — §5 에 정정 표시 없음 | obs[60] | 주석 권장 |

추가로 확인한 **일치** 항목 (gap 아님): SPENT_FAIL 종말보상 0 중립(docs/26 ↔
`RewardSpec.terminal` else 0.0) · c_lim 증분 부과(P3 수정 ↔ env_sys:379-385) ·
PARK_POSITION 60 근거(env_sys:62-79) · fire gate 단일화(FSM:85) · v2 overlay
비트동일 구조(scale_v2.py) · P94 판정식 커밋(f5c75b6)이 결과(6dccf93)에 선행.

## 7. 문서 간 contradictions

1. ★ docs/50 §1.3(철회) ↔ docs/50 §5(B):183(잔존) — 같은 문서 안 모순 (G04).
2. docs/48 §5 ↔ §10.2 (특권 정보) — 자체 정정 있으나 원문 미표시 (G05).
3. docs/53 §1.1 "handoff 구조적으로 불가능" — 작성 시점(R2 이전)에는 참,
   현재는 R2 flag 로 해소됨. docs/53 은 결정 메모라 시제 명확 — 모순 아님,
   단 인용 시 "R2 이전 진단" 임을 병기.
4. docs/56 §6.2 라벨 어휘 ↔ mission_rollout LABELS (G03).
5. docs/59 재스코프("legacy 한정") ↔ docs/52~58 의 legacy 결과 서술 — 모순이
   아니라 **스코프 계층**이나, 52~58 을 단독 인용하면 한정이 빠진다. 인용 규율로만
   해소 가능.

## 8. 자동 과장 표현 scan 결과

"물리적으로/구조적으로 불가능·증명·보장·확률·상한" 계열 전수 grep 중, **현재
evidence strength 와 어긋나는 hit 는 2건뿐**:

- docs/50:183 (G04 — 위 참조)
- docs/43:20 "포위를 **실패로** 채점" — docs/53 §4.4 이후 boxed 는 "실패" 가
  아니라 "비-clean, 미확정" 이다. 서술은 코드(clean_crossed 게이트)와 일치하나
  "실패" 단어가 구 계약 어휘.

나머지 hit 는 전부 (i) 철회 문서 자신의 인용, (ii) 금지 규율 문장, (iii) 실측
포획률 곡선(롤아웃 빈도 — v_soft 아님) 로 적법. docs/52 이후의 문서들은 오히려
과장 방지 규율(오류 13 동형, budget 한정, 두-줄 판정)이 일관 적용돼 있다.

## 9. pytest (provenance)

```
1 failed, 508 passed, 61 skipped  (659 s, win32 로컬)
FAILED tests/test_fire_audit.py::test_p63c_probe_positive_control_and_threshold
  (subprocess cp949 UnicodeDecodeError — 알려진 로컬 환경 산물, memory local-env-quirks)
61 skipped = torch 미설치
```

기대치와 정확히 일치 — **코드 회귀 신호 없음.** 서버 기준 정상 회귀는
docs/54: 474~476 passed / 0 failed.

## 10. 논문 집필 시 절대 쓰면 안 되는 문장 Top 10

1. "발사가 망가지면 정책이 하드킬로 도피한다" (정정 9 철회 — 하드킬 0건)
2. "성형 채널은 구조적으로/물리적으로 무력·불가능하다" (docs/52 철회)
3. "clean capture 가 가능한 배치는 수 cm 폭뿐이다" (robust-clean certificate 한정 + legacy regime 한정 없이)
4. "v_shot_soft = 포획 확률" (union 비확률 표본)
5. "어느 역할을 학습시켜도 SS 를 못 넘었다" (H_fin 검정 불가 + 지표 무판별)
6. "V2 통과" (FAIL/PASS 2줄 분리 의무)
7. "boxed 상태의 무력화율은 1.000 이다" (Pk=1 semantics check 를 성능으로)
8. "발사 시점에 kinetic 창이 이미 닫혀 있었다" / "post-fire 접촉 창의 부재를 인증했다" (budget 한정)
9. "MARL 이 shepherding 을 학습할 수 있는 충분한 신호가 확보됐다" (P94 green 은 channel 실재까지 — 학습 이용은 미검)
10. "SHAPING 구간은 더 어려운 구간이다" (라벨은 난도 축이 아님)

## 11. 현재 가장 강하게 방어 가능한 핵심 claim Top 10

1. 학습 열세의 인과 사슬: 역할 귀속 → 발사 → **조준** → 보상 기울기 부재 (C003, 각 링크가 측정)
2. 게이트 개방률 ↔ 성적의 양방향 동조 — 매개 관측 (C004)
3. boxed 병목 = 접촉 resolver 부재 (A 1.000 / C1 0.941 / C2 0.235, C013)
4. net-miss 즉시 종료는 비준 설계 대비 구현 비정합이었다 (코드+비준 기록 대조, C012)
5. legacy A2 에서 0.75m 밖 limiter 인과효과 0 — positive control 포함 (C023)
6. v3 에서 defender geometry → attacker action 방향성 causal channel 구현·검증 (P88, C026)
7. ★ 자연 상태에서 그 channel 의 인과효과 실증 — P94 46/50 발산, label 변화 7/50 (C028)
8. robust-clean certificate 는 legacy regime 에서 knife-edge (witness+exact replay, 재해석 포함, C009)
9. pre-fire 준비로 NK-밖 kinetic 창이 열릴 수 있다 — ep35 실증 1건 (C022)
10. SHAPING 라벨 ≠ 난도 축 (a_lim∝a_att 결합, C007)

---

*Task 1 규율 준수: 이 감사 중 문서·코드를 수정하지 않았다. G04/G05 등 수정
대상은 다음 세션 큐로만 남긴다.*
