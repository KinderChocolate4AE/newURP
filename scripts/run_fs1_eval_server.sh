#!/usr/bin/env bash
# FS1 봉인 평가 v1 (docs/123 §8, manifest artifacts/fs1/eval_v1_manifest.json):
# fresh exploiter 2개 (학습 방어 / kfirst50, 각 1e7 step) → 교차 평가 → v2 addendum (공칭 사다리)
# → 판독 → 커밋·push.
#   RUN=artifacts/fs1/run3 WORKERS=12 tmux new -d -s fs1e 'bash scripts/run_fs1_eval_server.sh'
set -euo pipefail
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
RUN=${RUN:-artifacts/fs1/run3}
WORKERS=${WORKERS:-12}
OUT="$RUN/eval_v1"
notify() { python -c "from shepherd.notify import ntfy; ntfy('$1', title='fs1e')" || true; }
trap 'notify "FS1 eval FAILED - check logs"' ERR
H=$(python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_eval_manifest import load; print(load()['manifest_hash'])")
mkdir -p "$OUT"

for X in learned kfirst50; do
  if [ "$X" = learned ]; then TGT="$RUN/ckpt.pt"; S=261100; else TGT=scripted:kfirst50; S=261200; fi
  python -u -m shepherd.fs1.train --out "$OUT/exploit_$X" --workers "$WORKERS" --torch-threads 2 \
      --exploit "$TGT" --seed "$S" --iters 100000 --total-steps 1e7 --steps-per-worker 4096 \
      > "$OUT/exploit_$X.log" 2>&1
done

# v1 = 봉인 그대로 (사다리 legacy 구성 — deviation 은 v2 addendum 에 기록, docs/123 §8.1)
python -u -m shepherd.fs1.eval run --ckpt "$RUN/ckpt.pt" --out "$OUT/eval" --workers "$WORKERS" \
    --episodes 240 --seed 261000 --pool-k 8 --traj 4 --manifest "$H" --ladder legacy \
    --exploiter "learned=$OUT/exploit_learned/ckpt.pt" "kfirst50=$OUT/exploit_kfirst50/ckpt.pt" \
    > "$OUT/eval.log" 2>&1
# v2 addendum = 공칭 사다리 셀만
H2=$(python -c "import sys; sys.path.insert(0, 'scripts'); from fs1_eval_manifest import load_v2; print(load_v2()['manifest_hash'])")
python -u -m shepherd.fs1.eval run --ckpt "$RUN/ckpt.pt" --out "$OUT/eval_v2" --workers "$WORKERS" \
    --episodes 240 --seed 261000 --groups ladder --traj 4 --manifest "$H2" --ladder nominal \
    > "$OUT/eval_v2.log" 2>&1
python scripts/fs1_eval_manifest.py --readout "$OUT" > "$OUT/readout.log" 2>&1

git add "$OUT"/exploit_*/log.jsonl "$OUT"/exploit_*/config.json "$OUT/eval" "$OUT/eval_v2" "$OUT/readout.json"
git commit -m "science(fs1): harvest FS1 eval v1 + v2 addendum ($RUN, manifests $H / $H2)"
git pull --rebase origin feat/scale-up-v2
git push origin feat/scale-up-v2
notify "FS1 eval v1 pushed"
