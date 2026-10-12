# LAB_LOG — night/2026-10-13

## 환경 점검 (02:37–02:43 KST, 사람 감시 중)
| # | 항목 | 결과 | 비고 |
|---|---|---|---|
| 1 | 서버 접속 (ssh -F /tmp/sshcfg server4) | OK | hostname=server-4, GPU1 0% / 24 MiB, 24 cores, RAM free ~106 GB |
| 2 | /data/hjhong/night + taskset tmux night_test | OK | has-session -t =night_test → OK, kill 후 부재 확인 |
| 3 | 서버 Python + GPU1 | OK | fs1jax/.venv-jax (실행만): jax 0.6.2, CUDA_VISIBLE_DEVICES=1 → CudaDevice(0), matmul OK. flax/optax 없음 → 순수 JAX 로 MLP+Adam 직접 작성 |
| 4 | 로컬→서버 전송 | OK | scp OK, tar czf - \| ssh 'tar xzf -' OK. rsync 없음 → tar-over-ssh 로 전체 트리 전송 |
| 5 | 로컬 Python | OK | py3.12 .venv: jax[cpu] 0.6.2, numpy, matplotlib; PYTHONIOENCODING=utf-8 한글 출력 OK |
| 6 | git 첫 커밋 + push (night/2026-10-13) | OK | origin (https) 에 새 브랜치 push, upstream 설정 |
| 7 | 백그라운드 실행 + 대기 | OK | 로컬 run_in_background 30 s → 완료 알림 수신. 서버: taskset tmux night_bgtest (sleep 30 → done 파일) + 로컬 until-ssh-test-f 폴링 background → 완료 알림. 밤새 이 방식 사용 |

## 실험 로그 (가설 | 설정 | 결과 | 판단)
