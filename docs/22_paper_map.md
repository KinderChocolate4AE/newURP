# 22 — 논문 수확 지도 (paper harvest map) — v0.2, 2026-07-19 (**지위: 참고 자료 전용** — §0-1 지휘 원칙이 본 문서 전 조항에 우선)

> **성격(v0.2 확정)**: 본 문서는 **수확 시점의 편집 기준**이다 — 연구 방향을 지배하지 않는다. 논문 절단·스코프 확정·프레이밍 결정은 **Hyunjun의 명시 지시로만** 이뤄진다. v0.1의 일부 조항(자동 배정·종결 실험·티어 중심 서술)은 §0-1 지휘 원칙으로 정정됨 — 본문에 [v0.2] 표기.
>
> **입력**: 업로드 권고안(paper_scope_recommendation, 2026-07-19) · docs/20 §6 · docs/12 §6 · 09 (ooo)~(qqq-1) · `URP/conference_targets_2026H2.md` · 벤ue 마감 웹 실측(2026-07-19, §4). **불변**: 판정 J·게이트 정의·seed 원장·2-모드 프로토콜·클레임 규율(A2-한정·제4병목 의무 보고·verify-before-cite).

---

## 0-1. 연구 지휘 원칙 (2026-07-19 Hyunjun 지시 — 본 문서 전체를 오버라이드)

**원 연구 질문(불변)**: *이종 다중 드론이 MARL을 통해 공격 드론을 협력적으로 양치기·성형하여, 포획 가능한 상태로 유도할 수 있는가?* 현 상태는 이 질문의 실패·후퇴가 아니라 **시스템 구조의 선명화**다: 협력 shaping은 MARL로 실제 학습됐고, shot은 learned일 필요가 없으며(rule-based terminal guard 분리가 더 자연스럽고 안정), hybrid 구조는 원 문제를 **더 적절하게 푸는 설계**다. d1에서 brake가 강한 것은 "현 국소 조건에서 MAPPO 필요성 미입증"이지 전체 연구의 진단-논문行 판정이 아니다.

