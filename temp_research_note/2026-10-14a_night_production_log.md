# night1013 생산 실행 로그 (R1 docs/138 · E8 docs/139)

생성: 2026-10-14 13:30:43 KST · 실행자 세션 (해석 없음, 완료·실패 개수만)

- R1 manifest `1cdb7153a9391665` · E8 manifest `afba5be9e9c2714c`
- 코드 pin: R1 = `/data/hjhong/fs1jax/code` (REVISION 80afb2a) · E8 = `/data/hjhong/fs1jax/code_e6` (REVISION 0d36d2b)
- GPU0 only, 학습 동시 3 (XLA_PYTHON_CLIENT_MEM_FRACTION=0.30), 학습 CPU 0-3/4-7/8-11, BC CPU 12-15 worker 4
- 스크립트: `/data/hjhong/fs1jax/r1/_runs/{night_worker.sh, snapwatch.py, e8_bc.sh, mkreport.py}`

## R1 (15 slot × b1/b3 + b3 스냅샷)

| variant | seed | b1 | b3 | b3_at1e7 | b3_at2e7 |
|---|---|---|---|---|---|
| t0.7_h1.0_cv | 0 | done | done | done | done |
| t0.7_h1.0_cv | 1 | done | done | done | done |
| t0.7_h1.0_cv | 2 | done | done | done | done |
| t0.7_h1.5_cv | 0 | done | done | done | done |
| t0.7_h1.5_cv | 1 | done | done | done | done |
| t0.7_h1.5_cv | 2 | done | done | done | done |
| t0.5_h1.0_cv | 0 | done | done | done | done |
| t0.5_h1.0_cv | 1 | done | done | done | done |
| t0.5_h1.0_cv | 2 | done | done | done | done |
| t0.5_h1.5_cv | 0 | done | done | done | done |
| t0.5_h1.5_cv | 1 | done | done | done | done |
| t0.5_h1.5_cv | 2 | done | done | done | done |
| t0.5_h1.0_ma | 0 | done | done | done | done |
| t0.5_h1.0_ma | 1 | done | done | done | done |
| t0.5_h1.0_ma | 2 | done | done | done | done |

집계: b1 done 15, b3 done 15, b3_at1e7 done 15, b3_at2e7 done 15

### b3 스냅샷 실제 step (첫 ckpt after 1e7 / 2e7)

