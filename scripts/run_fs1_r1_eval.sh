#!/usr/bin/env bash
# R1 착취자 예산 민감도 평가 (server4 CPU, manifest fs1_r1_manifest, docs/138): slot 마다 원래 1e7 착취자 (env-seed 0 재평가) + 새 b1/b3 착취자.
# 착취자 생산 경로: $IN/<variant>/s<seed>/{b1,b3,b3_at1e7,b3_at2e7}/ (ckpt.pt, done). 원래 착취자·방어: $E7B/<variant>/s<seed>/.
#   tmux new -d -s r1_eval 'cd <repo> && source .venv-l2/bin/activate && IN=/data/hjhong/fs1jax/r1 E7B=/data/hjhong/fs1jax/e7b bash scripts/run_fs1_r1_eval.sh'
main() {
  set -euo pipefail
  cd "$(dirname "$0")/.."
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
  IN=${IN:?IN required}; E7B=${E7B:?E7B required}
  WORKERS=${WORKERS:-6}
  OUT=artifacts/fs1/r1
  notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='r1')" || true; }
  flock /tmp/fs1_git.lock git pull -q --rebase origin feat/scale-up-v2 || true
  H=$(python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_r1_manifest import load; print(load()['manifest_hash'])")
  ROWS=$(python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_r1_manifest import build
for s in build()['slots']: print(s['variant'], s['seed'], s['tau_scale'], s['theta_scale'], s['aim'], s['eval_seed'])")
  while true; do
    left=0
    while read -r VAR S TAU THETA AIM SEED; do
      for EX in orig b1 b3 b3_at1e7 b3_at2e7; do
        E="$OUT/$VAR/s$S/eval_$EX"; [ -f "$E/done" ] && continue
        left=$((left + 1))
        if [ "$EX" = orig ]; then CK="$E7B/$VAR/s$S/judge_exploiter"; else CK="$IN/$VAR/s$S/$EX"; fi
        [ -f "$CK/done" ] || continue
        mkdir -p "$E"
        if ! python -u -m shepherd.fs1.eval run --ckpt "$E7B/$VAR/s$S/ckpt.pt" --out "$E" --workers "$WORKERS" \
            --episodes 240 --seed "$SEED" --mu 0.35 --nu 1.0 --stack r4p --tau-scale "$TAU" --theta-scale "$THETA" \
            --aim "$AIM" --env-seed 0 --manifest "$H" --ladder nominal --defenders learned_det learned_sto \
            --groups none --traj 2 --exploiter "judge=$CK/ckpt.pt" > "$E/eval.log" 2>&1; then
          notify "R1 eval $VAR s$S $EX failed - retry next pass"; continue
        fi
        touch "$E/done"
      done
    done <<< "$ROWS"
    [ "$left" -eq 0 ] && break
    sleep 300
  done
  python scripts/fs1_r1_readout.py --root "$OUT" > "$OUT/readout.log" 2>&1
  flock /tmp/fs1_git.lock bash -c "git add '$OUT' && git commit -m 'science(fs1): harvest R1 exploiter budget sensitivity (manifest $H)' \
      -m 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>' && git pull --rebase origin feat/scale-up-v2 && git push origin feat/scale-up-v2"
  notify "R1 eval pushed"
}
main "$@"; exit
