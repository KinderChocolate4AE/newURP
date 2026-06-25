# newURP_M1_formalization_scaffold (v2 — 2026-06-24)  [CURRENT]

> 채우는 사람 = Hyunjun(코어 소유). AI = 슬롯·옵션·strawman + 채운 뒤 검토. strawman = redline 대상(채택안 아님).
> **v2 변경(GPT 검증 반영)**: S8을 reachable-set + COMA로 강화; Atkinson&Kress must-distinguish 추가; **S9~S14를 OPTIONAL로 분류·탑재**(삭제 안 함).
> **규율(과검증 교훈)**: 핵심 S1-S8만으로 M2 build 진입. 완벽 정식화로 build 지연 금지. OPTIONAL은 *필요할 때만* 활성화.

## A. must-distinguish 대조 시트 (선택이 이 축 벗어나면 seam 이탈)
| 선례 | 그들이 하는 것 | 우리가 다른 축 |
|---|---|---|
| **Atkinson & Kress 2025** (Oper.Res. 73(4):1767, 10.1287/opre.2024.1025) | 유한 hard+soft, leakers vs 요격소모 **efficient frontier**, shoot-look-shoot | frontier를 **mobile shaping**으로 *움직임*; 비파괴 net; MARL |
| Von Moll turret+defender 2025 (arXiv:2509.09777) | 이종팀, 적을 turret 도달집합으로; HJI | net 전개 viability(각도 아님); 학습; 유한·miss-free |
| Chen luring 2024 (Astrodynamics 8(4):675) | inducer 유인→teammate 요격 | 비파괴 finite; MARL; 목적=교환비 |
| StringNet 2021 (Front.Robot.AI 8:640446) | 대형 장벽 봉쇄 | 발사형 유한 net; 목적=경제 |
| WTA/salvo (Manne'58·Hughes'95·Armstrong'14) | 고정 사수 배분·타이밍 | maneuver-shaping이 lever; 비파괴 |
| 狼群 2021 (智能系统 16(1):125, 10.11992/tis.202007043) | 이종역할+비용, 규칙·kinetic | MARL; 비파괴; 비용=교환비 |
| sequential-intruders (arXiv:2212.06628) | 재사용 point-capture | 유한·비가역·비파괴 |

## B. 핵심 슬롯 (S1-S8) — 질문 / 옵션 / strawman / [결정]

**S1 플레이어&소모성**: N limiter(소모성?) + 1 finisher + 적 1 or M? · 옵션 (a)N=3 소모 (b)N 가변 (c)적 M=포화 · strawman: N=3 소모+1+적1 · [결정:__]
**S2 상태(신규=자원)**: 잔탄 k∈{0..K}+전개타이머; +적 모드(feint/penetrate)?; +적 자원? · strawman: 3DOF+k+전개카운트 · [결정:__]
**S3 액션(신규=발사 commit)**: fire=일회성 비가역, 발사후 τ 잠금; 적 {feint vs commit-penetrate}; limiter=setpoint · [결정:__]
**S4 정보구조(가장 미묘)**: finisher commit이 적에게 관측? (관측=baiting/commitment 게임=루프탈출 지점) · 옵션 full / partial(잔탄 은닉) / 동시수 · strawman: 전개개시 관측·잔탄 partial · **[결정:__] ← 게임 종류 결정**
**S5 per-shot value(E_req 재사용)**: v_shot∈[0,1]=commit 시 상대상태 함수 · strawman: v_shot=P(적∈전개net부피|상대상태,τ)≈σ(w·φ), φ=E_req항 · [결정:__]
**S6 목적함수(신규=miss-free)**: P_capture 아님. R=(적 침투비용)/(방어 소진자원); viable={R>1 under 적 best-response} · 가이드: numerator(feint수·노출·시간)·denom(발사수·잃은 limiter) 구체화 · [결정:__]
**S7 해 개념**: 학습 shaping 정책 + (capacity×속도/기동비) 경험적 viable-envelope (usability·MARL) · 차분게임 value는 대조군 인용만 · [결정:__]

**S8 shaping-as-lever (THE 코어 — GPT 강화, 네가 유도)**:
- 유도 틀: commit 시 deploy-delay τ 동안 적 best-response reachable set R_A(x,τ|u_L); net 전개 부피 N. **v_shot = P[x_A(t+τ)∈N]** 또는 worst-case **1[R_A^br(x,τ|u_L)⊆N]**. limiter는 R_A 축소 or N 커버리지로 밀어 v_shot↑.
- 채널 랭크(GPT): **(a) escape-volume 축소 = 최강** / (d) ammo 보존 — 단 **fire iff v_shot ≥ V(x,k)−V(x,k−1)** threshold 필요 / (b) net 고커버리지 cone — anisotropic net 모델 필요 / (c) "deplete"는 적이 소모자원 없으면 **무효**(bounded accel뿐이면 순간 reachability일 뿐).
- 신용할당: **COMA difference-reward** D_i=v_shot(u_i,u_-i)−v_shot(u_i^0,u_-i) (Foerster et al. AAAI 2018). terminal 보상 단독 금지(sparse·confounded).
- **[결정/유도:__]**

## C. 조기 sanity (구 'probe' — M2 초 1회, 별도 게이트 아님)
toy 1 limiter+1 finisher(K=1) vs scripted bait. shaping on/off로 v_shot/frontier 차이 1회 확인 → 음성이면 재고. **의식화 금지, build 안에서.**

## D. 자가 점검 (build 전): S1-S8 채움 / §A 축 위반 0 / S8 수식 닫힘 / 현실 파라미터(capacity·속도/기동비·net spec).

## E. OPTIONAL 슬롯 (GPT 도출 — 탑재하되 코어 작동 후, **build 막지 말 것**)
- **S9 raid process**: 순차/포화 적 M (유한자원이 binding되는 핵심). 단 M1 시작은 K=1 단일.
- **S10 적 feint 비용** c_feint (+ c_feint/c_shot 민감도) — miss-is-free를 가정 아닌 *구조*로.
- **S11 관측성 축** (full/delayed/hidden ammo·commit = 다른 게임) — S4의 실험축 분리.
- **S12 reload/logistics** (no-reload/slow/cartridge/spent-net obstacle) — capacity가 정말 binding인지 결정.
- **S13 적 best-response 프로토콜** (scripted→optimization→self-play→OOD→관측성 ablation) — "weak adversary" 공격 방어.
- **S14 surrogate(v_shot) 검증** (held-out·reliability curve·net param 민감도) — "reward engineering" 공격 방어.
> 활성화 규칙: M3 결과가 약하거나 리뷰어 방어가 필요할 때 *그때* 해당 슬롯만. 처음부터 전부 하지 말 것(과검증 재발 금지).
