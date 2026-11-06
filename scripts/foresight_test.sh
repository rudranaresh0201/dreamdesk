#!/usr/bin/env bash
# Foresight test on sealed seed 5 (experiments/foresight_prereg.md): real runs, then dream runs, then the report.
set -u
cd "$(dirname "$0")/.."
OUT=runs/s5_foresight
DATA=data/wm_s5 bash scripts/real_eval.sh $OUT final 30 3 \
  "random:random:-:0 random:random:-:1 random:random:-:2 graph:graph:-:0 \
   achiever:dream:runs/ach/dream_seed0/achiever.pt:0 achiever:penalty:runs/ach/penalty_seed0/achiever.pt:0 \
   achiever:dream:runs/ach/dream_seed1/achiever.pt:1 achiever:penalty:runs/ach/penalty_seed1/achiever.pt:1 \
   achiever:dream:runs/ach/dream_seed2/achiever.pt:2 achiever:penalty:runs/ach/penalty_seed2/achiever.pt:2"
for r in dream_seed0 penalty_seed0 dream_seed1 penalty_seed1 dream_seed2 penalty_seed2; do
  [ -e $OUT/${r}_dream_final.json ] && continue
  ( ulimit -v 5000000; .venv/bin/python -W ignore -m dreamdesk.achiever dream_eval --ckpt runs/ach/$r/achiever.pt \
      --data data/wm_s5 --split final --goals 30 --out $OUT/${r}_dream_final.json --threads 6 )
done
.venv/bin/python -m dreamdesk.foresight_report $OUT --split final --json $OUT/foresight.json > $OUT/foresight.md
echo "foresight test finished"
