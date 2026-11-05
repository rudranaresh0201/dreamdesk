#!/usr/bin/env bash
# Stage 4 achiever training on the laptop, as in experiments/stage4_prereg.md (Deviation 1).
# Safe to rerun after an interruption: finished runs are skipped, unfinished ones resume exactly.
#   scripts/train_ach.sh [PARALLEL] "ARM:SEED ..."
set -u
cd "$(dirname "$0")/.."
PARALLEL="${1:-2}"
RUNS="${2:-dream:0 penalty:0 dream:1 penalty:1}"
ITERATIONS=1500
run_one() {
  IFS=: read -r arm seed <<< "$1"
  local penalty=0.0; [ "$arm" = "penalty" ] && penalty=0.5
  local out="runs/ach/${arm}_seed${seed}"
  if [ -e "$out/done" ]; then return; fi
  mkdir -p "$out"
  ( ulimit -v 5000000; nice -n 10 .venv/bin/python -u -W ignore -m dreamdesk.achiever train --out "$out" --seed "$seed" \
      --penalty "$penalty" --iterations "$ITERATIONS" --threads 4 --resume >> "$out/stdout.txt" 2>&1 ) && touch "$out/done"
}
export -f run_one
export ITERATIONS
printf '%s\n' $RUNS | xargs -P "$PARALLEL" -L 1 bash -c 'run_one "$0"'
echo "all laptop runs finished"
