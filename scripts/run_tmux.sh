#!/usr/bin/env bash
# 랩 서버 장기런 러너 — tmux + 로그 + ntfy 알림.
#
#   ./scripts/run_tmux.sh <session> <module> [args...]
#
# 예:
#   ./scripts/run_tmux.sh lead shepherd.scripts.lead_time_diag \
#       --n 300 --start-x 24 36 48 60 --out results/lead_time_diag.json
#
# 로그: results/<session>.log (tee 라 tmux attach 없이도 tail 가능)
# 알림: NTFY_TOPIC 이 설정돼 있으면 종료 시 푸시 (shepherd/notify.py 와 같은 토픽)
set -euo pipefail

SESSION="${1:?usage: run_tmux.sh <session> <module> [args...]}"; shift
MODULE="${1:?module required}"; shift

cd "$(dirname "$0")/.."
mkdir -p results
LOG="results/${SESSION}.log"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "세션 '$SESSION' 이미 존재. attach: tmux attach -t $SESSION" >&2
  exit 1
fi

# PYTHONUNBUFFERED: 진행 로그가 즉시 파일에 떨어지도록 (버퍼링으로 진행상황을
# 못 보던 사고 재발 방지)
CMD="PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 python -m ${MODULE} $* 2>&1 | tee ${LOG}"
CMD="${CMD}; code=\${PIPESTATUS[0]}"
CMD="${CMD}; python -c \"from shepherd.notify import ntfy; import sys; ntfy(f'${SESSION} exit=\$code', title='newURP')\" || true"
CMD="${CMD}; echo; echo '[done] exit='\$code' · log: ${LOG}'; exec bash"

tmux new-session -d -s "$SESSION" "$CMD"
echo "started: tmux session '$SESSION'"
echo "  attach : tmux attach -t $SESSION"
echo "  tail   : tail -f $LOG"
echo "  commit : $(git rev-parse --short HEAD)"
