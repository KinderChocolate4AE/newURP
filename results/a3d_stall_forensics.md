# A-3d 정체·붕괴 규명 — 2026-07-16 ((rr) ⓐ 이행)

입력: pilot2 아티팩트(`bfdc3b9`) + 무결성 컨트롤 480판((rr)) + 신규 기전 프로브 480판(brake/demo, `nb2_results.jsonl`). 전 측정 = 동일 게이팅 하네스·동일 CRN(ep 1:1 짝지음).

## 헤드라인 (발견 3)

1. **"전멸 eval"은 붕괴가 아니라 전부 d3(k=4) 번들 측정치**다 — 그리고 그 번들에서 trained는 무행동(0.188)·brake(0.188)보다 나쁜 **0.000~0.025** = 능동 이탈.
2. **게이팅 번들에 att_speed 핀이 없다** (설계 갭, 구현은 설계에 충실). 공격자는 항상 nominal 20으로 구동 → v16 엔트리(~1/3) = **어떤 행동으로도 0%**, v24(~1/3) = **무행동도 0.57~0.93 공짜**, 변별력은 v20(~1/3)뿐. 사다리 게이트 전체가 이 왜곡된 시험 위에서 돌았다.
3. **1줄짜리 brake 정책이 trained를 전 스테이지에서 지배** (d1 45/80 vs 34, d2 36/80 vs 29, d3 15/80 vs 0~3). "d1·d3 유의 증분"은 존속하나 competence 주장은 사망.

---

## 1. 전멸 eval 재귀속 (census)

`cur` 라벨 오프바이원(코드 확정: `evaluate()` → `on_eval()` 전이 → `describe()` 기록, train_m3a.py 612-625행) 보정 후:

| eval | 라벨 | **실측 번들** | cap | fire | len |
|---|---|---|---|---|---|
| s1@204800 | d2 | **d3** | 0.000 | 0.000 | 19.2 |
| s1@307200 | d2 | **d3** | 0.000 | 0.000 | 19.1 |
| s1@348160 | d2 | **d3** | 0.013 | 0.013 | 19.0 |
| s2@245760 | d2 | **d3** | 0.025 | 0.025 | 23.4 |

전멸 = 100% d3 측정. len 19~23 = 자연 침투 길이(교전 부재). d2 복귀 즉시 0.362 = 시간 축 붕괴 아님. MISLABEL은 전이 걸린 eval 전부(seed1 6회·seed2 2회·전 seed 첫 eval의 d0→d1).

## 2. Flatline 판독

비트 동결 아님: seed0 return_mean은 소수 3~5자리에서 계속 미세 표류(트레이너 정상 작동), 그러나 **80판 전부의 이산 결과 고정**(len_mean 47.5875가 122880부터 끝까지 동일) = 결정론 eval + 고정 CRN 번들 + 수렴 정책. seed1/2도 후반 동형(29/80 고정, 연속값만 진동). 즉 "예산 80% 무학습"의 실체 = **정책이 train 목적에서 수렴**했고 게이팅 문턱을 못 넘는 위치였던 것.

## 3. 근본 원인: 게이팅 번들 att_speed 미핀

코드 3점 확정: ① `env_m3.reset_to`는 `limiters/limiter_v/att_p/att_v`만 소비 — **`att_speed` 무시** ② 핀은 train rollout에만(`train_m3a.py:267`, `_begin_episode` params 패치) ③ 공격자는 env-내부 scripted(`env.py:334`, 외부 액션 무시) → eval 공격자는 **항상 cfg nominal 20 추격 드라이브**.

SBE 구성 전제(docs/17 §1) = "att_speed를 witness v로 핀". 게이팅 번들은 v* 주입 속도로 스폰되지만 컨트롤러가 20으로 보정 → v16 엔트리는 공격자가 **가속·선행**(창이 리미터 도착 전에 지나감 = 죽은 시험), v24는 **감속·지연**(창이 늦게 열림 = 리미터가 기다리면 공짜). witness-v 분해 실측 (captured, 컨트롤 arm):

