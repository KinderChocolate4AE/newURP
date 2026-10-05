#!/usr/bin/env bash
# E3 stage 1 평가 (server4, manifest v1.2 `scripts/fs1_e3_manifest.py`):
# JAX 가 학습한 exploiter ckpt (IN=<root>/<cell>/exploit_{kfirst50,fin12_fb}/{ckpt.pt,log.jsonl})
# 를 받아 cell 마다 ① ceiling 평가 240판 (paired) ② D3 진단 c5/fwd 96판 → 판독 → 커밋·push.
#   IN=/data/hjhong/l2/e3_in WORKERS=10 tmux new -d -s e3s1 'bash scripts/run_fs1_e3_stage1_eval.sh'
# main() 래핑 — 실행 중 git pull 안전. git 단계 flock.
main() {
  set -euo pipefail
  cd "$(dirname "$0")/.."
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
  IN=${IN:?IN required (JAX ckpt root)}
  WORKERS=${WORKERS:-10}
  OUT=artifacts/fs1/e3/stage1
  notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='e3s1')" || true; }
  trap 'notify "E3 stage1 eval FAILED - check logs"' ERR
  H=$(python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_e3_manifest import load; print(load()['manifest_hash'])")
  mkdir -p "$OUT"

  python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_e3_manifest import load, SEED0, CELL_SEED_STRIDE
for i, c in enumerate(load()['grid']['cells']): print(c['cell'], c['mu'], c['nu'], SEED0 + i*CELL_SEED_STRIDE)" |
  while read -r CELL MU NU SEED; do
    D="$OUT/$CELL"
    [ -f "$D/stage1_cell.done" ] && continue
    mkdir -p "$D"
    for X in kfirst50 fin12_fb; do
      cp "$IN/$CELL/exploit_$X/log.jsonl" "$D/exploit_$X/" 2>/dev/null || { mkdir -p "$D/exploit_$X"; cp "$IN/$CELL/exploit_$X/log.jsonl" "$D/exploit_$X/"; }
    done
    CK="$IN/$CELL/exploit_kfirst50/ckpt.pt"
    python -u -m shepherd.fs1.eval run --ckpt "$CK" --out "$D/eval" --workers "$WORKERS" \
        --episodes 240 --seed "$SEED" --mu "$MU" --nu "$NU" --manifest "$H" --ladder nominal \
        --defenders kfirst50 fin12_fb --groups ladder --traj 2 \
        --exploiter "kfirst50=$IN/$CELL/exploit_kfirst50/ckpt.pt" \
                    "fin12_fb=$IN/$CELL/exploit_fin12_fb/ckpt.pt" > "$D/eval.log" 2>&1
    python -u -m shepherd.fs1.eval run --ckpt "$CK" --out "$D/diag" --workers "$WORKERS" \
        --episodes 96 --seed "$SEED" --mu "$MU" --nu "$NU" --manifest "$H" --ladder nominal \
        --defenders c5_fb fwd_fb --groups ladder --traj 2 > "$D/diag.log" 2>&1
    touch "$D/stage1_cell.done"
    notify "E3 stage1 cell $CELL done"
  done

  python scripts/fs1_e3_stage1_readout.py --root "$OUT" > "$OUT/readout.log" 2>&1
  flock /tmp/fs1_git.lock bash -c "git add '$OUT' \
      && git commit -m 'science(fs1): harvest E3 stage 1 ceilings + diagnostics (manifest $H)' \
      && git pull --rebase origin feat/scale-up-v2 && git push origin feat/scale-up-v2"
  notify "E3 stage1 eval pushed"
}
main "$@"; exit
