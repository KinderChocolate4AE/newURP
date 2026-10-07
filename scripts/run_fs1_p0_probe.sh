#!/usr/bin/env bash
# P0 충실도·조건부 프로브 (server4, docs/126 §4 P0a/P0b; 선언 = 노트 2026-10-07d):
#   IN=/data/hjhong/l2 tmux new -d -s p0 'bash scripts/run_fs1_p0_probe.sh'
main() {
  set -euo pipefail
  cd "$(dirname "$0")/.."
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
  IN=${IN:?IN required}
  OUT=artifacts/fs1/p0
  notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='p0')" || true; }
  trap 'notify "P0 probe FAILED - check logs"' ERR
  mkdir -p "$OUT"
  python -u scripts/fs1_p0_fidelity_probe.py --stage1 "$IN/e3_in/stage1" \
      --e3b "$IN/e3b_in/phase1" --out-dir "$OUT" > "$OUT/probe.log" 2>&1
  flock /tmp/fs1_git.lock bash -c "git add '$OUT' \
      && git commit -m 'science(fs1): harvest P0 fidelity probe (docs/126 P0a/P0b)' \
                    -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>' \
      && git pull --rebase origin feat/scale-up-v2 && git push origin feat/scale-up-v2"
  notify "P0 probe pushed"
}
main "$@"; exit
