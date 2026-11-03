#!/usr/bin/env bash
# Stage 3: train the 5 world-model ensemble members (seeds 0-4), PARALLEL at a time, under a memory cap.
# Safe to rerun after an interruption: finished members are skipped, and unfinished ones continue after
# their last saved epoch (model, optimizer and random state are saved after every epoch).
#   scripts/train_wm.sh [PARALLEL] [THREADS]
set -u
cd "$(dirname "$0")/.."
OUT=runs/wm
PARALLEL="${1:-2}"
THREADS="${2:-8}"
EPOCHS=8
mkdir -p "$OUT"
one() {
  seed="$1"
  if grep -q "\"epoch\": $((EPOCHS - 1))," "$OUT/train_seed$seed.log" 2>/dev/null; then return; fi
  ( ulimit -v 4000000; nice -n 10 .venv/bin/python -W ignore -m dreamdesk.world_model train --out "$OUT" \
      --seed "$seed" --epochs "$EPOCHS" --threads "$THREADS" --resume ) >> "$OUT/stdout_seed$seed.txt" 2>&1
}
export -f one
export OUT EPOCHS THREADS
printf '%s\n' 0 1 2 3 4 | xargs -P "$PARALLEL" -I{} bash -c 'one {}'
echo "all members trained"
