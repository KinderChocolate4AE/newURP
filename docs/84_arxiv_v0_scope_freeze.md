# 84 — arXiv v0 scope freeze (결정 기록)

**결정 (2026-08-16)**: **E1e 판정이 나온 시점을 arXiv v0 의 science freeze 로 잡는다.**
이후 실험(E4-2 / 새 geometry 축 / T2 / MARL)은 v0 와 **병렬인 다음 research branch** 이며
v0 본문에 들어가지 않는다.

**근거**: E4-2/T2 까지 기다리면 논문 질문이 *"net feasibility / modality gap"* 에서
*"cooperative controller design / MARL"* 까지 퍼져 v0 가 흐려진다. 지금은 콘텐츠를 더
만드는 단계가 아니라 **잘라내는 단계**다.

---

## 1. Spine (한 문장)

> **Physical interception does not imply non-destructive capturability.**

그 아래 **두 층만** 붙인다.

1. **modality-level operating-regime separation**
2. **why the net modality has a narrow commit-state feasibility region**

E1e 가 확인되면 ② 가 닫힌다 — 단순 lateral bound 가 아니라 **두 competing geometric
constraint 와 interior optimum** 이 된다. **E1e 가 반증돼도 그대로 쓴다** — 그 경우
analytic bound 를 *conservative / partial characterization* 으로 낮춘다.

---

## 2. 넣을 것 / 뺄 것 (동결)

| 판정 | 항목 | 역할 |
|---|---|---|
| **넣음** | analytic outer bound + modality gap (χ · one-sided optimistic bound · T1 net curve vs physical curve · **E2-B sham-net null**) | 결과 ①. sham-net 이 censoring 설명을 제거 |
| **넣음** | practical commit geometry (**E1d → E1e**) | E1e 확인 시 **핵심 mechanism figure** 로 승격 |
| **넣음** | strong physical baseline correction (**E4-1c δ=0.125**) | *"physical baseline 이 약해서 만들어진 gap 아닌가"* 반론 차단. **physical controller 를 개선해도 두 modality 가 같아지지 않는다** 는 robustness 역할 |
| **압축** | E1/E1b slew attribution falsification | 긴 실험 섹션이 아니라 *"what does **not** explain the boundary"* 한 덩어리 |
| **아주 짧게** | Gate 7 | *"post-commit 0.30 s 안에서 non-prepositioned limiter 가 geometry 를 바꾸기는 어렵다 → future cooperation 은 pre-commit 이어야 한다"* 한 단락. Gate 10/11 전체는 본문에서 뺀다 |
| **appendix 또는 삭제** | **E3 · E4-1 · E4-1b** | 연구를 만드는 데는 핵심이었으나 v0 thesis 에는 controller-debugging history 다. 필요하면 appendix "physical baseline validation" 으로 요약 |
| **뺌** | **E4-2 · T2 · MARL** | 다음 논문의 cooperative-control half |
| **뺌** | **R4 measurement-debug history** | 본문에서 사라진다. 최종 correct metric 과 protocol 만 쓴다. reproducibility appendix / artifact history 에는 남는다 |

### 2.1 R4 canonical pointer (본문 대신 reproducibility appendix 로)

정정 이력(`0.043 → 0.190`)은 본문/appendix **어디에도 쓰지 않는다**. 최종 값만 쓴다:

$$P(d_{m actual}\le r_{m contact})=0.190,\qquad P(d_{m oracle}\le r_{m contact})=0.883$$

숫자 변경사를 설명하면 독자 시선이 science 대신 debugging history 로 간다.
대신 reproducibility appendix 에 **한 문장**:

> **For E3 proximity-derived diagnostics, `results/e3_oracle_r4.json` is the canonical
> artifact. The pre-R4 `results/e3_oracle.json` is retained for provenance only; all
> reported proximity statistics use the R4-corrected measurement contract.**

repo 쪽에서는 논문 문장 하나에 의존하지 않고 **`results/README.md`** 에 기계가 읽을 수
있는 canonical pointer 를 둔다 (전 실험 + `lead_time_r4` no-op 함정 포함). 네 구분을
명시한다: old artifact **삭제 안 함** · old **proximity metrics** superseded ·
old **outcome labels invalidated 아님** · `*_r4` 가 proximity metric 의 canonical source.

Conclusion 마무리 문장:

> *"The present work characterizes Map A; whether cooperative pre-commit control can
> transport states into the favorable set is left to subsequent work."*

---

## 3. 본문 구성 (동결)