1. **계속 개발이 기본**: 논문 절단·종결 = Hyunjun 별도 지시 시만. 학회 마감(국내·워크샵·RiTA 등)은 **당시 자산의 snapshot 수확 시점**일 뿐 — 스코프 확정·연구 종점·최종 프레이밍의 기준이 아니다. 마감 임박을 이유로 연구 질문을 축소하지 않는다.
2. **U-A/U-B = 콘텐츠 보관함, 라우터 아님**: "MARL = 방법 vs 연구 대상" 구분은 **나중에 실제로 자를 때의 편집 기준**이다. A3 공격자 등장이 자동 분리 사유가 아니다 — 결과가 "국소·반응형에선 단순 제어도 강하지만, 더 긴 회랑·전략적 공격자에선 협력 MARL의 적응성·역할 분화가 필요해진다"는 중심 서사를 강화하면 같은 연구축에서 계속 연결한다.
3. **진단-프레이밍 격하 금지**: 기본 프레이밍 = **"MARL 기반 협력 양치기·성형 시스템을 개발하는 과정에서, terminal action의 hybrid 분리와 local-to-mission reachability 병목을 규명하고 해결해 나가는 연구."** 양성 자산(비용-인지 협력 shaping 학습 · action-necessary predecessor에서의 capturability shaping 학습 · learned limiter + autonomous rule guard의 local capture · one-shot terminal vs continuous shaping의 올바른 구조 분리)이 중심이다. "왜 안 되는지 해부하는 진단 연구"는 회랑 부재·후속 개발 실패가 충분히 누적됐을 때만 선택 가능한 **fallback**이다.
4. **회랑 프로브 = 다음 개발 수를 고르는 전제 진단**(종결 실험 아님): 존재 → corridor-aware controller·curriculum·MARL 학습으로 / 극협소 → geometry·reward·observation·planning 개선 / 현 설정 부재 → 물리 조건·mission design 재설계 후 **다시 개발**. 부재 발견도 MARL 연구의 실패가 아니라 task design·physical feasibility에 대한 engineering feedback이다.
5. **평가 기준 = 원 문제 해결력**: 모든 제안은 "이 실험·변경이 MARL 양치기 시스템의 nominal 공격자 포획 능력을 실제로 키우는가"로 평가. 우선순위 상: ① A2 회랑 존재·구조 ② (존재 시) 재현 privileged controller/planner ③ brake가 실패·한계를 드러내는 longer-horizon·다중 역할 조건 ④ learned limiter의 상태-의존 협력 분석(vs 단순 controller) ⑤ A3 cost-aware attacker에서 고정 규칙 exploitability ⑥ (필요 시) curriculum·role specialization·centralized critic 발전 ⑦ nominal/broader 분포 autonomous capture. 우선순위 하: 티어 재평가 반복·진단 목차 정교화·U-A/U-B 배정을 이유로 한 실험축 조기 분리·마감 맞춤 클레임 축소·실패 시 즉시 종결 프레이밍.
6. **티어 평가 = snapshot 출판 가능성 전용**: "현재 부족 → 진단 논문으로 정리" 추론 금지. 올바른 사용 = "지금 snapshot으로도 국내 발표 가능; 연구는 계속 발전시키고, confirmation·mission-level 성능·stronger attacker·MARL 우위가 쌓일수록 최종 티어·중심 주장을 다시 결정." **harvest map ≠ research ceiling map.**
7. **[P-1] 확정 처분**: 8/31 트립와이어 = **현 술어·기존 predecessor/rewind 공략 캠페인의 종료선으로만** 유지(동일 실패 레버 무한 반복 방지 장치). 회랑 existence·corridor construction / nominal transfer / hybrid confirmation / longer-horizon cooperative shaping / A3+ attacker / MARL necessity / 역할 분화·일반화는 **별도 신규 개발축으로 계속 개방** — 이를 이유로 전체 연구를 B-fork 집필 전용으로 전환하지 않는다. 단 신규 축 개봉 시 0-e급 대형 사전등록·문서 증식 반복 금지: **Discovery mode로 핵심 신호 확보 → 양성 시에만 Confirmation 전환**(2-모드 프로토콜의 원래 취지).
8. **제안 형식 의무**: 다음 단계 제안 = ① 남은 병목 ② 그것을 직접 검정/해소하는 최소 실험 ③ 성공 시 nominal mission 해결력이 어떻게 느는가 ④ 실패 시 다음 개발 방향이 어떻게 달라지는가 — 를 먼저, 워크샵/U-A/U-B 활용은 **그 뒤에 부가로만**.

---

## 0-2. 방침 기록 (v0.1에서 이월)

- Paper A 즉시 분리 집필 안 함. 연구는 계속(공격자 업그레이드 포함, MARL 포함), 통합 산출물 = URP 보고서(중간 8월 말~9월 초, 최종 12/18). 논문 절단은 수확 시점에 Hyunjun 지시로.
- **[P-2] 워크샵 슬라이스**: 임박 국내 마감(§2 U-W 표) 선택은 교수님 상의 후 확정 — 어느 쪽이든 **중간 산출물 snapshot**이며 연구 종점·스코프 기준이 아니다(§0-1.1).

---

## 1. 유닛 경계 기준 (수확 시점의 편집 기준 — [v0.2] 라우터 아님)

기술 단계가 아니라 다음 3개 중 **2개 이상** 바뀌면 별도 논문: ① 주요 독립변수 ② 주요 baseline ③ 결론 문장.

| | U-A (포획 시스템 개발 서사) | U-B (MARL 필요성 서사) |
|---|---|---|
| 독립변수 | predecessor·horizon·capture geometry·회랑 연결성·terminal 분해 | attacker sophistication·attacker 목적·defender exploitability·co-adaptation |
| baseline | zero·brake·λ-brake·MAPPO·oracle/궤적최적화 | A3 MPC attacker·learned exploiter·defender MPC·IPPO·MAPPO·adversarial training |
| 결론 문장 | "이 포획 문제는 어디까지 물리적으로 연결되고, 무엇이 학습 가능하며, 무엇을 구조 분리해야 하는가" | "전략적 상대 앞에서 단순 제어는 언제 한계에 도달하고 왜 MARL이 필요한가" |

