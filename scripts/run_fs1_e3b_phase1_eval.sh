#!/usr/bin/env bash
# E3b phase 1 평가 (server4, manifest `scripts/fs1_e3b_manifest.py`):
# cell 마다 방어 {mix5050, kfirst_rand} × exploiter 그룹 {자기, 교차, stage-1 구 exploiter 2종}
# 240판 paired → 판독 → 커밋·push.
#   IN=/data/hjhong/l2/e3b_in WORKERS=6 tmux new -d -s e3b1 'bash scripts/run_fs1_e3b_phase1_eval.sh'
# S1IN = stage-1 exploiter ckpt 루트 (교차 보고용, 이미 server4 에 있음).
main() {
  set -euo pipefail
  cd "$(dirname "$0")/.."
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
  IN=${IN:?IN required}
  S1IN=${S1IN:-/data/hjhong/l2/e3_in/stage1}
  WORKERS=${WORKERS:-6}
  OUT=artifacts/fs1/e3b/phase1
  notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='e3b1')" || true; }
  trap 'notify "E3b1 eval FAILED - check logs"' ERR
  H=$(python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_e3b_manifest import load; print(load()['manifest_hash'])")
  mkdir -p "$OUT"

  python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_e3b_manifest import CELLS, SEED0, STRIDE
for i, c in enumerate(CELLS): print(c['cell'], c['mu'], c['nu'], SEED0 + i*STRIDE)" |
  while read -r CELL MU NU SEED; do
    D="$OUT/$CELL"
    [ -f "$D/done" ] && continue
    mkdir -p "$D"
    for X in mix5050 kfirst_rand; do
      mkdir -p "$D/exploit_$X" && cp "$IN/$CELL/exploit_$X/log.jsonl" "$D/exploit_$X/"
    done
    python -u -m shepherd.fs1.eval run --ckpt "$IN/$CELL/exploit_mix5050/ckpt.pt" --out "$D/eval" \
        --workers "$WORKERS" --episodes 240 --seed "$SEED" --mu "$MU" --nu "$NU" \
        --manifest "$H" --ladder nominal --defenders mix5050 kfirst_rand --groups none --traj 2 \
        --exploiter "mix5050=$IN/$CELL/exploit_mix5050/ckpt.pt" \
                    "kfirst_rand=$IN/$CELL/exploit_kfirst_rand/ckpt.pt" \
                    "kfirst50=$S1IN/$CELL/exploit_kfirst50/ckpt.pt" \
                    "fin12_fb=$S1IN/$CELL/exploit_fin12_fb/ckpt.pt" > "$D/eval.log" 2>&1
    touch "$D/done"
    notify "E3b1 cell $CELL done"
  done

  python scripts/fs1_e3b_readout.py --root "$OUT" > "$OUT/readout.log" 2>&1
  flock /tmp/fs1_git.lock bash -c "git add '$OUT' \
      && git commit -m 'science(fs1): harvest E3b phase 1 (manifest $H)' \
      && git pull --rebase origin feat/scale-up-v2 && git push origin feat/scale-up-v2"
  notify "E3b1 eval pushed"
}
main "$@"; exit
