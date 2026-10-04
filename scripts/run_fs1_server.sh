#!/usr/bin/env bash
# FS1 동시학습 (서버): BC 초기화 → MAPPO+PFSP 학습 → 로그 커밋 → push. 세션 자동 종료.
#   WORKERS=12 tmux new -d -s fs1 'bash scripts/run_fs1_server.sh'
#   진행 확인: tail -f artifacts/fs1/run2/log.jsonl
# 총 CPU = WORKERS + 2 (메인 torch 2 스레드). BLAS 스레드는 전부 1 로 고정 — 공용 서버.
# ckpt.pt (pool 스냅샷 포함, 수백 MB 가능) 는 커밋하지 않고 서버에 남긴다.
set -euo pipefail
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
WORKERS=${WORKERS:-12}
notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='fs1')" || true; }
trap 'notify "FS1 FAILED - check logs"' ERR

OUT=artifacts/fs1/run2
mkdir -p "$OUT"
# 1) BC 초기화 (방어자 = scripted FCS 방어 모방; 공격자는 autopilot + residual 0 에서 출발)
python -u -m shepherd.fs1.bc --out "$OUT/bc" --episodes 3000 --workers "$WORKERS" \
    > "$OUT/bc.log" 2>&1
# 2) MAPPO + PFSP 동시학습
python -u -m shepherd.fs1.train --out "$OUT" --workers "$WORKERS" --torch-threads 2 \
    --init "$OUT/bc/bc_snapshots.pt" --iters 100000 --total-steps 1.1e8 \
    --steps-per-worker 4096 > "$OUT/train.log" 2>&1

git add "$OUT/log.jsonl" "$OUT/config.json" "$OUT/bc/bc_report.json"
git commit -m "science(fs1): harvest FS1 run2 co-training log"
git pull --rebase origin feat/scale-up-v2
git push origin feat/scale-up-v2
notify "FS1 run2 pushed"
