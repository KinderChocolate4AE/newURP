#!/usr/bin/env bash
# arm C-1 정본 평가 (server4, manifest `fs1_armc1_manifest.build_armc1`, docs/127):
# (cell, seed) 마다 동결 증류-방어 vs 전용 judge exploiter 240판 paired → 판독 → push.
#   IN=/data/hjhong/l2/e3b_in/armc1 WORKERS=6 tmux new -d -s armc1 'IN=... bash scripts/run_fs1_armc1_eval.sh'
main() {
  set -euo pipefail
  cd "$(dirname "$0")/.."
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
  IN=${IN:?IN required}
  WORKERS=${WORKERS:-6}
  OUT=artifacts/fs1/armc1
  notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='armc1')" || true; }
  trap 'notify "armc1 eval FAILED - check logs"' ERR
  H=$(python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_armc1_manifest import load_armc1; print(load_armc1()['manifest_hash'])")
  mkdir -p "$OUT"

  python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_armc1_manifest import CELLS, SEEDS, SEED0, STRIDE
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
        --manifest "$H" --ladder nominal --defenders learned_det learned_sto --groups none --traj 2 \
        --exploiter "judge=$IN/$CELL/s$S/judge_exploiter/ckpt.pt" > "$D/eval.log" 2>&1
    touch "$D/done"
  done

  python scripts/fs1_armc1_readout.py --root "$OUT" > "$OUT/readout.log" 2>&1
  flock /tmp/fs1_git.lock bash -c "git add '$OUT' \
      && git commit -m 'science(fs1): harvest arm C-1 canonical eval (manifest $H)' \
                    -m 'Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>' \
      && git pull --rebase origin feat/scale-up-v2 && git push origin feat/scale-up-v2"
  notify "armc1 eval pushed"
}
main "$@"; exit