- `2026-10-13 19:39:35 w3 R1 t0.7_h1.0_cv/s1 b3_at1e7 SNAPSHOT it=179 total_steps=10562921 (target 1e+07)`
- `2026-10-13 19:39:38 w1 R1 t0.7_h1.0_cv/s0 b3_at1e7 SNAPSHOT it=199 total_steps=10134254 (target 1e+07)`
- `2026-10-13 19:43:13 w3 R1 t0.7_h1.0_cv/s1 b3_at2e7 SNAPSHOT it=339 total_steps=20720462 (target 2e+07)`
- `2026-10-13 19:43:44 w1 R1 t0.7_h1.0_cv/s0 b3_at2e7 SNAPSHOT it=379 total_steps=20761135 (target 2e+07)`
- `2026-10-13 19:49:48 w2 R1 t0.7_h1.0_cv/s2 b3_at1e7 SNAPSHOT it=219 total_steps=11057543 (target 1e+07)`
- `2026-10-13 19:52:53 w1 R1 t0.7_h1.5_cv/s0 b3_at1e7 SNAPSHOT it=219 total_steps=10662718 (target 1e+07)`
- `2026-10-13 19:54:08 w2 R1 t0.7_h1.0_cv/s2 b3_at2e7 SNAPSHOT it=399 total_steps=20405205 (target 2e+07)`
- `2026-10-13 19:57:19 w1 R1 t0.7_h1.5_cv/s0 b3_at2e7 SNAPSHOT it=399 total_steps=20327436 (target 2e+07)`
- `2026-10-13 20:02:09 w3 R1 t0.7_h1.5_cv/s1 b3_at1e7 SNAPSHOT it=199 total_steps=10598005 (target 1e+07)`
- `2026-10-13 20:06:20 w3 R1 t0.7_h1.5_cv/s1 b3_at2e7 SNAPSHOT it=379 total_steps=20510415 (target 2e+07)`
- `2026-10-13 20:06:31 w1 R1 t0.7_h1.5_cv/s2 b3_at1e7 SNAPSHOT it=219 total_steps=10925796 (target 1e+07)`
- `2026-10-13 20:10:28 w1 R1 t0.7_h1.5_cv/s2 b3_at2e7 SNAPSHOT it=399 total_steps=20161247 (target 2e+07)`
- `2026-10-13 20:14:03 w2 R1 t0.5_h1.0_cv/s0 b3_at1e7 SNAPSHOT it=199 total_steps=10424184 (target 1e+07)`
- `2026-10-13 20:18:01 w2 R1 t0.5_h1.0_cv/s0 b3_at2e7 SNAPSHOT it=359 total_steps=20251824 (target 2e+07)`
- `2026-10-13 20:20:21 w1 R1 t0.5_h1.0_cv/s1 b3_at1e7 SNAPSHOT it=219 total_steps=10748871 (target 1e+07)`
- `2026-10-13 20:24:58 w1 R1 t0.5_h1.0_cv/s1 b3_at2e7 SNAPSHOT it=419 total_steps=20717936 (target 2e+07)`
- `2026-10-13 20:26:36 w3 R1 t0.5_h1.0_cv/s2 b3_at1e7 SNAPSHOT it=219 total_steps=11039828 (target 1e+07)`
- `2026-10-13 20:30:43 w3 R1 t0.5_h1.0_cv/s2 b3_at2e7 SNAPSHOT it=399 total_steps=20582579 (target 2e+07)`
- `2026-10-13 20:32:02 w2 R1 t0.5_h1.5_cv/s0 b3_at1e7 SNAPSHOT it=179 total_steps=10422389 (target 1e+07)`
- `2026-10-13 20:36:06 w2 R1 t0.5_h1.5_cv/s0 b3_at2e7 SNAPSHOT it=339 total_steps=21342351 (target 2e+07)`
- `2026-10-13 20:39:09 w1 R1 t0.5_h1.5_cv/s1 b3_at1e7 SNAPSHOT it=179 total_steps=10454551 (target 1e+07)`
- `2026-10-13 20:43:03 w1 R1 t0.5_h1.5_cv/s1 b3_at2e7 SNAPSHOT it=339 total_steps=20422300 (target 2e+07)`
- `2026-10-13 20:44:34 w2 R1 t0.5_h1.5_cv/s2 b3_at1e7 SNAPSHOT it=199 total_steps=10867082 (target 1e+07)`
- `2026-10-13 20:48:34 w2 R1 t0.5_h1.5_cv/s2 b3_at2e7 SNAPSHOT it=359 total_steps=20828810 (target 2e+07)`
- `2026-10-13 20:49:37 w3 R1 t0.5_h1.0_ma/s0 b3_at1e7 SNAPSHOT it=219 total_steps=10680834 (target 1e+07)`
- `2026-10-13 20:54:13 w3 R1 t0.5_h1.0_ma/s0 b3_at2e7 SNAPSHOT it=419 total_steps=20519476 (target 2e+07)`
- `2026-10-13 20:57:44 w2 R1 t0.5_h1.0_ma/s1 b3_at1e7 SNAPSHOT it=199 total_steps=10936181 (target 1e+07)`
- `2026-10-13 21:01:43 w2 R1 t0.5_h1.0_ma/s1 b3_at2e7 SNAPSHOT it=359 total_steps=20808668 (target 2e+07)`
- `2026-10-13 21:02:37 w1 R1 t0.5_h1.0_ma/s2 b3_at1e7 SNAPSHOT it=199 total_steps=10613201 (target 1e+07)`
- `2026-10-13 21:06:16 w1 R1 t0.5_h1.0_ma/s2 b3_at2e7 SNAPSHOT it=359 total_steps=20555267 (target 2e+07)`

## E8 1단계 (4점 × seed 20–24)

| point | seed | BC | train (1.1e8) | judge (det) | 예산 (근거 라벨) |
|---|---|---|---|---|---|
| a0 | 20 | done | done | done | 3e7 BUDGET_UNDERTRAINED |
| a1 | 20 | done | done | done | 3e7 BUDGET_UNDERTRAINED |
| a2 | 20 | done | done | done | 3e7 BUDGET_UNDERTRAINED |
| a3 | 20 | done | done | done | 3e7 BUDGET_UNDERTRAINED |
| a0 | 21 | done | done | done | 3e7 BUDGET_UNDERTRAINED |
| a1 | 21 | done | done | done | 3e7 BUDGET_UNDERTRAINED |
| a2 | 21 | done | done | done | 3e7 BUDGET_UNDERTRAINED |
| a3 | 21 | done | done | done | 3e7 BUDGET_UNDERTRAINED |
| a0 | 22 | done | done | done | 3e7 BUDGET_UNDERTRAINED |
| a1 | 22 | done | done | done | 3e7 BUDGET_UNDERTRAINED |
| a2 | 22 | done | done | done | 3e7 BUDGET_UNDERTRAINED |
| a3 | 22 | done | done | done | 3e7 BUDGET_UNDERTRAINED |
| a0 | 23 | done | done | done | 3e7 BUDGET_UNDERTRAINED |
| a1 | 23 | done | done | done | 3e7 BUDGET_UNDERTRAINED |
| a2 | 23 | done | done | done | 3e7 BUDGET_UNDERTRAINED |
| a3 | 23 | done | done | done | 3e7 BUDGET_UNDERTRAINED |
| a0 | 24 | done | done | done | 3e7 BUDGET_UNDERTRAINED |
| a1 | 24 | done | done | done | 3e7 BUDGET_UNDERTRAINED |
| a2 | 24 | done | done | done | 3e7 BUDGET_UNDERTRAINED |
| a3 | 24 | done | done | done | 3e7 BUDGET_UNDERTRAINED |

