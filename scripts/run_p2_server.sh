#!/usr/bin/env bash
# P2 전체 자동 실행 (서버): controls → seed 0/1 병렬 학습 → readout → 커밋 → push.
# 사용법 (레포 루트에서):
#   tmux new -d -s p2 'bash scripts/run_p2_server.sh'
# tmux 세션은 스크립트 종료와 함께 자동으로 닫힌다. 진행 확인: tmux attach -t p2
# 또는 tail -f artifacts/p2_limiter/seed{0,1}.log  (ntfy 로 시작/종료 알림).
set -euo pipefail
cd "$(dirname "$0")/.."
export CUBLAS_WORKSPACE_CONFIG=:4096:8

notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='p2-lim')" || true; }
trap 'notify "P2 FAILED - check logs"' ERR

mkdir -p artifacts/p2_limiter
python -u -m scripts.p2_limiter --controls 2>&1 | tee artifacts/p2_limiter/controls.log

python -u -m scripts.p2_limiter --run --seed 0 --device cuda \
    > artifacts/p2_limiter/seed0.log 2>&1 &
P0=$!
python -u -m scripts.p2_limiter --run --seed 1 --device cuda \
    > artifacts/p2_limiter/seed1.log 2>&1 &
P1=$!
wait "$P0"
wait "$P1"

python -m scripts.p2_limiter --readout 2>&1 | tee artifacts/p2_limiter/readout.log

git add artifacts/p2_limiter/
git commit -m "science(marl): harvest P2 limiter-only v2"
git push origin feat/scale-up-v2
notify "P2 harvest pushed - readout ready"
