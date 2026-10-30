#!/usr/bin/env bash
# E9 비이상성 접힘 프로브 (server4 CPU 단일 프로세스, docs/144, manifest fs1_e9_manifest).
#   tmux new -d -s e9_probe 'cd <repo> && source .venv-l2/bin/activate && IN=/data/hjhong/l2 bash scripts/run_fs1_e9_probe.sh'
main() {
  set -euo pipefail
  cd "$(dirname "$0")/.."
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
  IN=${IN:?IN required}
  OUT=artifacts/fs1/e9
  notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='e9')" || true; }
  trap 'notify "E9 probe FAILED - check logs"' ERR
  flock /tmp/fs1_git.lock git pull -q --rebase origin feat/scale-up-v2 || true
  python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_e9_manifest import load; print(load()['manifest_hash'])"
  mkdir -p "$OUT"
  python -u scripts/fs1_e7_probe.py --stage1 "$IN/e3_in/stage1" --e3b "$IN/e3b_in/phase1" \
      --out-dir "$OUT" --grid e9 > "$OUT/probe.log" 2>&1
  python scripts/fs1_e9_readout.py --dir "$OUT" --e4-dir artifacts/fs1/e4 > "$OUT/readout.log" 2>&1
  flock /tmp/fs1_git.lock bash -c "git add '$OUT' \
      && git commit -m 'science(fs1): harvest E9 non-ideality fold probe (docs/144)' \
                    -m 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>' \
      && git pull --rebase origin feat/scale-up-v2 && git push origin feat/scale-up-v2"
  notify "E9 probe pushed"
}
main "$@"; exit
