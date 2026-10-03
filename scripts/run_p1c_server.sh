#!/usr/bin/env bash
# P1c 전체 자동 실행 (서버): 2-shard 병렬 → readout → 커밋 → push. 세션 자동 종료.
#   tmux new -d -s p1c 'bash scripts/run_p1c_server.sh'
set -euo pipefail
cd "$(dirname "$0")/.."
notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='p1c')" || true; }
trap 'notify "P1c FAILED - check logs"' ERR

mkdir -p artifacts/p1c_standoff
python -u -m scripts.p1c_standoff --run --shard 0/2 \
    > artifacts/p1c_standoff/shard0.log 2>&1 &
P0=$!
python -u -m scripts.p1c_standoff --run --shard 1/2 \
    > artifacts/p1c_standoff/shard1.log 2>&1 &
P1=$!
wait "$P0"
wait "$P1"

python -m scripts.p1c_standoff --readout 2>&1 | tee artifacts/p1c_standoff/readout.log
git add artifacts/p1c_standoff/
git commit -m "science(ladder): harvest P1c standoff probe"
git push origin feat/scale-up-v2
notify "P1c harvest pushed"