1. **Introduction** — physical interception 과 non-destructive capture 를 같은
   "interception success" 로 보는 것이 왜 부족한가 → modality question
2. **Related Work** — 아래 3 소절만
3. **Problem Formulation** — 4 limiter + 1 net capturer · terminal geometry · τ, ρ, χ ·
   T0/T1 scope · one-sided assumptions
4. **Feasibility Analysis** — analytic optimistic outer bound. E1e 확인 시
   lateral / far-edge competing constraint 와 `ax*`
5. **Experimental Protocol** — T1 fixed configuration · threat distribution ·
   frozen contracts · physical vs net outcome 정의
6. **Results** — **첫 그림이 반드시 modality curves** → analytic/practical boundary →
   E2-B sham-net counterfactual → E1e geometric validation
7. **Robustness / What the gap is not** — strong pursuit δ=0.125 · slew counterfactual (짧게)
8. **Discussion** — closed-loop outcome gap ≠ state-wise set inclusion ·
   post-commit cooperation limitation · pre-commit state shaping 이 다음 질문
9. **Conclusion**

---

## 4. 문헌 전략 (동결)

**본문 1 ~ 1.5 페이지 · 핵심 20 ~ 30 편.** 50 편짜리 C-UAS survey 로 키우지 않는다.
Introduction 에서 5 ~ 8 편, Related Work 는 **세 소절**:

**Net-based aerial interception → Cooperative pursuit/capture → What is missing: feasibility
of the terminal modality**

### 반드시 연결할 cluster 4 개

| # | cluster | 우리 역할 |
|---|---|---|
| 1 | **airborne / net-based C-UAS 실물 시스템** — Pliska et al. (agile non-cooperative UAV 대상 mid-air net interception guidance + 실기체), UAV Hunter (airborne tether-net + detection/tracking), 2026 LiDAR–vision 기반 autonomous drone-on-drone net capture, UAV-borne flexible-net dynamics + 실험 검증 | *"net capture 라는 modality 자체가 비현실적"* 이라는 인상을 **주지 않기 위해** 반드시 짚는다 |
| 2 | **cooperative / multi-UAV net capture** — 2019 cooperative UAVs carrying a net, 최근 multi-UAV tethered net + multibody dynamics + MAPPO | *"여러 UAV 로 net capture 한다"* 자체를 **novelty 로 내세우지 않는다** |
| 3 | **flexible-net mechanics / terminal hardware** — 2025 flexible-net capture system deployment parameter optimization, 2026 net dynamics + 실험 검증 | 경계 긋기: *"우리는 net mechanics 가 아니라 **commit-state feasibility** 를 다룬다"* |
| 4 | **multi-UAV pursuit / MARL** — UAV dynamics 포함 pursuit-evasion MARL, multi-role cooperative pursuit, rogue-drone cooperative search/track | **3 ~ 5 편으로 끊는다**: *"cooperative pursuit / role learning 은 존재하지만 본 논문의 질문은 learned policy performance 가 아니라 terminal modality feasibility"* |

### Positioning

net 문헌은 hardware · perception/tracking · guidance · net dynamics · multi-UAV capture
**구현**에, pursuit/MARL 문헌은 capture/search/control **성능**에 초점이 있다. 따라서 우리
positioning 은

> *"우리가 최초로 net 을 쏜다 / 협력한다"* 가 **아니라**,
> **terminal state 가 modality 별로 어떻게 다른 feasibility 를 갖는지 계측하고 경계를 분해한다**

이는 **targeted search 에 기반한 positioning 이며 "세계 최초" 주장으로 쓰지 않는다.**

### 금지

generic 한 *"드론 위협 증가 · jamming · radar …"* 문헌을 두 페이지 깔지 않는다. contribution
과 거리가 멀다.

---

## 5. 실행 순서

1. **E1e 실행 → 판정** (`47268e1`, 회귀 5/5 통과 · 서버 ~50 분)
2. **arXiv v0 science freeze** ← 여기서 잠금
3. v0 집필 (§3 구성 · §4 문헌)
4. 새 geometry 축 선정 + E4-2 합동 동결 = **병렬 branch**. 성공하면 v0.1 / AIAA 에서
   *"feasibility characterization → cooperative state shaping"* 으로 확장. **실패해도 v0
   핵심은 흔들리지 않는다.**

---

*연관: 사전등록/판정 정본 = `docs/83` · 순서 규율 = `docs/81` · 미팅 브리핑 = `docs/82` ·
claim registry = `artifacts/audits/claim_registry.tsv`*
