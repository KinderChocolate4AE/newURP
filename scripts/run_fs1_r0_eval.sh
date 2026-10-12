#!/usr/bin/env bash
# R0 평가 반복성 (server4 CPU, manifest fs1_r0_manifest, docs/135): 2 slot × 착취자 2 × env seed 8 = 32 평가 → 판독 → push.
#   tmux new -d -s r0 'cd <repo> && source .venv-l2/bin/activate && IN=/data/hjhong/fs1jax/e7b bash scripts/run_fs1_r0_eval.sh'
main() {
  set -euo pipefail
  cd "$(dirname "$0")/.."
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
  IN=${IN:?IN required}
  WORKERS=${WORKERS:-6}
  OUT=artifacts/fs1/r0
  notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='r0')" || true; }
  trap 'notify "R0 eval FAILED - check logs"' ERR
  H=$(python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_r0_manifest import load; print(load()['manifest_hash'])")
  python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_r0_manifest import SLOTS, EXPLOITERS, ENV_SEEDS
for s in SLOTS:
    for ex, d in EXPLOITERS.items():
        for k in ENV_SEEDS: print(s['variant'], s['seed'], s['tau_scale'], s['theta_scale'], s['aim'], s['eval_seed'], ex, d, k)" |
  while read -r VAR S TAU THETA AIM SEED EX EXD K; do
    E="$OUT/$VAR/s$S/env$K/eval_$EX"
    [ -f "$E/done" ] && continue
    mkdir -p "$E"
    G=$([ "$EX" = det ] && echo judge || echo judge_sto)
    python -u -m shepherd.fs1.eval run --ckpt "$IN/$VAR/s$S/ckpt.pt" --out "$E" \
        --workers "$WORKERS" --episodes 240 --seed "$SEED" --mu 0.35 --nu 1.0 --stack r4p \
        --tau-scale "$TAU" --theta-scale "$THETA" --aim "$AIM" --coop-window --env-seed "$K" \
        --manifest "$H" --ladder nominal --defenders learned_det learned_sto --groups none --traj 2 \
        --exploiter "$G=$IN/$VAR/s$S/$EXD/ckpt.pt" > "$E/eval.log" 2>&1
    touch "$E/done"
  done
  python scripts/fs1_r0_readout.py --root "$OUT" > "$OUT/readout.log" 2>&1
  flock /tmp/fs1_git.lock bash -c "git add '$OUT' \
      && git commit -m 'science(fs1): harvest R0 evaluation repeatability (manifest $H)' \
                    -m 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>' \
      && git pull --rebase origin feat/scale-up-v2 && git push origin feat/scale-up-v2"
  notify "R0 pushed"
}
main "$@"; exit