| | v16 | v20 | v24 |
|---|---|---|---|
| d1 zero | 0/34 | 1/19 | **25/27** |
| d1 brake | 0/34 | **18/19** | 27/27 |
| d2 zero | 0/26 | 0/25 | **19/29** |
| d2 brake | 0/26 | 7/25 | **29/29** |
| d3 demo | 2/29 | 8/28 | 16/23 |

**v16 = 전 arm·전 스테이지 합산 2/202.** 번들 구성(전진 rng 결정론): d1 34/19/27, d2 26/25/29, d3 29/28/23.

주: V-4("eval 전 경로 nominal 불변")는 judgment 오염 방지가 목적이었으나, **게이팅 번들은 스폰(스테이지 산물)과 공격자 속도(nominal)가 서로 모순되는 시험**이 됨 — frozen/judgment 번들은 spawn_fn=None이라 무영향. A-3(σ≫창)·pilot1(D0 σ) 이은 **"잘못 출제된 시험" 3호**. 이번 것은 코드 실수가 아니라 비준된 설계의 갭.

## 4. 리그 테이블 + 시험 구조

captured/80 (게이팅 번들, teacher finisher 동일):

| | zero | random | brake | demo | **trained** | exit 전진선(k*) |
|---|---|---|---|---|---|---|
| d1 | 26 | 27 | **45** | 40 | 34 (s0) | 40/80 (0.40) |
| d2 | 19 | 22 | 36 | **37** | 29 (s1·s2) | 31/80 (0.30) |
| d3 | 15 | 7 | 15 | **26** | 0~3 | 22/80 (0.20) |

- paired 중첩: d2에서 zero의 19판은 **brake 36·demo 37의 완전 부분집합** = "공짜 고정 부분집합 + 행동 증분" 구조 실증.
- brake(= -30·unit(v), 도착점 정지 근사)가 d1·d2에서 **전진선을 넘는다**(45>40, 36>31). demo도 d2·d3 통과(37>31, 26>22). **trained만 전 스테이지에서 전진선 미달.**
- 구조 해석: seed0 d1 = 34/80 수렴, 전진에 40 필요, 죽은 v16이 34판 → 살아있는 46판 중 87% 요구 = 실질 천장 근접 과제. seed1/2 d2 = 29/80, **전진선 31에 단 2판 부족**으로 350k 스텝 고착. 게이트 thrash(전진→즉사→후퇴)는 게이트 오작동이 아니라 **d3에서 정책이 실제로 0점**인 것의 정직한 반영.

## 5. 미결: trained d3 ≈ 0의 기전 (서버 필요)

v24 공짜(무행동도 0.57)까지 0으로 만드는 것은 회피 비행뿐: 리미터를 회랑 밖으로 끌어내 창 형성 자체를 소거(fire 0.000, len=침투 길이). 후보: ⓐ 미학습 스테이지 OOD(정책은 d2까지 학습, d3 스폰의 위치·속도(≤4.8m/s)는 obs-norm 밖 → Gaussian mean 외삽 폭주) ⓑ 결정론-eval 붕괴(학습 중 포획은 탐사 노이즈 의존) ⓒ PBRS Φ의 원거리 구배가 창 반대 방향. **판별 = 서버 궤적 덤프**(아래 §7 B-2). 주의: 전이 직후 20k 스텝 d3 학습 후에도 0 유지 — 순수 무경험 아님.

## 6. (rr) 해석 개정안 ((ss) 초안 방향)

- 존속: V-5 전제 반증·paired 무결성 컨트롤 필요성·"물리 벽 제거"·d1/d3 zero-대비 유의 증분(동일 시험 내 비교라 유효).
- 개정: ① 그 증분은 **왜곡 시험 내부**의 증분(1/3 dead·1/3 free) ② **competence 부정** — brake가 전 스테이지 지배, 전진선 기준 brake/demo는 통과·trained만 미달 ③ 정체 원인 = 붕괴 아닌 "수렴 + 오출제 시험의 문턱 기하"(d2는 2판 차) ④ 파일럿2 판정은 **핀 픽스 후 재실험 전까지 전면 유보**.