**[v0.2 정정]**: "U-A에서 MARL = 방법, U-B에서 MARL = 연구 대상"은 절단 시점의 편집 기준일 뿐이다. **실험을 지금부터 논문 단위로 격리하는 규칙으로 사용 금지** — A3 결과라도 중심 서사(§0-1.2)를 강화하면 같은 축에 연결하고, 분리 여부는 결과 축적 후 결정한다. (v0.1의 "A3부터 자동으로 U-B 적립" 문구 폐지.)

---

## 2. 유닛 정의 (4개 — 보관함)

### U-W — 워크샵/국내 슬라이스 (snapshot 수확 단위)

- **중심 클레임**: learned cooperative shaping + verified rule-based terminal guard = **teacher-free autonomous capture**(국소 d1). docs/20 Q-tier 워크샵 필요선 충족 — paired Δ̂ 全 seed > 0.10(+.758 / +.483 / +.483 vs zero .017), 가드 규율 fire_clean .98–1.0·wasted ≈ 0·d0 1.00×3 ((ppp)). **캐비앗 의무 표기**: dev-only discovery(3-seed, sealed 소진) + 제4병목(brake+guard .858 > learned .775) 정직 보고.
- **각도 4종**(학회별 재단): ① hybrid capture ② L0 MARL 학습(mix 역-U {0: 11.80, 0.5: 14.00, 1.0: 10.40}·비용-인지·10-seed +1.91 CI[+0.83,+3.13]) ③ 실패 해부·사전등록 방법론(증거 테이블·이중 면도날·오라클 σ-감쇠) ④ WarSim/스택.
- **임박 마감 [P-2 상의용]**: SASE 신청 7/31(1쪽) / **AI학술 8/24**(국문 단편+학부 경진) / KSME 8/26(초록) / **RiTA 8/31**(영문 2–15쪽 — ⚠ LNNS/Scopus 게재 옵션 = 아카이벌 → 발표-only 권장). 가을: KSAS 추계(공지 대기), KIMST 추계(예상 9~10월), IEIE 10/19, KRoC 11/26 하드.
- 국내 단편 = 비아카이벌 → 저널·arXiv 선점과 무충돌.

### U-A — 포획 시스템 개발 서사 (권고안 Paper A 계열)

- **[v0.2] 기본 프레이밍 = 개발 서사**(§0-1.3): MARL 협력 양치기·성형 시스템 개발 과정에서 hybrid terminal 분리와 local-to-mission reachability 병목을 규명·해결. 진단·mission-design 프레이밍(권고안 §5.2)은 회랑 부재·후속 실패 누적 시의 fallback.
- **중심 질문**(권고안 §3): local capturability shaping ↔ mission-level reachability — 무엇이 학습 가능하고, 무엇을 구조 분리하며, 어떻게 연결되는가.
- **아웃라인** = 권고안 §4.1~4.6 + 보강 3(L0 요약 = surrogate-terminal 분리 실측 증거 · 명제 N 이론 절 · docs/12 §6 표 승격).
- **회랑 실존 프로브**: **[v0.2 재정의] 종결 실험이 아니라 다음 개발 수 선택용 전제 진단**(§0-1.4). 논문 편입 시점엔 §4.6 자리에 들어가지만, 실행 목적은 개발 라우팅이다. A3 캠페인 전제 진단 겸용(A2 회랑 미확인 시 A3 실패 원인 분리 불능).
- **MARL 취급** = 권고안 §6: 필요성·우월성 주장은 해당 증거 확보 시점까지 유보(제4병목 정면 보고).

### U-B — MARL 필요성 서사 (권고안 Paper B 계열)

