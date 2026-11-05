#!/usr/bin/env bash
# Fallback for Stage 4 seed 2 (prereg Deviation 2): if Kaggle's seed-2 runs aren't here when the laptop part of the
# test ends, train them on the laptop, then test them the same way. Kaggle results unpacked into runs/ach/*_seed2
# first (with a done file) are used instead. Stop this script (by PID) before unpacking a Kaggle zip mid-run.
set -u
cd "$(dirname "$0")/.."
until grep -q "laptop part of the Stage 4 test finished" runs/stage4_test_laptop.log; do sleep 120; done
bash scripts/train_ach.sh 2 "dream:2 penalty:2"
for r in dream_seed2 penalty_seed2; do
  [ -e runs/ach/$r/done ] || { echo "runs/ach/$r not done: stopping before the test"; exit 1; }
done
bash scripts/real_eval.sh runs/real_test test 30 2 \
  "achiever:dream:runs/ach/dream_seed2/achiever.pt:2 achiever:penalty:runs/ach/penalty_seed2/achiever.pt:2"
for r in dream_seed2 penalty_seed2; do
  ( ulimit -v 5000000; .venv/bin/python -W ignore -m dreamdesk.achiever dream_eval --ckpt runs/ach/$r/achiever.pt \
      --split test --goals 30 --out runs/real_test/${r}_dream_test.json --threads 6 )
done
echo "seed 2 part of the Stage 4 test finished"
