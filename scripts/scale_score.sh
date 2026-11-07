#!/usr/bin/env bash
# Test 1 scoring (experiments/scale_prereg.md): fine-tune every prior seed k with seed k on each held-out app's
# first B clicks, train scratch with seeds 0-2, score all on val, then the baselines and the report.
# Runs are skipped if their .json exists, so this can be stopped and restarted.
#   scripts/scale_score.sh [PARALLEL] [THREADS]
set -eu
cd "$(dirname "$0")/.."
P=${1:-3}; T=${2:-5}
APPS="disk-usage files logs web-chat web-fitness web-quiz web-todo web-weather"
for b in 100 300; do
  mkdir -p data/budget_scale/B$b
  for a in disk-usage files logs; do cp -n data/budget/B$b/$a.pkl data/budget_scale/B$b/; done
done
.venv/bin/python -m dreamdesk.budget --apps web-chat web-fitness web-quiz web-todo web-weather \
  --budgets 100 300 --data data/wm_web --out data/budget_scale
for p in prior7 prior15 prior23; do for s in 0 1 2; do
  grep -q '"epoch": 7' runs/scale/$p/train_seed$s.log || { echo "$p seed $s is not finished"; exit 1; }
done; done
mkdir -p runs/scale_ft
jobs=""
for s in 0 1 2; do
  for p in prior7 prior15 prior23; do jobs+="finetune $p $s"$'\n'; done
  jobs+="scratch scratch $s"$'\n'
done
echo -n "$jobs" | xargs -P "$P" -L 1 bash -c '
  arm=$0; dir=$1; s=$2
  prior=runs/scale/$dir/member_seed$s.pt; [ "$arm" = scratch ] && prior=none
  .venv/bin/python -u -W ignore -m dreamdesk.finetune run --arms $arm --apps '"$APPS"' --budgets 100 300 \
    --seeds $s --prior $prior --budget-dir data/budget_scale --threads '"$T"' --out runs/scale_ft/$dir \
    >> runs/scale_ft/${dir}_seed$s.log 2>&1
  echo "$(date +%H:%M) $dir seed $s: exit $? ($(grep -c "^\[" runs/scale_ft/${dir}_seed$s.log) runs)"'
.venv/bin/python -W ignore -m dreamdesk.scale_report baselines > runs/scale_ft/baselines.log
.venv/bin/python -W ignore -m dreamdesk.scale_report report | tee runs/scale_ft/report.md
echo "$(date +%H:%M) scale scoring finished"
