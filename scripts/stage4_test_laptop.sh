#!/usr/bin/env bash
# After the laptop training: the Stage 4 test (experiments/stage4_prereg.md) for everything trained here.
# Kaggle's seed-2 policies are tested later with the same scripts. Each real run happens once.
set -u
cd "$(dirname "$0")/.."
until grep -q "all laptop runs finished" runs/train_ach.log; do sleep 120; done
for r in dream_seed0 penalty_seed0 dream_seed1 penalty_seed1; do
  [ -e runs/ach/$r/done ] || { echo "runs/ach/$r not done: stopping before the test"; exit 1; }
done
bash scripts/real_eval.sh runs/real_test test 30 2 \
  "random:random:-:0 random:random:-:1 random:random:-:2 graph:graph:-:0 \
   achiever:dream:runs/ach/dream_seed0/achiever.pt:0 achiever:penalty:runs/ach/penalty_seed0/achiever.pt:0 \
   achiever:dream:runs/ach/dream_seed1/achiever.pt:1 achiever:penalty:runs/ach/penalty_seed1/achiever.pt:1"
for r in dream_seed0 penalty_seed0 dream_seed1 penalty_seed1; do
  ( ulimit -v 5000000; .venv/bin/python -W ignore -m dreamdesk.achiever dream_eval --ckpt runs/ach/$r/achiever.pt \
      --split test --goals 30 --out runs/real_test/${r}_dream_test.json --threads 6 )
done
echo "laptop part of the Stage 4 test finished"
