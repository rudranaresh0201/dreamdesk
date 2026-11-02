#!/usr/bin/env bash
# Collects calculator data with several private desktops side by side.
#   scripts/collect.sh WORKERS EPISODES_PER_WORKER OUT_DIR [SEED_OFFSET]
set -u
WORKERS="$1"; EPISODES="$2"; OUT="$3"; OFFSET="${4:-0}"
cd "$(dirname "$0")/.."
mkdir -p "$OUT"
PIDS=()
for ((w = 0; w < WORKERS; w++)); do
  nice -n 10 bash scripts/private.sh $((90 + w)) python3 -u -m dreamdesk.collect \
    --worker "$w" --episodes "$EPISODES" --out "$OUT" --seed-offset "$OFFSET" \
    > "$OUT/worker$w.log" 2>&1 < /dev/null &
  PIDS+=($!)
done
for p in "${PIDS[@]}"; do wait "$p"; done
echo "all workers finished"
