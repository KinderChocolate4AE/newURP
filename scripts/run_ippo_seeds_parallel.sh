#!/usr/bin/env bash
# Parallel multi-seed IPPO launcher (Phase 2B run 2+; lab server, one GPU).
#
# PRINCIPLE: one OS process per seed. They share the GPU via CUDA's normal
# multi-process time-slicing (VRAM ~0.5 GB each; our kernels are tiny MLPs so
# GPU contention is ~zero). The REAL shared resource is CPU (the env loop is
# single-threaded per process), so each process gets a BLAS-thread cap and
# nice -n 10 -- worst case ~(1+THREADS)*n_seeds cores, yielding to other
# users automatically.
#
# SAFETY: refuses to launch unless HEAD CONTAINS $REQUIRED_COMMIT (ancestor
# check -- robust to later commits; prevents the run-2a incident: stale code
# silently re-running old results because git pull was skipped). Per-seed
# stdout goes to $OUT/seed<N>.launch.log; exit codes are collected; the
# last-3-eval DoD summary is printed at the end.
#
# Usage (inside tmux on the server):
#   bash scripts/run_ippo_seeds_parallel.sh
#   GPU=0 SEEDS="0 1 2 3 4" OUT=results/ippo_run3 bash scripts/run_ippo_seeds_parallel.sh
set -euo pipefail

REQUIRED_COMMIT="${REQUIRED_COMMIT:-cef170f}"   # 2B stabilization recipe
GPU="${GPU:-1}"
OUT="${OUT:-results/ippo_run2}"
SEEDS_STR="${SEEDS:-0 1 2}"
THREADS="${THREADS:-2}"   # per-process BLAS cap: 3 seeds x (1 env + 2 BLAS) = ~9 cores max
read -r -a SEEDS_ARR <<< "$SEEDS_STR"

cd "$(dirname "$0")/.."                       # repo root (script lives in scripts/)
if [ -f ".venv-l2/bin/activate" ]; then
  # shellcheck disable=SC1091
  source ".venv-l2/bin/activate"
fi

if ! git merge-base --is-ancestor "$REQUIRED_COMMIT" HEAD 2>/dev/null; then
  echo "FAIL: HEAD $(git rev-parse --short HEAD) does not contain $REQUIRED_COMMIT"
  echo "      -- git pull --ff-only first (stale-code guard)"
  exit 1
fi

echo "== GPU $GPU status (want: enough free VRAM; util does not matter much) =="
command -v nvidia-smi >/dev/null && \
  nvidia-smi --id="$GPU" --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv || true
echo "== load: $(uptime | sed 's/.*load average/load average/') / $(nproc) cores =="

export CUDA_VISIBLE_DEVICES="$GPU"
export WANDB_MODE="${WANDB_MODE:-offline}"
export WANDB_DIR="${WANDB_DIR:-$(cd .. && pwd)/wandb}"
export OMP_NUM_THREADS="$THREADS" MKL_NUM_THREADS="$THREADS" OPENBLAS_NUM_THREADS="$THREADS"
export PYTHONUNBUFFERED=1                     # live per-seed logs (stdout to file is block-buffered otherwise)

mkdir -p "$OUT"
PIDS=()
for s in "${SEEDS_ARR[@]}"; do
  LOG="$OUT/seed${s}.launch.log"
  echo "[launch] seed $s (GPU $GPU, threads<=$THREADS, nice 10) -> $LOG"
  nice -n 10 python -m shepherd.scripts.train_ippo \
      --config configs/l2_ippo.yaml --device cuda \
      --seed "$s" --output "$OUT" > "$LOG" 2>&1 &
  PIDS+=("$!")
  sleep 5                                     # stagger first-write/init races
done
echo "PIDs: ${PIDS[*]}"
echo "watch progress:  tail -f $OUT/seed${SEEDS_ARR[0]}.launch.log"

FAIL=0
for i in "${!PIDS[@]}"; do
  if wait "${PIDS[$i]}"; then
    echo "[done] seed ${SEEDS_ARR[$i]} OK"
  else
    echo "[FAIL] seed ${SEEDS_ARR[$i]} exited nonzero -- see $OUT/seed${SEEDS_ARR[$i]}.launch.log"
    FAIL=1
  fi
done

echo
echo "=== Phase 2B DoD summary (last-3-eval mean margin > 0 per seed) ==="
for s in "${SEEDS_ARR[@]}"; do
  python - "$OUT/seed${s}/summary.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
print(f"seed {d['seed']}: last3_margin={d['dod_margin_last3']:+.3f} "
      f"last3_return={d['return_mean_last3']:.3f} (final point {d['dod_margin']:+.3f})")
PY
done
exit "$FAIL"
