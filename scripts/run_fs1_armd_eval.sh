#!/usr/bin/env bash
# arm D 정본 평가 (server4, manifest `fs1_armd_manifest.build_armd`, docs/128):
# (cell, seed) 마다 동결 스택-방어 (sto 판정) vs 전용 judge exploiter 240판 paired → 판독 → push.
#   tmux new -d -s armd 'cd <repo> && source .venv-l2/bin/activate && IN=/data/hjhong/l2/e3b_in/armd bash scripts/run_fs1_armd_eval.sh'
main() {
  set -euo pipefail
  cd "$(dirname "$0")/.."
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
  IN=${IN:?IN required}
  WORKERS=${WORKERS:-6}
  OUT=artifacts/fs1/armd
  notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='armd')" || true; }
  trap 'notify "armd eval FAILED - check logs"' ERR
  H=$(python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_armd_manifest import load_armd; print(load_armd()['manifest_hash'])")
  mkdir -p "$OUT"

  python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_armd_manifest import CELLS, SEEDS, SEED0, STRIDE
for i, c in enumerate(CELLS):
    for s in SEEDS: print(c['cell'], c['mu'], c['nu'], s, SEED0 + i*STRIDE)" |
  while read -r CELL MU NU S SEED; do
    D="$OUT/$CELL/s$S"
    [ -f "$D/done" ] && continue
    mkdir -p "$D/judge_exploiter"
    cp "$IN/$CELL/s$S/log.jsonl" "$D/"
    cp "$IN/$CELL/s$S/judge_exploiter/log.jsonl" "$D/judge_exploiter/"
    python -u -m shepherd.fs1.eval run --ckpt "$IN/$CELL/s$S/ckpt.pt" --out "$D/eval" \
        --workers "$WORKERS" --episodes 240 --seed "$SEED" --mu "$MU" --nu "$NU" --stack r4p \
        --def-stack 4 --manifest "$H" --ladder nominal --defenders learned_sto learned_det \
        --groups none --traj 2 \
        --exploiter "judge=$IN/$CELL/s$S/judge_exploiter/ckpt.pt" > "$D/eval.log" 2>&1
    touch "$D/done"
  done

  python scripts/fs1_armd_readout.py --root "$OUT" > "$OUT/readout.log" 2>&1
  flock /tmp/fs1_git.lock bash -c "git add '$OUT' \
      && git commit -m 'science(fs1): harvest arm D canonical eval (manifest $H)' \
                    -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>' \
      && git pull --rebase origin feat/scale-up-v2 && git push origin feat/scale-up-v2"
  notify "armd eval pushed"
}
main "$@"; exit