- **중심 질문**(권고안 §7): 언제 단순 협력 제어가 무너지고, 비용-강요 적응 공격자 아래에서 MARL이 필요해지는가. 사다리 = docs/20 A0~A5(A3 cost-aware MPC → A4 exploiter → A5 self-play).
- **+ S9 경제 해제**: J_A에 방어 자원 소모·baiting 포함(권고안 §8.2) = novelty 감사(2026-06-24)의 open seam 실험 실현. M2 numpy POC 4종 = 서론/동기 재료. S6 2-tier 계약상 경제 frontier 주장은 이 보관함에서만.
- **[v0.2]**: attacker upgrade 실험의 소속은 자동이 아니다 — 결과·중심 주장에 따라 절단 시점에 결정(§0-1.2).
- 신규 축 개봉 시 discovery-mode 우선(§0-1.7 — 0-e급 사전등록 반복 금지).

### U-R — URP 보고서 스파인 (상위집합)

- 중간보고 8월 말~9월 초(진행 snapshot) / 최종 12/18. 보고서는 논문이 아니므로 유닛 경계 무관 전부 수록. 종합 성과 발표처 = KIMST 2027 종합(예상 신청 4월 하순·6월 제주).

---

## 3. 티어 판정 — snapshot 출판 가능성 평가 전용 ([v0.2] research ceiling 아님)

> 기준일 2026-07-19, 추가 실험 0 가정의 **snapshot 평가**. "현재 부족 → 진단으로 정리" 추론에 사용 금지(§0-1.6) — 연구가 발전할수록 이 표 자체가 갱신된다.

| 티어 | 2026-07-19 snapshot | 승급에 필요한 축적 |
|---|---|---|
| 국내 단편/워크샵 | **충족** — U-W 각도 ①~④ 즉시 재단 가능 | — (dev-only 캐비앗 표기만) |
| 영문 단편(RiTA급) | **충족** | — |
| 학회 본회(ICRA/IROS/AAMAS급) | 미충족(snapshot 기준) | ⓐ hybrid confirmation 재현(신규 held-out 번들·5–10 seeds — sealed-v2d1 소진이라 신규 대역, 1회 원칙 무충돌) ⓑ mission-level 결과(회랑 구조·corridor-aware 개발 성과) |
| Q2 저널(응용) | 미충족(snapshot 기준) | ⓐ+ⓑ |
| Q1 저널(RA-L/T-AES/ASTE급) | 미충족(snapshot 기준) | ⓐⓑ + ⓒ MARL 필요성 증거(A3+·longer-horizon·역할 분화) 또는 일반성, 또는 nominal autonomous capture |

- snapshot의 공격면 4(기록용): dev-only discovery · d1-국소 · 제4병목(brake .858 ≥ learned .775) · A2 고정. **이는 개발 우선순위(§0-1.5)가 해소해 나가는 대상이지, 프레이밍을 낮출 근거가 아니다.**

---

## 4. 벤ue 사다리 (마감 실측 2026-07-19 — 수확 시점 참조용)

### 국제

