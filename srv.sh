#!/bin/bash
# Server helper (Git Bash). Usage:
#   ./srv.sh push                      # send whole code tree (not .venv/runs) to server
#   ./srv.sh run NAME CORES exp-args   # tmux night_NAME on GPU1, pinned cores, -> runs/NAME.out (+ EXIT line)
#   ./srv.sh wait NAME...              # block until each runs/NAME.out has an EXIT line
#   ./srv.sh pull                      # fetch runs/ back
#   ./srv.sh sh 'cmd'                  # run in server code dir
set -e
sed '1s/^\xEF\xBB\xBF//' ~/.ssh/config > /tmp/sshcfg
SSH="ssh -F /tmp/sshcfg -o ConnectTimeout=30 -o LogLevel=ERROR server4"
D=/data/hjhong/night/code
PY=/data/hjhong/fs1jax/.venv-jax/bin/python
MEM=${MEM:-0.3}
cd "$(dirname "$0")"
case "$1" in
  push) tar czf - --exclude=.venv --exclude=runs --exclude=.git --exclude=__pycache__ . | $SSH "mkdir -p $D/runs && cd $D && tar xzf -" ;;
  run) name=$2; cores=$3; shift 3
       $SSH "cd $D && tmux new-session -d -s night_$name \"CUDA_VISIBLE_DEVICES=1 XLA_PYTHON_CLIENT_MEM_FRACTION=$MEM PYTHONUNBUFFERED=1 taskset -c $cores $PY exp.py $* > runs/$name.out 2>&1; echo EXIT \\\$? >> runs/$name.out\"" ;;
  wait) shift; for n in "$@"; do until $SSH "grep -q '^EXIT' $D/runs/$n.out" 2>/dev/null; do sleep 30; done; done
        for n in "$@"; do $SSH "tail -2 $D/runs/$n.out"; done ;;
  pull) $SSH "cd $D && tar czf - runs" | tar xzf - ;;
  runpy) name=$2; cores=$3; shift 3
       $SSH "cd $D && tmux new-session -d -s night_$name \"CUDA_VISIBLE_DEVICES=1 XLA_PYTHON_CLIENT_MEM_FRACTION=$MEM PYTHONUNBUFFERED=1 taskset -c $cores $PY $* > runs/$name.out 2>&1; echo EXIT \\\$? >> runs/$name.out\"" ;;
  sh) shift; $SSH "cd $D && $*" ;;
esac