집계: bc done 20, judge done 20, train done 20

### E8 착취자 예산

- 규칙: R1 readout label == BUDGET_UNDERTRAINED → 3e7, 그 밖 → 1e7. readout 파일 `/data/hjhong/l2/newURP/artifacts/fs1/r1/readout.json` 존재: True
- `2026-10-13 22:36:23 w2 E8 JUDGE START a0/s20 try1 budget=3e7 (R1 label BUDGET_UNDERTRAINED) :: cd /data/hjhong/fs1jax/code_e6 && CUDA_VISIBLE_DEVICES=0 taskset -c 4-7 /data/hjhong/fs1jax/.venv-jax/bin/python -m shepherd.fs1_jax.train --out /data/hjhong/fs1jax/e8/a0/s20/judge_exploiter --iters 1000000 --total-steps 3e7 --B 256 --exploit /data/hjhong/fs1jax/e8/a0/s20/ckpt.pt --stack r4p --tau-scale 1.0 --a-scale 0.489962 --theta-scale 1.0 --aim cv --mu 0.35 --nu 1.0 --seed 315020`
- `2026-10-13 22:36:34 w3 E8 JUDGE START a1/s20 try1 budget=3e7 (R1 label BUDGET_UNDERTRAINED) :: cd /data/hjhong/fs1jax/code_e6 && CUDA_VISIBLE_DEVICES=0 taskset -c 8-11 /data/hjhong/fs1jax/.venv-jax/bin/python -m shepherd.fs1_jax.train --out /data/hjhong/fs1jax/e8/a1/s20/judge_exploiter --iters 1000000 --total-steps 3e7 --B 256 --exploit /data/hjhong/fs1jax/e8/a1/s20/ckpt.pt --stack r4p --tau-scale 0.8333333333 --a-scale 0.705545 --theta-scale 1.0 --aim cv --mu 0.35 --nu 1.0 --seed 315120`
- `2026-10-13 22:44:31 w1 E8 JUDGE START a2/s20 try1 budget=3e7 (R1 label BUDGET_UNDERTRAINED) :: cd /data/hjhong/fs1jax/code_e6 && CUDA_VISIBLE_DEVICES=0 taskset -c 0-3 /data/hjhong/fs1jax/.venv-jax/bin/python -m shepherd.fs1_jax.train --out /data/hjhong/fs1jax/e8/a2/s20/judge_exploiter --iters 1000000 --total-steps 3e7 --B 256 --exploit /data/hjhong/fs1jax/e8/a2/s20/ckpt.pt --stack r4p --tau-scale 0.6666666667 --a-scale 1.102414 --theta-scale 1.0 --aim cv --mu 0.35 --nu 1.0 --seed 315220`

## smoke 결과

- `2026-10-13 19:29:29 SMOKE_E8 physics (code_e6, FS1Env+fs1_jax.resolve, CPU): a0 tau 0.30/0.30 ticks 6 a_att 10.0214 | a1 0.25/0.25 ticks 5 a_att 14.4307 | a2 0.20/0.20 ticks 4 a_att 22.5480 | a3 0.15/0.15 ticks 3 a_att 40.0854 -> env.tau==fsm.tau==jaxP.tau, ticks 6/5/4/3, a_att match: ALL PASS`
- `2026-10-13 19:34:50 SMOKE_R1 (code 80afb2a, 2 iters, exploit e7b/t0.7_h1.0_cv/s0/ckpt.pt, seed 320000): rc=0, 20s, log 2 lines. config diff vs E7-b judge_exploiter: only out/seed/iters + new fields limiter_roe=a, limiter_inert=False (E7-c defaults, no-op; absent in E7-b config). Smoke outputs deleted.`
- `2026-10-13 19:34:50 SMOKE_E8 train (code_e6 0d36d2b, a3: BC 16 eps workers 4 cpu 12-15 rc=0; train 2 iters --init bc rc=0; det exploiter 2 iters jseed 315320 rc=0). config diff vs e1b/d0/s10 (train+judge): only iters/out/seed/init/tau_scale/a_scale. Smoke outputs deleted.`