| 벤ue | 성격/통상 티어 | 마감 | 정합 보관함 | 비고 |
|---|---|---|---|---|
| **ICRA 2027 (서울)** | 로보틱스 본회 | **2026-09-15 실측** ([공식](https://2027.ieee-icra.org/contribute/)) | U-A | 서울 개최 = 참석 장벽 최소. 워크샵(모집 ~2027 초) = U-W 국제판 카드 |
| RA-L | Q1 저널(로보틱스) | 상시 | U-A | ~6쪽+, 심사 ~3개월. ICRA/IROS 발표 연동 옵션 시기 요확인 |
| **IROS 2027 (피렌체)** | 로보틱스 본회 | **2027-03-01** ([aconf 실측](https://www.aconf.org/conf_300883.2027_IEEE/RSJ_International_Conference_on_Intelligent_Robots_and_Systems_(IROS).html) — 공식 CFP 재확인 요) | U-A/U-B | 가을~겨울 축적 기준 현실적 옵션 |
| AAMAS 2027 (하노이 5/3–7) | MAS 본회 | 2026-10 TBC ([공식](https://warwick.ac.uk/fac/sci/dcs/aamas2027/)) | — | 실험 일정상 스킵 — MAS 계열 정조준 = **AAMAS 2028** |
| IEEE T-AES | Q1 저널(항공우주·방어) | 상시 | U-A·U-B | 장문 허용, C-UAS/OR 독자층 정합 최고 |
| Aerospace Sci & Tech / JGCD | Q1~Q2 저널 | 상시 | U-A | 유도조종·capturability 문헌 본진 |
| Drones / Machines (MDPI) | JCR Q1~Q2(변동 요확인) | 상시·고속 | 폴백 | Xu net 논문(Drones)·Huh 2026(Machines) 게재지 |
| IEEE Access | Q1~Q2(하락 추세) | 상시 | 최후 폴백 | — |
| ICRA/AAMAS 워크샵, NeurIPS 계열 WS | 워크샵 | 행사별 | U-W | 비아카이벌 위주 — 선점·피드백용 |

### 국내 (정본 `conference_targets_2026H2.md` 요약 — 마감 순)

SASE 신청 7/31 → AI학술 8/24 → KSME 8/26 → RiTA 8/31 → KSAS 추계(공지 대기·1순위) → KIMST 추계(예상 9~10월·1순위) → IEIE 10/19 → KRoC 2027 11/26 하드 → KIMST 2027 종합(예상 4월 하순 신청). 출장·슬라이스 배분 전략은 정본 문서 §전략 노트.

---

## 5. 콘텐츠 배정 매트릭스 (수확 시점의 절단 기준 — [v0.2] 실험 격리 규칙 아님)

● = 본문 핵심 / ◐ = 요약·배경 / ○ = 미포함. **절단 시점에** 이 표가 배정을 결정한다. 미실행 항목(13·15)의 소속은 결과에 따라 재결정.

| # | 자산 (핵심 수치 · 출처) | U-W | U-A | U-B | U-R |
|---|---|---|---|---|---|
| 1 | L2 게이트 PASS·mix 역-U {11.80/14.00/10.40}·비용-인지 셰이핑·10-seed paired +1.91 CI[+0.83,+3.13] ((i)(k)(n)·P1) | ●(각도②) | ◐(surrogate-terminal 분리 증거) | ●(협력 알고리즘 기반선) | ● |
| 2 | 명제 N — plateau v_soft=5/6·θ_fire∈(5/6,1] shaping-forcing (docs/10 DRAFT) | ◐ | ●(이론 절) | ◐ | ● |
| 3 | A-1 절벽 [0.1274,0.1455]·A-2 정적-폭에도 즉사 (0.1335,0.1501]·인센티브 가설 기각 ((y)(cc)) | ●(각도③) | ●(§4.5) | ○ | ● |
| 4 | A-3 이중 면도날(공간 0.05–0.2 m × CRN)·robust witness 실존·리파인 1.00 ((ff)(gg)(bbb)) | ●(각도③) | ● | ○ | ● |
| 5 | A-3b 캠페인 최초 학습 포획(R0 .95–1.00)·spawn-luck 천장 ((kk)) | ◐ | ● | ○ | ● |
| 6 | U-1 recoverability 오라클 G0: r@2+ ≡ 0 ((nn)) | ○ | ● | ○ | ● |
| 7 | A-3d SBE 2-게이트·4조건 σ-validation·오라클 σ-감쇠(k=1 .94–.95 / k≥2 .61–.81)·BANK FAIL ((hhh)(iii)) | ●(각도③) | ●(방법론 + 합성 한계) | ○ | ● |
| 8 | **L1 재성형 학습** Δ^teacher +.79/+.80/+.93·cap .81/.82/.94·zero .017 ((ooo)) | ● | ●(§4.2) | ◐ | ● |
| 9 | J1 learned-fire 결합 실패(always-fire/무발사 양극)·부식 곡선 ((ooo)(ppp)) | ◐ | ●(§4.3 — hybrid 근거 증거) | ◐(트리거 설계 교훈) | ● |
| 10 | **hybrid 자율 포획** j1_e1 .775/.500/.500·가드 규율 완벽·d0 1.00 ((ppp)) | ● | ●(§4.3) | ◐ | ● |
| 11 | **제4병목** brake+guard .858 ≥ learned .775 ((ppp)) | ●(정직 보고) | ●(§4.4) | ●(문제 제기) | ● |
| 12 | 수확 공집합 F_hist={2:195}·nominal 프로브 0/500 무발사 ((qqq)(qqq-1) 정정 표현 준수) | ○ | ●(§4.5 — 3종 장애·미검 명제 분리) | ○ | ● |
| 13 | 회랑 실존 프로브 (미실행 — 전제 진단, §0-1.4) | ○ | ●(결과 따라) | ◐(전제 진단) | ● |
| 14 | M2 경제 POC 4종(exchange_game "shaping>buy-nets" 등)·S9 exchange-frontier | ○ | ○(S6 2-tier 계약 — 경제 주장 금지) | ●(서론·동기) | ◐ |
| 15 | A3 MPC·A4 exploiter·A5 self-play (미실행 — 소속은 결과 따라, §0-1.2) | ○ | 결과 따라 | 결과 따라 | ● |
| 16 | 6-DOF/SITL stretch·E_req/N1 앵커 트랙(WP-A4/CP-4 대기) | ○ | ○ | ○ | ◐(별도 트랙 표기) |

---

## 6. 클레임·게재 규율 (전 유닛 공통)

1. **A2-한정**: "적응 공격자에 대한 방어" 클레임은 A3+ 결과 후에만(docs/20 원칙).
2. **제4병목 의무 보고**: 정책 vs 단순 컨트롤러 비교 없이 RL-방법 클레임 금지.
3. **discovery/confirmation 라벨 의무**: (ppp) 계열 dev 결과는 confirmation 재현 전까지 discovery 표기.
4. **(qqq-1) 정정 표현 준수**: "3중 독립 증거" 금지 — "분석·합성·학습 경로의 세 종류 horizon-extension 장애"; nominal 무발사 = transfer 실패 증거(회랑 부재 증거 아님).
5. **verify-before-cite**: Huh 2026 = REAL(Machines 14(4):413) 정밀 인용 / "Jia 2026" 사용 금지 / FRPN(≠EPN). must-cite-and-diverge: Atkinson & Kress 2025(OR 73(4)), Von Moll 2509.09777, Chen 2024(luring), Liu 2506.03297(tethered net+MAPPO), Gavin 2603.16279, StringNet(Chipade-Panagou), Choi 2026, COMA(Foerster AAAI'18).
6. **방어 가능한 novelty 코어**: 학습된 net-finisher viability set을 협력 셰이핑 신호로 + hybrid 역할 분담(learned shaping / verified guard) + shaping-as-economic-lever seam.
7. **공개 노선**: moat 완화 결정(2026-06-24 reframe) 유지 — 코드·재현 공개(J.6 ON), arXiv는 원고 시점.
8. **이중게재 경계**: 국내 단편 비아카이벌 무충돌 / RiTA LNNS·ICTC Xplore = 아카이벌 주의 / URP 보고서·학위 = 무관.

## 7. 결정 슬롯 (v0.2 상태)

- **[P-1] 확정(2026-07-19)**: §0-1.7 그대로 — 8/31 트립와이어는 현 술어·predecessor/rewind 캠페인 종료선으로만; 신규 개발축(회랑·nominal·hybrid confirmation·longer-horizon·A3+·necessity·역할 분화) 개방, B-fork 전용 전환 없음, 신규 축은 discovery-mode 우선.
- **[P-2] 대기**: U-W 슬라이스·마감 선택 (교수님 상의 후; §2 표) — snapshot 수확일 뿐 스코프 기준 아님.
- **[P-3] 재정의**: 회랑 실존 프로브 = 다음 개발 수 선택용 전제 진단(§0-1.4), discovery-mode로 실행(대형 사전등록 없음 — 판정 J·평가 경로 동결·seed 대장·증거 기록의 최소선만).
- **[P-4] 대기**: hybrid confirmation 재현 편성(신규 held-out 번들·5–10 seeds) — 티어 승급 조건 ⓐ이자 시스템 검증 그 자체.
