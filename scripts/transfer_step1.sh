#!/usr/bin/env bash
# Stage 5 step 1 (experiments/transfer_prereg.md): smoke test, then train one 7-app member, then score it.
set -u
cd "$(dirname "$0")/.."
until grep -q "pilot planner+hybrid finished" runs/real_pilot_planner.log; do sleep 60; done
echo "$(date +%H:%M) smoke"
rm -rf runs/wm7_smoke
( ulimit -v 4000000; .venv/bin/python -W ignore -m dreamdesk.world_model train --data data/wm7 --out runs/wm7_smoke --seed 0 --epochs 1 --limit 20 --threads 6 ) || { echo "smoke train FAILED"; exit 1; }
( ulimit -v 5000000; timeout 3600 .venv/bin/python -W ignore -m dreamdesk.transfer_eval --member runs/wm7_smoke/member_seed0.pt --out runs/wm7_smoke/transfer_val.json ) || { echo "smoke eval FAILED"; exit 1; }
echo "$(date +%H:%M) smoke ok; training"
( ulimit -v 4000000; nice -n 10 .venv/bin/python -W ignore -m dreamdesk.world_model train --data data/wm7 --out runs/wm7 --seed 0 --epochs 8 --threads 6 --resume ) || { echo "train FAILED"; exit 1; }
echo "$(date +%H:%M) trained; scoring"
( ulimit -v 5000000; .venv/bin/python -W ignore -m dreamdesk.transfer_eval --member runs/wm7/member_seed0.pt --out runs/wm7/transfer_val.json ) | tee runs/wm7/transfer_val.txt
echo "$(date +%H:%M) step 1 finished"
