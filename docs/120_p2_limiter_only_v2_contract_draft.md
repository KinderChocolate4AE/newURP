# 120 — P2 limiter-only 학습 v2 계약 (**봉인 2026-10-02** — manifest `8ba6d0df420d6631`)

- **봉인**: 2026-10-02 사용자 승인 ("ㄱㄱ" — §6 제안값 그대로). 정본 수치 =
  `artifacts/p2_limiter/manifest.json` (`scripts/p2_limiter_manifest.py`).
- **결재 결과**: ① mix = 6 config 균등 (route × jink, sense 30 · λ REF 고정)
  ② `P2_POSITIVE` 문턱 = 양 seed 각각 pooled ΔN ≥ +34/1,680 + 고결합 2 config
  ΔN ≥ 0 ③ 학습 131,072 step × seed {0, 1} (b5 hyperparameter 그대로 — NO_SELECTION
  유지) ④ c5 arm 포함 (보고 전용) ⑤ 평가 config 당 280 유지 (arm 당 1,680).
- **실행기**: `scripts/p2_limiter.py` — b5 runner 상속 + mix 주입
  (`sha256("p2-mix", seed, ep)` 균등), neutral-init·finisher-freeze 를 INVALID
  조건으로 검증, 전제조건 (COMPLETE_P1 + P2_PREMISE_SUPPORTED + ROW9_FLIP_NOISE)
  를 실행 시 강제.

- **일자**: 2026-10-02 · **상위**: docs/117 P2 · docs/89 r5 · **선행 충족**:
  P1a `COMPLETE_P1` + `P2_PREMISE_SUPPORTED` (spread 127) · plant pre-check 종결
  (`ROW9_FLIP_NOISE` — point-mass 세계 선언 깨끗함, 2026-10-02b).

## 1. 질문

**선언된 공격자 결합-이득 mix 위에서, limiter-only PPO (capturer scripted 고정) 가
hold limiter 를 일관되게 개선하는가 — 그리고 개선 폭이 공격자의 limiter-반응
결합 이득 (route_gain) 에 어떻게 의존하는가.**

b5 (2026-09-24, 무신호) 와의 차이는 **공격자 축 하나**다: b5 는 공칭 단일 config,
P2 는 P1a 지도에서 선정한 mix. 가설 (docs/117): limiter 조형의 학습 가치는
공격자가 limiter 를 보고 반응하는 정도 (결합 이득) 에 의존한다. **양·음 어느
결과든 foundation 곡선** ("공격자 행동 수위 → limiter 조형 가치") 이 된다 —
따라서 판정 명칭은 STOP 이 아니라 `P2_POSITIVE` / `P2_NULL` 이다 (INVALID 는 별도).

## 2. 세계·역할 (동결)

- **세계**: B0 v3 `5e7b5b486b9d8a4a`, point-mass (pre-check 종결 근거).
- **capturer**: **scripted launcher 고정**. F3 keeper 는 hold-limiter 세계의
  산물이라 c5/learned limiter 가 만드는 상태 분포에서 보증이 없다 — P2 에
  넣으면 "capturer 분포 이동" 교란이 limiter 효과와 섞인다 (RL2 교훈). F3 재평가는
  P2 종료 후 별도 계약.
- **공격자 mix (P1a 지도 기반, 선언 후 고정)**:
  route_gain {0.2, 0.5, 0.8} × jink {0, 0.6} = **6 config** (sense 30 고정 — ∞ 는
  30 과 중복, λ REF 고정 — null 축, bait 제외 — 미발동). 학습 중 episode 마다
  6 config 균등 추출 (선언 난수), 평가는 config 별 paired suite.

## 3. Arms

| arm | limiter | 용도 |
|---|---|---|
| hold | scripted hold | primary 대조 (H_illegal 0 구조) |
| c5 | scripted arc (B2 RULE_COOP) | reference rule (H_illegal 경향 보고용) |
| learned × seed {0, 1} | PPO (b5 계보: pilot hyperparameters · limiter neutral init · freeze_finisher · scripted 행동 log-prob 미포함) | 본 실험 |

## 4. 평가·판정 (결과 전 봉인)

- 평가: 6 config × 28 cell × 10 ep = **1,680 ep/arm**, 전 arm paired (fresh
  namespace). 학습과 평가 namespace 분리.
- **Primary (사전 등록)**: paired ΔN(learned − hold), seed 별·config 별.
  - `P2_POSITIVE`: 양 seed 에서 pooled ΔN > 0 **이고** 6 config 중 route 0.8
    (고결합) config 들에서 ΔN ≥ 0 — 방향성 요구는 고결합 쪽에만 둔다 (가설이
    예측하는 곳). 수치 문턱은 §6-②.
  - `P2_NULL`: 위 미충족. b5 와 합쳐 "limiter 조형 가치가 공격자 수위에 둔감"
    으로 기록 → docs/104 Track B 로 중심 이동 (docs/117 출구).
- **안전**: learned·hold pooled H_illegal == 0 (c5 는 보고만).
- **보고 전용 진단**: crossing (P1a 교훈: crossing 은 어차피 280/280 포화 —
  gate 금지), config 별 ΔN 곡선 (foundation 그림), 학습 곡선.
- **INVALID**: 계보·완주·pairing·예산·neutral-init 검증·freeze 검증 위반.

## 5. 학습 예산 (제안 — §6 결재)

b5 의 32,768 step 은 "더 긴 학습을 배제하지 않는다" 캐비앗이 있었다. 제안:
**seed 당 131,072 step (4×, rollout 512 × 256 update)**, checkpoint 매 16 update.
mix 학습이라 config 당 유효 노출이 1/6 인 점을 보정하는 증액이다. 서버 기준
b5 의 ~4 배 소요.

## 6. 결재 목록 (봉인 전 사용자 결정)

1. 공격자 mix 확정 (§2 — 6 config 균등. 대안: route 축만 3 config).
2. `P2_POSITIVE` 수치 문턱: pooled ΔN 의 최소 폭 (제안: 양 seed 각각 ΔN ≥ +34/1,680
   = +2%p — b5 노이즈 스케일 (±5/280 ≈ 1.8%p) 위).
3. 학습 예산 (§5 — 131,072 승인 또는 조정) · seed 수 (2 유지 vs 3).
4. c5 arm 포함 여부 (비용 1,680 ep — 포함 권장: foundation 그림의 rule 기준선).
5. 평가 episode 수 (config 당 280 유지 vs 축소).
