#!/usr/bin/env bash
# E7-b′ 정본 평가 (server4 CPU, manifest `fs1_e7_manifest.build_e7b2`, docs/129 §8): sto 감사
# (variant, seed) 마다 동결 방어 vs 전용 judge exploiter 240판 paired (+ scripted 전이 참조,
# 창 tick 협력 counterfactual) → 판독 → push.
#   tmux new -d -s e7b2 'cd <repo> && source .venv-l2/bin/activate && IN=/data/hjhong/fs1jax/e7b bash scripts/run_fs1_e7b2_eval.sh'
main() {
  set -euo pipefail
  cd "$(dirname "$0")/.."
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
  IN=${IN:?IN required}
  WORKERS=${WORKERS:-6}
  OUT=artifacts/fs1/e7b2
  notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='e7b2')" || true; }
  trap 'notify "E7-b2 eval FAILED - check logs"' ERR
  H=$(python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_e7_manifest import load_e7b2; print(load_e7b2()['manifest_hash'])")
  mkdir -p "$OUT"

  python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_e7_manifest import B_VARIANTS, B_SEEDS, B_SEED0, B_STRIDE
for i, v in enumerate(B_VARIANTS):
    for s in B_SEEDS: print(v['name'], v['tau_scale'], v['theta_scale'], v['aim'], s, B_SEED0 + i*B_STRIDE)" |
  while read -r VAR TAU THETA AIM S SEED; do
    D="$OUT/$VAR/s$S"
    [ -f "$D/done" ] && continue
    mkdir -p "$D/judge_exploiter_sto"
    cp "$IN/$VAR/s$S/log.jsonl" "$D/"
    cp "$IN/$VAR/s$S/judge_exploiter_sto/log.jsonl" "$D/judge_exploiter_sto/"
    python -u -m shepherd.fs1.eval run --ckpt "$IN/$VAR/s$S/ckpt.pt" --out "$D/eval" \
        --workers "$WORKERS" --episodes 240 --seed "$SEED" --mu 0.35 --nu 1.0 --stack r4p \
        --tau-scale "$TAU" --theta-scale "$THETA" --aim "$AIM" --coop-window \
        --manifest "$H" --ladder nominal --defenders learned_sto learned_det \
        --groups none --traj 2 \
        --exploiter "judge_sto=$IN/$VAR/s$S/judge_exploiter_sto/ckpt.pt" > "$D/eval.log" 2>&1
    touch "$D/done"
  done

  python scripts/fs1_e7b2_readout.py --root "$OUT" > "$OUT/readout.log" 2>&1
  flock /tmp/fs1_git.lock bash -c "git add '$OUT' \
      && git commit -m 'science(fs1): harvest E7-b2 sto-audit canonical eval (manifest $H)' \
                    -m 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>' \
      && git pull --rebase origin feat/scale-up-v2 && git push origin feat/scale-up-v2"
  notify "E7-b2 eval pushed"
}
main "$@"; exit
