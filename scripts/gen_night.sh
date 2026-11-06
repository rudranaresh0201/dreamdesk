#!/usr/bin/env bash
# Generalisation test, overnight (experiments/generalise_prereg.md): after the foresight test, record sealed seed 6
# for Files, build its data, then run the pre-registered test and the report. Each step resumes if rerun.
set -u
cd "$(dirname "$0")/.."
DEPTH="$1"
until grep -q "foresight test finished" runs/s5_foresight.log 2>/dev/null; do sleep 60; done
echo "$(date +%H:%M) recording seed 6"
bash scripts/record_seed6.sh 2
grep -q '^finished:' data/explore_seed6/logs/files_random_seed6.log && grep -q '^finished:' data/explore_seed6/logs/files_novelty_seed6.log \
  || { echo "seed 6 recording incomplete"; exit 1; }
[ -e data/wm_s6/files.pkl ] || .venv/bin/python -m dreamdesk.add_split --src data/explore_seed6 --seed 6 --split final6 \
  --apps files --data data/wm_final --out data/wm_s6 || exit 1
.venv/bin/python -m dreamdesk.budget --apps files --budgets 100 300 --data data/wm_s6 --out data/budget_s6 || exit 1
.venv/bin/python - <<'P' || exit 1
import pickle
for b in (100, 300):
    x = pickle.load(open(f"data/budget/B{b}/files.pkl", "rb")); y = pickle.load(open(f"data/budget_s6/B{b}/files.pkl", "rb"))
    assert x["transitions"]["train"] == y["transitions"]["train"] and y["tokens"][:len(x["tokens"])] == x["tokens"]
print("budget train splits identical to the ones the models trained on")
P
echo "$(date +%H:%M) running the test"
GOAL_DATA=data/wm_s6 BUDGET_DIR=data/budget_s6 APPS=files GOAL_RULE=split PLANNER_DEPTH=$DEPTH \
  bash scripts/stage5_tasks.sh runs/gen_final final6 60 3 "0 1 2" "100 300"
.venv/bin/python -m dreamdesk.gen_report runs/gen_final --split final6 --json runs/gen_final/report.json > runs/gen_final/report.md
echo "$(date +%H:%M) generalisation test finished"
