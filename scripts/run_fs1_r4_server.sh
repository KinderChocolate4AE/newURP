#!/usr/bin/env bash
# FS1 r4 (docs/123 §9) 한 seed 전 과정: BC → MAPPO+PFSP 학습 → 학습 로그 push → 봉인 평가
# (exploiter 2 + v1 + v2 addendum, scripts/run_fs1_eval_server.sh) → push. seed 별 병렬:
#   for s in 0 1 2; do SEED=$s tmux new -d -s fs1r4s$s 'bash scripts/run_fs1_r4_server.sh'; done
# 코어: seed 당 WORKERS(6) + torch 1 = 7 → 3 seed 21. 반복 배치 = 6 × 8192 = r3 의 12 × 4096 과 같음.
# main() 으로 감싸 bash 가 파일 전체를 먼저 읽는다 — 실행 중 git pull 로 스크립트가 바뀌어도 안전.
main() {
  set -euo pipefail
  cd "$(dirname "$0")/.."
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
  SEED=${SEED:?SEED required}
  WORKERS=${WORKERS:-6}
  OUT=artifacts/fs1/r4_s$SEED
  notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='fs1r4')" || true; }
  trap 'notify "FS1 r4 seed '"$SEED"' FAILED - check logs"' ERR
  mkdir -p "$OUT"
  python -u -m shepherd.fs1.bc --out "$OUT/bc" --episodes 3000 --workers "$WORKERS" --seed "$SEED" \
      > "$OUT/bc.log" 2>&1
  python -u -m shepherd.fs1.train --out "$OUT" --workers "$WORKERS" --torch-threads 1 --seed "$SEED" \
      --init "$OUT/bc/bc_snapshots.pt" --iters 100000 --total-steps 1.1e8 --steps-per-worker 8192 \
      > "$OUT/train.log" 2>&1
  flock /tmp/fs1_git.lock bash -c "git add '$OUT/log.jsonl' '$OUT/config.json' '$OUT/bc/bc_report.json' \
      && git commit -m 'science(fs1): harvest FS1 r4 seed $SEED co-training log' \
      && git pull --rebase origin feat/scale-up-v2 && git push origin feat/scale-up-v2"
  RUN="$OUT" WORKERS="$WORKERS" TORCH_THREADS=1 bash scripts/run_fs1_eval_server.sh
}
main "$@"; exit
