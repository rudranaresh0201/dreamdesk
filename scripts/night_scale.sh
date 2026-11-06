#!/usr/bin/env bash
# Overnight for tests 1-3 (experiments/scale_prereg.md): after the web recordings, check that LibreOffice Math
# runs in the sandbox, record it like every other app (seeds 0-4, random + novelty, 500 steps), then build datasets.
set -u
cd "$(dirname "$0")/.."
until grep -q "all runs finished" data/explore_web.log; do sleep 60; done
echo "$(date +%H:%M) web recordings done; building data/wm_web"
.venv/bin/python -m dreamdesk.wm_data data/explore_web data/wm_web
echo "$(date +%H:%M) math smoke"
rm -rf runs/math_smoke; mkdir -p runs/math_smoke
timeout 20m bash scripts/sandbox.sh --out "$PWD/runs/math_smoke" /usr/bin/bash -c \
  "/usr/bin/python3 -u -m dreamdesk.explore --app math --explorer random --steps 60 --seed 99 --out $PWD/runs/math_smoke 2>&1" \
  2>&1 | grep -v dbind | tail -3
if ! ls runs/math_smoke/*.jsonl.gz >/dev/null 2>&1; then echo "math smoke FAILED; math is left out"; exit 0; fi
echo "$(date +%H:%M) recording math"
OUT="$PWD/data/explore_math"; mkdir -p "$OUT/logs"
for seed in 0 1 2 3 4; do for ex in random novelty; do
  name="math_${ex}_seed${seed}"
  grep -q '^finished:' "$OUT/logs/$name.log" 2>/dev/null && continue
  rm -f "$OUT/$name.jsonl.gz"
  nice -n 10 timeout 90m bash scripts/sandbox.sh --out "$OUT" /usr/bin/bash -c \
    "/usr/bin/python3 -u -m dreamdesk.explore --app math --explorer $ex --steps 500 --seed $seed --out $OUT 2>&1" \
    2>&1 | grep -v dbind > "$OUT/logs/$name.log"
  echo "$(date +%H:%M) $name: $(tail -1 "$OUT/logs/$name.log")"
done; done
.venv/bin/python -m dreamdesk.wm_data data/explore_math data/wm_math
echo "$(date +%H:%M) night_scale finished"
