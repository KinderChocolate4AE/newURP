#!/usr/bin/env bash
# E8 고정 χ 공격자 가속 스윕 평가 (server4 CPU, manifest fs1_e8_manifest, docs/139). 생산 경로: $IN/<a_i>/s<seed>/ (ckpt.pt, judge_exploiter/done).
#   tmux new -d -s e8_eval 'cd <repo> && source .venv-l2/bin/activate && IN=/data/hjhong/fs1jax/e8 bash scripts/run_fs1_e8_eval.sh'
main() {
  set -euo pipefail
  cd "$(dirname "$0")/.."
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
  IN=${IN:?IN required}
  WORKERS=${WORKERS:-6}
  OUT=artifacts/fs1/e8
  notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='e8')" || true; }
  flock /tmp/fs1_git.lock git pull -q --rebase origin feat/scale-up-v2 || true
  H=$(python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_e8_manifest import load; print(load()['manifest_hash'])")
  STAGE=${STAGE:-1}   # v1.1: 2 = seed 20–27 (2단계 조건부)
  ROWS=$(python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_e8_manifest import POINTS, SEEDS, SEEDS_STAGE2, SEED0, STRIDE, N
for i, p in enumerate(POINTS):
    for s in SEEDS + (SEEDS_STAGE2 if '$STAGE' == '2' else []): print(p['name'], p['tau_scale'], p['a_scale'], s, SEED0 + i*STRIDE, N)")
  while true; do
    left=0
    while read -r PT TAU AS S SEED NEP; do
      D="$OUT/$PT/s$S"; SRC="$IN/$PT/s$S"; E="$D/eval_judge"
      [ -f "$E/done" ] && continue
      left=$((left + 1))
      [ -f "$SRC/judge_exploiter/done" ] || continue
      mkdir -p "$D/judge_exploiter" "$E"
      cp "$SRC/log.jsonl" "$D/"; cp "$SRC/judge_exploiter/log.jsonl" "$D/judge_exploiter/"
      if ! python -u -m shepherd.fs1.eval run --ckpt "$SRC/ckpt.pt" --out "$E" --workers "$WORKERS" --episodes "$NEP" \
          --seed "$SEED" --mu 0.35 --nu 1.0 --stack r4p --tau-scale "$TAU" --a-scale "$AS" --theta-scale 1.0 --aim cv \
          --coop-window --env-seed 0 --manifest "$H" --ladder nominal --defenders learned_det learned_sto --groups none \
          --traj 2 --exploiter "judge=$SRC/judge_exploiter/ckpt.pt" > "$E/eval.log" 2>&1; then
        notify "E8 eval slot $PT s$S failed - retry next pass"; continue
      fi
      touch "$E/done"
    done <<< "$ROWS"
    [ "$left" -eq 0 ] && break
    sleep 600
  done
  python scripts/fs1_e8_readout.py --root "$OUT" > "$OUT/readout.log" 2>&1
  flock /tmp/fs1_git.lock bash -c "git add '$OUT' && git commit -m 'science(fs1): harvest E8 fixed-chi attacker acceleration sweep (manifest $H)' \
      -m 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>' && git pull --rebase origin feat/scale-up-v2 && git push origin feat/scale-up-v2"
  notify "E8 eval pushed"
}
main "$@"; exit
