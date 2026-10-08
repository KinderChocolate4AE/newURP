#!/usr/bin/env bash
# E7-a 프로브 (server4 CPU, docs/129 §2, manifest fs1_e7_manifest.py):
#   tmux new -d -s e7a 'cd <repo> && source .venv-l2/bin/activate && IN=/data/hjhong/l2 bash scripts/run_fs1_e7_probe.sh'
main() {
  set -euo pipefail
  cd "$(dirname "$0")/.."
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
  IN=${IN:?IN required}
  OUT=artifacts/fs1/e7a
  notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='e7a')" || true; }
  trap 'notify "E7-a probe FAILED - check logs"' ERR
  python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_e7_manifest import load_e7a; print(load_e7a()['manifest_hash'])"
  mkdir -p "$OUT"
  python -u scripts/fs1_e7_probe.py --stage1 "$IN/e3_in/stage1" \
      --e3b "$IN/e3b_in/phase1" --out-dir "$OUT" > "$OUT/probe.log" 2>&1
  flock /tmp/fs1_git.lock bash -c "git add '$OUT' \
      && git commit -m 'science(fs1): harvest E7-a net-physics probe (docs/129)' \
                    -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>' \
      && git pull --rebase origin feat/scale-up-v2 && git push origin feat/scale-up-v2"
  notify "E7-a probe pushed"
}
main "$@"; exit