## 7. 결정 큐 (Hyunjun 비준 대상)

1. **V-4′(게이팅 핀 픽스)**: `m3_eval_bundle` 게이팅 경로에서 spawn dict에 `att_speed` 있으면 per-episode env 재구축(train rollout과 동일 기계). frozen/judgment 경로(spawn_fn=None) 무접촉. *대안(비추): bank를 v20-only로 축소 — 가족 폭 상실.*
2. **V-5′ 최종형**: 동일 번들·동일 ep paired — ⓐ 무결성: vs zero-action, McNemar 단측 + Δ CI ⓑ competence 문맥: brake·demo 리그 병기(전진선 대비). 다음 런 착수 전 확정.
3. **exit 재보정**: 핀 픽스 후 컨트롤 arm(zero/brake/demo) 재실행으로 스테이지별 천장·공짜 floor 재측정 → exit 재유도(현행 값은 오출제 번들 기준이라 무의미).
4. **`cur` 라벨 픽스**(로깅 전용, eval 전 스냅샷 기록) + run_state에 측정-번들 d_idx 병기.
5. TODO ① 계측 위치 d4 재지정(기존 (rr) 항목 유지).
6. docs/09 **(ss)** 기록 + 본 리포트·프로브 데이터 커밋.

## 8. 서버 런북 (Hyunjun, 순서대로)

```bash
# B-0 (규명 마감용, 재런 불요): wandb 오프라인 덤프 — flatline 서명
cd /data/hjhong/newURP && source .venv-l2/bin/activate
ls wandb/ | grep offline   # m3a pilot2 런 3개 특정
python scripts/wandb_offline_dump.py --run wandb/<offline-run-seed0> \
  --keys limiter/log_std limiter/entropy limiter/approx_kl grad_norm \
         epochs_ran clip_fraction_action perf/lr_frac
# 판독: 102k 이후 limiter/log_std ↘(탐사 소멸)인지, approx_kl→0·epochs_ran 유지인지.
# log_std가 LOG_STD_MIN 근처면 = 엔트로피 붕괴(ent_coef_limiter 0.0의 귀결) → 처방 후보: ent_coef_limiter>0.

# B-1: ckpt best(20480) vs latest(519168) 파라미터 이동량
python - <<'PY'
import torch
for s in (0,1,2):
    a=torch.load(f'results/m3a_a3d_pilot2/seed{s}/ckpt_mappo_best.pt',map_location='cpu')
    b=torch.load(f'results/m3a_a3d_pilot2/seed{s}/ckpt_mappo_latest.pt',map_location='cpu')
    sa,sb=a['lim_actor'],b['lim_actor']
    import math
    tot=sum(float((sb[k]-sa[k]).norm())**2 for k in sa)
    print(f"seed{s} lim_actor Δ||θ||={math.sqrt(tot):.4f} log_std(best→latest):",
          sa['log_std'].mean().item(),'->',sb['log_std'].mean().item())
PY
# (ckpt dict 키가 다르면 load_warm의 키 매핑 참조)

# B-2 (핵심 미결): trained ckpt의 d3 궤적 덤프 — v24 공짜 episode에서 리미터가 어디로 가는가
# 스크립트는 다음 세션에서 준비(§5 판별 ⓐ/ⓑ/ⓒ). B-0/B-1 결과 먼저.
```

### 재현 각주
- 컨트롤/프로브 원자료: `nb_results.jsonl`(480) + `nb2_results.jsonl`(480), ep·arm·stage 단위.
- brake = `-30·unit(v_i)`(obs 판독) / demo = bank `demo_accels` 개방루프 재생(도착 후 0) — 엔트리 복원 = 게이팅 rng(`515151+d_idx·991+ep`) 복제.
- v-분해의 witness 귀속도 동일 rng 복제(스폰은 run seed 무관·결정론).
