#!/usr/bin/env bash
# Stage 3: train the 5 world-model ensemble members (seeds 0-4), PARALLEL at a time, under a memory cap.
# Safe to rerun after an interruption: members whose log shows the last epoch are skipped, others restart.
#   scripts/train_wm.sh [PARALLEL] [THREADS]
set -u
cd "$(dirname "$0")/.."
OUT=runs/wm
PARALLEL="${1:-2}"
THREADS="${2:-8}"
EPOCHS=8
mkdir -p "$OUT/interrupted"
STAMP="$(date +%Y%m%d-%H%M%S)"
one() {
  seed="$1"
  if grep -q "\"epoch\": $((EPOCHS - 1))," "$OUT/train_seed$seed.log" 2>/dev/null; then return; fi
  for f in "$OUT/train_seed$seed.log" "$OUT/member_seed$seed.pt"; do
    [ -e "$f" ] && mv "$f" "$OUT/interrupted/${STAMP}_$(basename "$f")"
  done
  ( ulimit -v 4000000; nice -n 10 .venv/bin/python -W ignore -m dreamdesk.world_model train --out "$OUT" \
      --seed "$seed" --epochs "$EPOCHS" --threads "$THREADS" ) > "$OUT/stdout_seed$seed.txt" 2>&1
}
export -f one
export OUT EPOCHS STAMP THREADS
printf '%s\n' 0 1 2 3 4 | xargs -P "$PARALLEL" -I{} bash -c 'one {}'
echo "all members trained"
