#!/usr/bin/env bash
# Demo video only (no claims): records the sandbox's private screen while an agent does Files goals on val.
#   scripts/record_demo.sh AGENT OUT KIND GOALS      e.g. scripts/record_demo.sh planner runs/demo/planner combo 12
# Writes OUT/real.mp4, OUT/events.jsonl (timestamped steps, and what the dream imagined), OUT/start.txt.
set -eu
cd "$(dirname "$0")/.."
AGENT="$1"; OUT="$(realpath -m "$2")"; KIND="$3"; GOALS="$4"; B=100
mkdir -p "$OUT"; rm -f "$OUT"/*.jsonl "$OUT"/real.mp4
EXTRA=""; [ "$AGENT" = planner ] && EXTRA="--members runs/ft/finetune_files_B${B}_seed0.pt runs/ft/finetune_files_B${B}_seed1.pt runs/ft/finetune_files_B${B}_seed2.pt"
timeout 1h bash scripts/sandbox.sh --out "$OUT" /usr/bin/bash -c "
  date +%s.%N > $OUT/start.txt
  ffmpeg -loglevel error -f x11grab -framerate 30 -video_size 1280x800 -i :90 -c:v libx264 -preset veryfast -crf 16 -pix_fmt yuv420p $OUT/real.mp4 &
  F=\$!
  DEMO_LOG=$OUT/events.jsonl PLANNER_DEPTH=10 .venv/bin/python -u -W ignore -m dreamdesk.real_eval --app files --agent $AGENT \
    --name demo $EXTRA --data data/budget_s6/B$B --goal-data data/wm_s6 --rule split --split val --kind $KIND --goals $GOALS --seed 0 --out $OUT
  kill -INT \$F; wait \$F" 2>&1 | grep -v dbind | grep -v '^$'