## 실패·재시도·격리

- 없음

## 실행 명령 원본 (각 계열 첫 실행)

```
cd /data/hjhong/fs1jax/code && CUDA_VISIBLE_DEVICES=0 taskset -c 0-3 /data/hjhong/fs1jax/.venv-jax/bin/python -m shepherd.fs1_jax.train --out /data/hjhong/fs1jax/r1/t0.7_h1.0_cv/s0/b3 --iters 1000000 --total-steps 3e7 --B 256 --exploit /data/hjhong/fs1jax/e7b/t0.7_h1.0_cv/s0/ckpt.pt --stack r4p --tau-scale 0.7 --theta-scale 1.0 --aim cv --mu 0.35 --nu 1.0 --seed 325000
```
```
cd /data/hjhong/fs1jax/code && CUDA_VISIBLE_DEVICES=0 taskset -c 4-7 /data/hjhong/fs1jax/.venv-jax/bin/python -m shepherd.fs1_jax.train --out /data/hjhong/fs1jax/r1/t0.7_h1.0_cv/s0/b1 --iters 1000000 --total-steps 1e7 --B 256 --exploit /data/hjhong/fs1jax/e7b/t0.7_h1.0_cv/s0/ckpt.pt --stack r4p --tau-scale 0.7 --theta-scale 1.0 --aim cv --mu 0.35 --nu 1.0 --seed 320000
```
```
(cwd code_e6) CUDA_VISIBLE_DEVICES= taskset -c 12-15 /data/hjhong/fs1jax/.venv-jax/bin/python /data/hjhong/fs1jax/runs/bc_variant_e6.py 0.489962 1.0 1.0 cv --out /data/hjhong/fs1jax/e8/a0/s20/bc --episodes 3000 --workers 4 --seed 20 --stack r4p --mu 0.35 --nu 1.0
```
```
cd /data/hjhong/fs1jax/code_e6 && CUDA_VISIBLE_DEVICES=0 taskset -c 8-11 /data/hjhong/fs1jax/.venv-jax/bin/python -m shepherd.fs1_jax.train --out /data/hjhong/fs1jax/e8/a0/s20 --iters 1000000 --total-steps 1.1e8 --B 256 --stack r4p --distill-fire --tau-scale 1.0 --a-scale 0.489962 --theta-scale 1.0 --aim cv --mu 0.35 --nu 1.0 --seed 20 --init /data/hjhong/fs1jax/e8/a0/s20/bc/bc_snapshots.pt
```
```
cd /data/hjhong/fs1jax/code_e6 && CUDA_VISIBLE_DEVICES=0 taskset -c 4-7 /data/hjhong/fs1jax/.venv-jax/bin/python -m shepherd.fs1_jax.train --out /data/hjhong/fs1jax/e8/a0/s20/judge_exploiter --iters 1000000 --total-steps 3e7 --B 256 --exploit /data/hjhong/fs1jax/e8/a0/s20/ckpt.pt --stack r4p --tau-scale 1.0 --a-scale 0.489962 --theta-scale 1.0 --aim cv --mu 0.35 --nu 1.0 --seed 315020
```

## 재개 명령

남은 slot 은 작업자가 done/claim 으로 건너뛰며 이어서 처리한다. 중단된 작업자의 stale claim 을 먼저 지운다 (실행 중 작업이 없을 때만):
```
ssh server4
cd /data/hjhong/fs1jax
# 실행 중 학습이 없는지 확인: ps -ef | grep '[s]hepherd.fs1_jax.train'
find r1 e8 -maxdepth 3 -name '.claim*' -type d -exec rmdir {} +   # stale 잠금만 (done 있는 slot 은 영향 없음)
# 2회 실패 표시 (.fail*) 는 원인 확인 후에만 지운다
for w in 'x_w1 1 0-3' 'x_w2 2 4-7' 'x_w3 3 8-11'; do set -- $w; tmux new-session -d -s $1 "bash /data/hjhong/fs1jax/r1/_runs/night_worker.sh $2 $3"; sleep 3; done
tmux new-session -d -s x_e8bc 'bash /data/hjhong/fs1jax/r1/_runs/e8_bc.sh'   # BC 가 남았을 때만
```
- 주의: night_worker.sh 는 08:00 이후 새 slot (R1 작업·E8 train) 을 시작하지 않는다 (12시 이전 기준). 낮에 재개하려면 `past 0800` 조건을 확인할 것.
- E8 judge 는 readout.json 라벨이 생길 때까지 대기한다 (작업자 루프가 60 s 마다 재확인, 10:00 에 종료).

