#!/usr/bin/env bash
# E3b phase 2 평가 (server4, manifest `fs1_e3b_manifest.build_p2`):
# (cell, arm, seed) 마다 동결 학습 방어 vs 전용 judge exploiter 240판 paired → 판독 → push.
#   IN=/data/hjhong/l2/e3b_in/phase2 WORKERS=6 tmux new -d -s e3b2 'bash scripts/run_fs1_e3b_phase2_eval.sh'
main() {
  set -euo pipefail
  cd "$(dirname "$0")/.."
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
  IN=${IN:?IN required}
  WORKERS=${WORKERS:-6}
  OUT=artifacts/fs1/e3b/phase2
  notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='e3b2')" || true; }
  trap 'notify "E3b2 eval FAILED - check logs"' ERR
  H=$(python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_e3b_manifest import load_p2; print(load_p2()['manifest_hash'])")
  mkdir -p "$OUT"

  python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_e3b_manifest import P2_CELLS, P2_SEEDS
for i, c in enumerate(P2_CELLS):
    for arm in ('armA', 'armB'):
        for s in P2_SEEDS: print(c['cell'], c['mu'], c['nu'], arm, s, 270000 + i*1000)" |
  while read -r CELL MU NU ARM S SEED; do
    D="$OUT/$CELL/$ARM/s$S"
    [ -f "$D/done" ] && continue
    mkdir -p "$D/judge_exploiter"
    cp "$IN/$CELL/$ARM/s$S/log.jsonl" "$D/"
    cp "$IN/$CELL/$ARM/s$S/judge_exploiter/log.jsonl" "$D/judge_exploiter/"
    python -u -m shepherd.fs1.eval run --ckpt "$IN/$CELL/$ARM/s$S/ckpt.pt" --out "$D/eval" \
        --workers "$WORKERS" --episodes 240 --seed "$SEED" --mu "$MU" --nu "$NU" --stack r4p \
        --manifest "$H" --ladder nominal --defenders learned_det learned_sto --groups none --traj 2 \
        --exploiter "judge=$IN/$CELL/$ARM/s$S/judge_exploiter/ckpt.pt" > "$D/eval.log" 2>&1
    touch "$D/done"
  done

  python scripts/fs1_e3b_p2_readout.py --root "$OUT" > "$OUT/readout.log" 2>&1
  flock /tmp/fs1_git.lock bash -c "git add '$OUT' \
      && git commit -m 'science(fs1): harvest E3b phase 2 (manifest $H)' \
      && git pull --rebase origin feat/scale-up-v2 && git push origin feat/scale-up-v2"
  notify "E3b2 eval pushed"
}
main "$@"; exit
