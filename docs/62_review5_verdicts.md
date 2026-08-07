# 62 — 외부 리뷰 5 판정 로그 (위협 v3 + docs/61) + 반영

**2026-08-07 · 프롬프트 = `review_prompt_threat_v3.md` · 대상 = docs/60 전 과정 + docs/61 r0**

---

## 1. 판정표 (리뷰어)

| 주장 | 판정 | 핵심 이유 |
|---|---|---|
| 1. P88 = 방향성 causal channel 개통 | **조건부 유지** | 코드 수준 존재는 확립. 단 P88 은 **controllability test 이지 natural-state occupancy test 가 아님** — 자연 상태 이용 가능성 미확인 |
| 2. P91b 교정 = 비소급 | **조건부 유지** | 5조건(§3) 안에서 허용. 기록은 "v1 FAIL → 교정 → v2 PASS" 분리 유지, 병합 서술 금지. **이 선례를 threat tuning 면허로 쓰지 않는다** |
| 3. budget 공유 = 계약 | **조건부 유지** | saturation 은 자연스러움. 단 **route_gain 입력값을 반응 강도로 읽으면 안 됨** — 셀별 realized reactivity 순서 확인 필요 |
| 4. V6 = sanity | **조건부 유지** | non-pathology sanity 로만. label invariance ≠ mechanism irrelevance — 구분은 paired ablation 의 몫 |
| 5. angular-gap 충분성 | **조건부 유지** | proof-of-concept 로 충분. 단 결론은 "angular-gap family 한정" — **CPA OOD 가 headline 의 핵심 falsifier** |
| 6. docs/61 최소가정·판정 충분 | **기각** | 9셀 균등 = "최소 가정" 아님 (→ balanced design distribution 재명명) · nominal-중심 설계 인정 · E[J]∧최악셀 판정 게이밍 가능 (2위 취약 셀) · OOD ≠ 일반화 인증서 |
| 7. 미실시 항목 학습 후 이월 | **기각** | 위험 순위: ①route paired ablation ②scripted baseline 동결 ③A2 상속값 명시 ④수직(스코프 한정으로 방어 가능) ⑤detection ⑥slowdown |

**총평 채택**: P87/89/90/91 은 engineering gates (구현 불변식 검증 — green 이
정상). 과학적 gate 는 P88 하나였고, 그것도 "존재" 까지만. **남은 질문 =
"그 channel 이 자연 상태에서 충분히 존재해 MARL 이 실제로 이용할 수 있는가."**

**최위험 미검증 가정 (리뷰어 지정)**: P88 에서 존재가 확인된 channel 이
자연 발생 상태분포에서 충분한 빈도·크기로 작동해 mission-level shaping
signal 이 된다는 가정. 틀리면 P88 은 artificial manipulation 으로 남고,
이후 MARL gain 이 나와도 speed/spawn/초기기하 효과와 분리 불가.

## 2. 허용/금지 문장 (즉시 발효)

- 허용: *"v3 에서는 limiter geometry 가 attacker action 을 방향성 있게
  변화시키는 causal channel 이 구현·검증됐다."*
- 금지 (P94 green 전): *"MARL 이 shepherding 을 학습할 수 있는 충분한
  신호가 확보됐다"* · "학습 가능한 shepherding channel".
- 금지 (영구): "TRAIN 범위가 nominal 설계와 독립" (V6-비의존만 주장 가능 —
  nominal-centered design 임은 인정) · "OOD 통과 = 암기 아님 증명"
  (OOD 는 반례 탐색 장치).

## 3. P91b 류 교정의 허용 경계 (리뷰어 5조건 — 규율로 등재)

```
1. gate 가 downstream 과학 결과 전에 실패했다
2. 원인이 의도된 계약의 구현 오류로 식별된다
3. 수정이 연구 가설·성공 기준·성능 목표를 바꾸지 않는다
4. 실패 결과와 수정 시점이 보존된다 (v1 FAIL / v2 PASS 분리 기록)
5. 영향받는 gate 를 재실행한다
```
성능 결과를 본 뒤 attacker behavior 를 고치는 것은 이 논리로 정당화 불가.

## 4. 동결 전 수정 3개 → docs/61 r1 반영 (§ 매핑)

| 수정 | 반영 |
|---|---|
| 1. natural-state route paired ablation gate (**학습 전 필수**) | docs/61 §5 **P94** 신설 |
| 2. "balanced experimental design distribution" 재명명 + realized-reactivity audit (weak<med<strong 순서 확인) | docs/61 §0·§1 재명명 + §5 **P95** 신설 |
| 3. headline lexicographic 판정 (primary endpoint + noninferiority margin/CI) + scripted baseline 결과 전 동결 | docs/61 §6 재작성 + baseline 동결 문서 예약 (docs/63) |

부수 반영: A2 상속값 = "fixed inherited nuisance parameters" 명시 + OOD/
sensitivity 등재 (§2) · 수직 위협 = 명시적 scope limitation (§4) ·
9셀 전체 결과 벡터 의무 공개 (§6).
