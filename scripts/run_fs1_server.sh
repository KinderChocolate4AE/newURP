#!/usr/bin/env bash
# FS1 동시학습 1차 실행 (서버): 학습 → 로그 커밋 → push. 세션 자동 종료.
#   tmux new -d -s fs1 'bash scripts/run_fs1_server.sh'
#   진행 확인: tail -f artifacts/fs1/run0/log.jsonl
# ckpt.pt (pool 스냅샷 포함, 수백 MB 가능) 는 커밋하지 않고 서버에 남긴다.
set -euo pipefail
cd "$(dirname "$0")/.."
notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='fs1')" || true; }
trap 'notify "FS1 FAILED - check logs"' ERR

OUT=artifacts/fs1/run0
mkdir -p "$OUT"
python -u -m shepherd.fs1.train --out "$OUT" --workers 22 --iters 1200 \
    --steps-per-worker 4096 > "$OUT/train.log" 2>&1

git add "$OUT/log.jsonl" "$OUT/config.json"
git commit -m "science(fs1): harvest FS1 run0 co-training log"
git pull --rebase origin feat/scale-up-v2
git push origin feat/scale-up-v2
notify "FS1 run0 pushed"
