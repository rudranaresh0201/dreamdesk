#!/usr/bin/env bash
# Stage 5 real tasks on held-out apps after a short exploration (experiments/tasks_prereg.md), inside the sandbox.
#   scripts/stage5_tasks.sh OUT SPLIT GOALS PARALLEL "SEEDS" ["BUDGETS"]
# e.g. scripts/stage5_tasks.sh runs/s5_pilot val 10 3 "0"
# Per app: random (knows nothing), and for each budget B: graph (map of the first B clicks) and planner
# (3-member ensemble of the fine-tuned dreams from runs/ft, bank = first B clicks). Goals are the same for
# every agent and budget (from data/wm_final, rule "pilot": any scorable goal). Finished runs are kept.
set -u
cd "$(dirname "$0")/.."
OUT="$(realpath -m "$1")"; SPLIT="$2"; GOALS="$3"; PARALLEL="$4"; SEEDS="$5"; BUDGETS="${6:-100 300 1000}"
APPS="${APPS:-disk-usage files logs}"
mkdir -p "$OUT/logs" "$OUT/interrupted"
JOBS=()
for seed in $SEEDS; do for app in $APPS; do
  case "${GOAL_RULE:-pilot}" in split|deep) ;; *) JOBS+=("$app random random - $seed");; esac
  for b in $BUDGETS; do
    # rule "split": goals depend on what the first B clicks saw, so Random gets its own run per budget
    case "${GOAL_RULE:-pilot}" in split|deep) JOBS+=("$app random random-B$b $b $seed");; esac
    JOBS+=("$app graph graph-B$b $b $seed" "$app planner planner-B$b $b $seed")
  done
done; done
run_one() {
  local app="$1" agent="$2" name="$3" b="$4" seed="$5"
  local base="${app}_${name}_${SPLIT}_seed${seed}"
  if grep -q '^finished:' "$OUT/logs/$base.log" 2>/dev/null; then return; fi
  for f in "$OUT/$base.jsonl" "$OUT/logs/$base.log"; do [ -e "$f" ] && mv "$f" "$OUT/interrupted/$(date +%s)_$(basename "$f")"; done
  local data="${GOAL_DATA:-data/wm_final}" extra=""
  if [ "$b" != "-" ]; then
    data="${BUDGET_DIR:-data/budget_final}/B$b"
    [ "$agent" = random ] || extra="--members runs/ft/finetune_${app}_B${b}_seed0.pt runs/ft/finetune_${app}_B${b}_seed1.pt runs/ft/finetune_${app}_B${b}_seed2.pt"
  fi
  nice -n 10 timeout 2h bash scripts/sandbox.sh --out "$OUT" /usr/bin/bash -c \
    "MAX_STEPS=${MAX_STEPS:-10} PLANNER_DEPTH=${PLANNER_DEPTH:-5} .venv/bin/python -u -W ignore -m dreamdesk.real_eval --app $app --agent $agent --name $name $extra --data $data --goal-data ${GOAL_DATA:-data/wm_final} --seed $seed --rule ${GOAL_RULE:-pilot} --split $SPLIT --goals $GOALS --out $OUT 2>&1" \
    2>&1 | grep -v dbind | grep -v '^$' > "$OUT/logs/$base.log"
  echo "$(date +%H:%M) $base: $(tail -1 "$OUT/logs/$base.log")"
}
export -f run_one
export OUT SPLIT GOALS GOAL_RULE MAX_STEPS PLANNER_DEPTH GOAL_DATA BUDGET_DIR
printf '%s\n' "${JOBS[@]}" | xargs -P "$PARALLEL" -L 1 bash -c 'run_one "$0" "$1" "$2" "$3" "$4"'
echo "all stage 5 task runs finished"
