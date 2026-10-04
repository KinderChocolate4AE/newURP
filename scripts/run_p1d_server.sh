#!/usr/bin/env bash
# P1d 전체 자동 실행 (서버): 2-shard 병렬 → readout → 커밋 → push. 세션 자동 종료.
#   tmux new -d -s p1d 'bash scripts/run_p1d_server.sh'
set -euo pipefail
cd "$(dirname "$0")/.."
notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='p1d')" || true; }
trap 'notify "P1d FAILED - check logs"' ERR

mkdir -p artifacts/p1d_runway
python -u -m scripts.p1d_runway --run --shard 0/2 \
    > artifacts/p1d_runway/shard0.log 2>&1 &
P0=$!
python -u -m scripts.p1d_runway --run --shard 1/2 \
    > artifacts/p1d_runway/shard1.log 2>&1 &
P1=$!
wait "$P0"
wait "$P1"

python -m scripts.p1d_runway --readout 2>&1 | tee artifacts/p1d_runway/readout.log
git add artifacts/p1d_runway/
git commit -m "science(ladder): harvest P1d forward-limiter runway probe"
git pull --rebase origin feat/scale-up-v2   # 로컬 커밋과 엇갈림 방지 (P1c 교훈)
git push origin feat/scale-up-v2
notify "P1d harvest pushed"
