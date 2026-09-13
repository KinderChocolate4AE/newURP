# 2026-09-14b — **메커니즘 branch 종료(CLOSED).** 본선 복귀: docs/97 → B2 → stop rule → training contract → MARL

- **지위**: 종료 선언 + 증거 사슬 통합. 새 실험 없음.
- **판정**: `101-A` 가 메커니즘 branch 의 **정당한 종료점**이다. 여기서 더 파면 연구의
  중심이 "협력 기하" 에서 "CEM 이 scripted A2 의 불연속을 어떻게 exploit 하는가" 로
  옮겨간다 — 그건 본 논문의 중심이 아니다.

---

## 1. 이 branch 가 원래 맡은 역할

R2b privileged CEM 은 **deployable solution 이 아니다.** 애초 역할은 attainment benchmark:

> **이 world 에서 limiter control 로 얻을 수 있는 capture opportunity 가 실재하는가?**

그 뒤 probe 들의 역할은 그 CEM 을 해부해서:

> **그 opportunity 가 어떤 cooperative mechanism 을 통해 생기는가?**

**둘 다 수행됐다.**

## 2. 닫힌 것 (증거 사슬)

| 카드 | 결론 |
|---|---|
| R2b C arm | joint limiter plan 으로 **capture attainable** (constructive witness) |
| dep-probe | 성공의 일부는 **same-plan single-limiter reduction 으로 재현 안 됨** (46/140) |
| `95-BR2` geometry probe | 그 효과는 **FIRE 직전 instantaneous closure 가 아님** (pre-fire 채널 98% 비활성, ΔV=0, D_i=0) |
| `96-BR1` steering probe | **이른 limiter 지령을 철회하면 capture 가 깨짐** (98% → 41%, 비단조 0/46) → trajectory-mediated |
| `98-B` margin audit | judge boundary artifact **아님** (witness ×4 에도 여유 11.2 cm 불변) · 단순 **위치 평행이동으로 설명 안 됨** |
| `99-P` velocity decomp | AUTH-LOST 를 가르는 것은 **속력**(20×), 위치는 못 가름(0.76) |
| `99-X` | 섭동 자체는 세 그룹 **동일**, 갈리는 것은 증폭 여부 |
| `CJ-audit` | 가속차가 **전부 route 항** (residual 0.002), `committed`/jink **기각** |
| **`101-A`** | **near-tie argmax separatrix 확정** — GO gate 오차 `0.00e+00` |

### 최종 메커니즘 (sealed A2 안에서)

$$ 11\,\text{cm} \rightarrow 0.013\,\text{rad} \rightarrow
   \boxed{\delta_g \approx 0.021\,\text{rad near-tie 교차}} \rightarrow 107°\ \text{route 전환} $$
$$ \rightarrow 16.1\,\text{m/s}^2 \rightarrow 0.84\,\text{m/s} \rightarrow 42\,\text{mm}
   \rightarrow \text{capture 술어 상실} $$

**각 단계가 앞 단계 크기에서 계산되고 관측과 맞는다.**

> **논문용 한 문장**: sealed A2 에서 limiter 들은 FIRE 순간 escape set 을 직접 봉쇄한 것이
> 아니라, **earlier trajectory interaction 을 통해 반응형 표적의 behavioral route choice 를
> 바꾸고** downstream capture state 를 형성했다.
>
> **반드시 병기**: 이 구체적 argmax-transition 메커니즘은 **A2 policy-specific** 이며
> physics-only 일반 법칙으로 주장하지 않는다.

## 3. 예상 밖의 소득 — 실용적으로 가장 큰 것

$$ \boxed{\ \text{현행 M2 instantaneous dense reward 가 실제 성공 mechanism 에 blind 하다}\ } $$

성공 plan **46/46 이 `delta_headline` 을 pre-fire 구간에서 전혀 움직이지 않았다**
(`95-BR2`). 그런데 그 plan 들의 이른 구간 지령이 결과를 결정한다 (`96-BR1`).
의심의 핵심은 계수 크기가 아니라 **credit assignment 의 causal horizon** 이다.

⇒ **이번 우회의 정당화**: MARL 진입 전에 **잘못된 reward 를 봉인하는 것을 막았다.**
training contract 설계에 직접 들어간다.

## 4. DEFER — ① "왜 near-tie 였나"

> **DEFERRED — CEM enrichment near A2 route-choice boundaries** (docs/97 §B.8 에 등재)

질문: $P(\text{near-tie} \mid C\text{-success})$ 가 baseline / random / rule 성공 상태보다
높은가. **메커니즘 존재 주장에 필요하지 않다** — `101-A` 는 이미 "이 성공 사례들에서 작은
기하 섭동이 A2 의 behavioral decision boundary 를 넘겼다" 를 말한다. CEM 이 *의도적으로*
그쪽을 선호했는지는 다음 claim 의 전제가 아니다.

계속 파면 CEM optimization landscape · near-tie prevalence · random 대비 enrichment ·
search bias 로 새 카드가 연쇄한다. **reviewer-defense card 로 보관.**

## 5. 논문 spine (이제 보인다)

1. **물리적 capture regime** — $(\chi, \eta, \lambda)$ 에서 capture boundary 정량화
2. **단순 rule controller 는 못 얻는 영역** — R2b B null
3. **그런데 privileged joint search 는 얻음** — constructive cooperative opportunity
4. **그 opportunity 의 정체** — ← **오늘 끝낸 chain (§2)**
5. **deployable controller 가 그것을 배울 수 있는가** — **B2 / MARL 본게임**
6. **더 강한 adaptive attacker 에서도 cooperative gain 이 남는가** — PFSP

## 6. 연구 위치 (한 줄)

- 시작: *"협력 limiter 가 capture set 을 shaping 할 수 있는가?"*
- **지금**: *"그럴 수 있다" 는 constructive witness 를 얻었고, sealed A2 에서 그 shaping 이
  **어떻게** 발생했는지까지 설명했다.*
- 남은 진짜 질문: $\boxed{\text{deployable closed-loop policy 가 이 opportunity 를 회수할 수 있는가?}}$

## 7. 복귀 순서 (확정)

$$ \text{docs/97 결재} \rightarrow \textbf{mechanism branch CLOSED}
   \rightarrow \text{B2 scripted} \rightarrow \text{stop rule}
   \rightarrow \text{training contract} \rightarrow \text{MARL} $$

repo-R2/R3 는 docs/97 뒤 hygiene. ① 은 DEFER.

**본 노트 이후 메커니즘 카드를 새로 열지 않는다** — 열려면 위 본선 게이트 중 하나가
그것을 요구할 때만.
