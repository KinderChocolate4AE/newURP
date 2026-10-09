#!/usr/bin/env bash
# E7-c 정본 평가 (server4 CPU, manifest `fs1_e7_manifest.build_e7c` v1.3, docs/130):
# (cond, seed) 마다 동결 방어 {det, sto} vs 전용 착취자 {det, sto} 240판 paired
# (+ 창 tick 협력 counterfactual, kill_phase) → 판독 (det·sto 두 계열) → push.
#   tmux new -d -s evalc7 'cd <repo> && source .venv-l2/bin/activate && IN=/data/hjhong/fs1jax/e7c bash scripts/run_fs1_e7c_eval.sh'
main() {
  set -euo pipefail
  cd "$(dirname "$0")/.."
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
  IN=${IN:?IN required}
  WORKERS=${WORKERS:-6}
  OUT=artifacts/fs1/e7c
  notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='e7c')" || true; }
  trap 'notify "E7-c eval FAILED - check logs"' ERR
  H=$(python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_e7_manifest import load_e7c; print(load_e7c()['manifest_hash'])")
  mkdir -p "$OUT"

  python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_e7_manifest import C_CONDS, C_SEED0, C_STRIDE
for i, c in enumerate(C_CONDS):
    lim = '--limiter-roe post_shot' if c['limiters'] == 'post_shot' else '--limiter-inert'
    for s in (0, 1, 2): print(c['name'], c['tau_scale'], c['theta_scale'], s, C_SEED0 + i*C_STRIDE, lim)" |
  while read -r COND TAU THETA S SEED LIM1 LIM2; do
    D="$OUT/$COND/s$S"
    [ -f "$D/done" ] && continue
    mkdir -p "$D/judge_exploiter" "$D/judge_exploiter_sto"
    cp "$IN/$COND/s$S/log.jsonl" "$D/"
    cp "$IN/$COND/s$S/judge_exploiter/log.jsonl" "$D/judge_exploiter/"
    cp "$IN/$COND/s$S/judge_exploiter_sto/log.jsonl" "$D/judge_exploiter_sto/"
    python -u -m shepherd.fs1.eval run --ckpt "$IN/$COND/s$S/ckpt.pt" --out "$D/eval" \
        --workers "$WORKERS" --episodes 240 --seed "$SEED" --mu 0.35 --nu 1.0 --stack r4p \
        --tau-scale "$TAU" --theta-scale "$THETA" --aim cv $LIM1 $LIM2 --coop-window \
        --manifest "$H" --ladder nominal --defenders learned_det learned_sto --groups none --traj 2 \
        --exploiter "judge=$IN/$COND/s$S/judge_exploiter/ckpt.pt" \
                    "judge_sto=$IN/$COND/s$S/judge_exploiter_sto/ckpt.pt" > "$D/eval.log" 2>&1
    touch "$D/done"
  done

  python scripts/fs1_e7c_readout.py --root "$OUT" > "$OUT/readout.log" 2>&1
  flock /tmp/fs1_git.lock bash -c "git add '$OUT' \
      && git commit -m 'science(fs1): harvest E7-c canonical eval (manifest $H)' \
                    -m 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>' \
      && git pull --rebase origin feat/scale-up-v2 && git push origin feat/scale-up-v2"
  notify "E7-c eval pushed"
}
main "$@"; exit
