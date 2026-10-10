#!/usr/bin/env bash
# E2 = AMI 공격자 기전 개입 (server4 CPU, manifest `fs1_ami_manifest`, docs/132): (line, variant, seed)
# 마다 base (residual 기록) → 7 개입 arm, 동결 방어 vs 전용 exploiter 240판 paired → 판독 → push.
#   tmux new -d -s ami_e2 'cd <repo> && source .venv-l2/bin/activate && IN=/data/hjhong/fs1jax/e7b bash scripts/run_fs1_ami_eval.sh'
main() {
  set -euo pipefail
  cd "$(dirname "$0")/.."
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
  IN=${IN:?IN required}
  WORKERS=${WORKERS:-6}
  RES=${RES:-/data/hjhong/l2/ami_res}          # shuffle 공여 residual (repo 밖, 커밋 안 함)
  OUT=artifacts/fs1/ami
  notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='ami')" || true; }
  trap 'notify "AMI eval FAILED - check logs"' ERR
  H=$(python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_ami_manifest import load; print(load()['manifest_hash'])")
  mkdir -p "$OUT"

  python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_ami_manifest import LINES, ARMS, B_VARIANTS, B_SEEDS, B_SEED0, B_STRIDE, ENV_SEED, N
for ln, L in LINES.items():
    for i, v in enumerate(B_VARIANTS):
        for s in B_SEEDS:
            for arm in ARMS: print(ln, L['defender'], L['exploiter'], v['name'], v['tau_scale'], v['theta_scale'], v['aim'], s, B_SEED0 + i*B_STRIDE, arm, ENV_SEED, N)" |
  while read -r LN DEF EX VAR TAU THETA AIM S SEED ARM ES NEP; do
    D="$OUT/$LN/$VAR/s$S/$ARM"
    [ -f "$D/done" ] && continue
    mkdir -p "$D"
    DON="$RES/$LN/$VAR/s$S.json"
    EXTRA=()
    case "$ARM" in
      base) EXTRA=(--record-res "$DON") ;;
      shuf_*) EXTRA=(--att-iv "$ARM" --att-donor "$DON") ;;
      *) EXTRA=(--att-iv "$ARM") ;;
    esac
    python -u -m shepherd.fs1.eval run --ckpt "$IN/$VAR/s$S/ckpt.pt" --out "$D" \
        --workers "$WORKERS" --episodes "$NEP" --seed "$SEED" --mu 0.35 --nu 1.0 --stack r4p \
        --tau-scale "$TAU" --theta-scale "$THETA" --aim "$AIM" --coop-window --env-seed "$ES" \
        --manifest "$H" --ladder nominal --defenders "$DEF" --groups none --traj 2 \
        --exploiter "judge=$IN/$VAR/s$S/$EX/ckpt.pt" "${EXTRA[@]}" > "$D/eval.log" 2>&1
    touch "$D/done"
  done

  python scripts/fs1_ami_readout.py --root "$OUT" > "$OUT/readout.log" 2>&1
  flock /tmp/fs1_git.lock bash -c "git add '$OUT' \
      && git commit -m 'science(fs1): harvest E2 AMI attacker-intervention eval (manifest $H)' \
                    -m 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>' \
      && git pull --rebase origin feat/scale-up-v2 && git push origin feat/scale-up-v2"
  notify "AMI eval pushed"
}
main "$@"; exit
