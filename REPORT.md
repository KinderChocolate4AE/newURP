# 야간 자율 연구 보고 — night/2026-10-13 (02:37–08:15 KST)

## 1. 한 줄 요약
<!--HEADLINE-->

## 2. 세계 설계서 요약과 현실성 범위
상세: `WORLD.md`. 3D 점질량, 물리 dt 0.02 s (판정은 step 내 최근접점으로 연속 처리), 제어 0.1 s, 판 최대 30 s.
자산은 원점, 공격자는 500–700 m · ±60° · 고도 20–80 m 에서 출발, 자산 3 m 이내 도달 = 누출.

| 대상 | 명목값 (범위) |
|---|---|
| 공격자 (FPV 급) | 30 m/s (25–40), 20 m/s² (15–30), 반응 τ 0.2 s (0.1–0.3) |
| net 드론 | 22 m/s, 8 m/s², τ 0.3 s; 그물 반경 1.5 m (1–2), 발사속도 25 m/s, 비행 ≤1.0 s (사거리 ~25 m), 전개 0.25 s, 2발, 재장전 1 s |
| limiter | 45 m/s (40–80), 30 m/s² (25–50), τ 0.1 s (0.05–0.15), 자동 근접신관 2.5 m (2–4), 1회용 |
| 방어 센서 트랙 | 위치/속도 잡음 σ 1 m / 1 m/s (0.5–3), 지연 0.1 s (0.05–0.3) |

범위 변경 경위:
- **v1 → v1.1 (02:46, 점수 기록 전)**: 완전 관측에서 스크립트 방어가 512/512 요격 → 방어 트랙 잡음·지연 추가.
- **S1 → S2 (03:21, 사람 지시)**: S1 은 limiter 우위로 net 기여 ≈ 0. 결과 보기 전에 고정한 선택 규칙 (LAB_LOG 03:08) 으로 regime 스윕 → (a)(b)(c) 동시 충족 regime 없음 → 위반합 최소 **R9_lag3 (방어 트랙 지연 0.3 s, 범위 상한), n=1** 선택. 여기서 점수표 S2 를 새로 시작. S1 숫자와 섞지 않는다.
- R9_lag3 가 뽑힌 이유에 대한 단서: 지연이 net 단독 요격률을 29.7→41.5% 로 **올렸다**. 원인은 스크립트 fire-control 이 등속 리드조준이라 비행시간이 길수록 (곡선 비행 공격자) 오차가 큰데, 지연된 트랙이 실제 발사를 늦춰 비행시간을 줄인 효과. 즉 net 기여를 키운 것은 센서 악화 자체가 아니라 약한 스크립트 발사창의 우연한 보정이다.
- 스윕의 net 기여 (Δnet ≤ 7.8%p) 는 발사 타이밍이 약한 원 스크립트로 잰 **하한**이다. net 드론을 자산 앞 8 m 골키퍼로 두고 비행시간 ≤0.5 s 에서만 쏘는 GK 스크립트는 같은 S2 에서 net 단독 88.7% (원 스크립트 41.2%).

설계 결정 (세계가 아니라 방어 설계, 점수표를 바꾸지 않음): fire-control 인터록 (리드조준 해의 비행시간 ≤1.0 s 일 때만 발사 가능; 원 스크립트 숫자 불변 확인), GK 프리셋 (base 정책), 방어 관측의 측정 트랙 이력 3개.

### limiter 수 n 표기 정리
- S1 의 모든 학습·레드팀 실험은 **n=2** (기준선만 n=1–4).
- regime 스윕: 스크립트 방어 n=1–4 를 모두 잼. 짧은 레드팀 (red400) 열만 **n=2**.
- S2 의 모든 학습·레드팀·PSRO 는 **n=1** (선택 규칙이 n=1 을 고름). LAB_LOG 에서 "n2" 가 붙은 이름은 S1 또는 스윕 red400 이다.

## 3. 점수표
<!--TABLES-->

## 4. 효과가 있었던 설계 결정 3개 / 없었던 것 3개
<!--DECISIONS-->

## 5. 확신하지 못하는 부분
<!--UNSURE-->

## 6. 재현
로컬 (Windows, Git Bash):
```
py -3.12 -m venv .venv && ./.venv/Scripts/python -m pip install "jax[cpu]==0.6.2" numpy matplotlib
PYTHONIOENCODING=utf-8 ./.venv/Scripts/python test_sim.py
PYTHONIOENCODING=utf-8 ./.venv/Scripts/python netcmp.py runs/x.json S2,GK,obs_hist=3 runs/S2GK_g1.pkl "--fire_prior 1 --lim_scale 1.0" runs/S2_RP_e4_w.pkl
PYTHONIOENCODING=utf-8 ./.venv/Scripts/python report_tables.py
```
서버 (server4, `/data/hjhong/night/code`, python = `/data/hjhong/fs1jax/.venv-jax/bin/python` 실행만):
```
./srv.sh push                                   # 로컬 → 서버 전체 트리
./srv.sh run NAME 16 baseline S2_baseline --world S2
./srv.sh run NAME 12 train_def S2GK_g1 --world S2,GK,obs_hist=3 --n 1 --iters 2000 --lr 1e-4 --envs 4096 \
    --red <S2 레드팀 pkl,...> --red_frac 0.7 --c_lim 0.2 --fire_prior 1 --lim_scale 1.0 --seed 91
./srv.sh run NAME 16 train_att S2_RP_x_s1 --world S2,GK,obs_hist=3 --n 1 --iters 800 --seed 1001 \
    --def runs/<def>.pkl --fire_prior 1 --lim_scale 1.0
tmux new -d -s night_psroA 'CUDA_VISIBLE_DEVICES=1 $PY psro.py A 30 runs/S2GK_g1.pkl S2,GK,obs_hist=3 "--c_lim 0.2 --fire_prior 1 --lim_scale 1.0" 12 16,17,18 0805 0820'
```
<!--TMUX-->

## 7. 다음에 할 일
<!--NEXT-->
