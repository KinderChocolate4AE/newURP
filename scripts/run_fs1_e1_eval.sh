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
  if [ -n "${WAIT_FILE:-}" ]; then for _ in $(seq 120); do [ -f "$WAIT_FILE" ] && break; sleep 120; done; fi   # 앞 작업 종료 대기 (최대 4h)
  flock /tmp/fs1_git.lock git pull -q --rebase origin feat/scale-up-v2 || true
  H=$(python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_e1_manifest import load; print(load()['manifest_hash'])")
  ROWS=$(python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_e1_manifest import LADDER, PAIR, E6_ARMS, SEEDS, SEED0, STRIDE, N
for i, p in enumerate(LADDER + PAIR + E6_ARMS):
    for s in SEEDS: print(p['name'], p['tau_scale'], p.get('a_scale', 1.0), p.get('mu', 0.35), s, SEED0 + i*STRIDE, N)")
  while true; do
    left=0
    while read -r PT TAU AS MU S SEED NEP; do
      D="$OUT/$PT/s$S"; SRC="$IN/$PT/s$S"
      for EX in judge_exploiter judge_exploiter_sto; do      # det 착취자 (판정) 가 먼저 나오면 먼저 평가
        G=$([ "$EX" = judge_exploiter ] && echo judge || echo judge_sto)
        E="$D/eval_$G"
        [ -f "$E/done" ] && continue
        left=$((left + 1))
        [ -f "$SRC/$EX/done" ] || continue
        mkdir -p "$D/$EX" "$E"
        cp "$SRC/log.jsonl" "$D/"; cp "$SRC/$EX/log.jsonl" "$D/$EX/"
        if ! python -u -m shepherd.fs1.eval run --ckpt "$SRC/ckpt.pt" --out "$E" \
            --workers "$WORKERS" --episodes "$NEP" --seed "$SEED" --mu "$MU" --nu 1.0 --stack r4p \
            --tau-scale "$TAU" --a-scale "$AS" --theta-scale 1.0 --aim cv --coop-window --env-seed 0 \
            --manifest "$H" --ladder nominal --defenders learned_det learned_sto --groups none --traj 2 \
            --exploiter "$G=$SRC/$EX/ckpt.pt" > "$E/eval.log" 2>&1; then
          notify "E1 eval slot $PT s$S $G failed - skipped, loop continues"   # 한 slot 실패가 전체를 멈추지 않게
          continue                                                             # (다음 순회에서 재시도)
        fi
        touch "$E/done"
      done
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
