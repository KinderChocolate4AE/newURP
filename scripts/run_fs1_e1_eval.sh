#!/usr/bin/env bash
# E1 전이 사다리 정본 평가 (server4 CPU, manifest fs1_e1_manifest, docs/134): 착취자가 준비된 slot 부터
# learned_det / learned_sto × {det, sto exploiter} 240판 paired → 전부 끝나면 판독 → push. 반복 실행 안전 (done 표시).
#   tmux new -d -s e1_eval 'cd <repo> && source .venv-l2/bin/activate && IN=/data/hjhong/fs1jax/e1 bash scripts/run_fs1_e1_eval.sh'
main() {
  set -euo pipefail
  cd "$(dirname "$0")/.."
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
  IN=${IN:?IN required}
  WORKERS=${WORKERS:-6}
  OUT=artifacts/fs1/e1
  notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='e1')" || true; }
  trap 'notify "E1 eval FAILED - check logs"' ERR
  H=$(python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_e1_manifest import load; print(load()['manifest_hash'])")
  ROWS=$(python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_e1_manifest import LADDER, PAIR, SEEDS, SEED0, STRIDE, N
for i, p in enumerate(LADDER + PAIR):
    for s in SEEDS: print(p['name'], p['tau_scale'], s, SEED0 + i*STRIDE, N)")
  while true; do
    left=0
    while read -r PT TAU S SEED NEP; do
      D="$OUT/$PT/s$S"; SRC="$IN/$PT/s$S"
      [ -f "$D/done" ] && continue
      left=$((left + 1))
      [ -f "$SRC/judge_exploiter/done" ] && [ -f "$SRC/judge_exploiter_sto/done" ] || continue
      mkdir -p "$D/judge_exploiter" "$D/judge_exploiter_sto"
      cp "$SRC/log.jsonl" "$D/"; cp "$SRC/judge_exploiter/log.jsonl" "$D/judge_exploiter/"
      cp "$SRC/judge_exploiter_sto/log.jsonl" "$D/judge_exploiter_sto/"
      python -u -m shepherd.fs1.eval run --ckpt "$SRC/ckpt.pt" --out "$D/eval" \
          --workers "$WORKERS" --episodes "$NEP" --seed "$SEED" --mu 0.35 --nu 1.0 --stack r4p \
          --tau-scale "$TAU" --theta-scale 1.0 --aim cv --coop-window --env-seed 0 \
          --manifest "$H" --ladder nominal --defenders learned_det learned_sto --groups none --traj 2 \
          --exploiter "judge=$SRC/judge_exploiter/ckpt.pt" "judge_sto=$SRC/judge_exploiter_sto/ckpt.pt" \
          > "$D/eval.log" 2>&1
      touch "$D/done"
    done <<< "$ROWS"
    [ "$left" -eq 0 ] && break
    sleep 600
  done
  python scripts/fs1_e1_readout.py --root "$OUT" > "$OUT/readout.log" 2>&1
  flock /tmp/fs1_git.lock bash -c "git add '$OUT' \
      && git commit -m 'science(fs1): harvest E1 transition ladder canonical eval (manifest $H)' \
                    -m 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>' \
      && git pull --rebase origin feat/scale-up-v2 && git push origin feat/scale-up-v2"
  notify "E1 eval pushed"
}
main "$@"; exit
