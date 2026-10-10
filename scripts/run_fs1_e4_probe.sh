#!/usr/bin/env bash
# E4 ρ-collapse 프로브 (server4 CPU 단일 프로세스, docs/133, manifest fs1_e4_manifest). AMI 종료를 기다린 뒤 시작
# (CPU 상한: WORKERS 6 + 이 프로세스가 겹치지 않게).
#   tmux new -d -s e4_probe 'cd <repo> && source .venv-l2/bin/activate && IN=/data/hjhong/l2 bash scripts/run_fs1_e4_probe.sh'
main() {
  set -euo pipefail
  cd "$(dirname "$0")/.."
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
  IN=${IN:?IN required}
  OUT=artifacts/fs1/e4
  notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='e4')" || true; }
  trap 'notify "E4 probe FAILED - check logs"' ERR
  while [ ! -f artifacts/fs1/ami/readout.json ]; do sleep 120; done      # AMI 판독 = AMI 종료
  flock /tmp/fs1_git.lock git pull -q --rebase origin feat/scale-up-v2 || true
  python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_e4_manifest import load; print(load()['manifest_hash'])"
  mkdir -p "$OUT"
  python -u scripts/fs1_e7_probe.py --stage1 "$IN/e3_in/stage1" --e3b "$IN/e3b_in/phase1" \
      --out-dir "$OUT" --grid e4 --coop > "$OUT/probe.log" 2>&1
  python scripts/fs1_e4_readout.py --dir "$OUT" > "$OUT/readout.log" 2>&1
  flock /tmp/fs1_git.lock bash -c "git add '$OUT' \
      && git commit -m 'science(fs1): harvest E4 rho-collapse probe (docs/133)' \
                    -m 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>' \
      && git pull --rebase origin feat/scale-up-v2 && git push origin feat/scale-up-v2"
  notify "E4 probe pushed"
}
main "$@"; exit
