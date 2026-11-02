#!/usr/bin/env bash
# Arm A, as pre-registered in experiments/arm_a_prereg.md: check data, train 5 seeds, test in the real app.
#   scripts/arm_a.sh
# Refuses to replace earlier results: move runs/arm_a away to run it again.
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python
OUT=runs/arm_a
SEEDS="0 1 2 3 4"

[ -e "$OUT" ] && { echo "$OUT already exists"; exit 1; }
python3 -m dreamdesk.check_data data/calculator | tee /dev/stderr | grep -q "VERDICT: PASS" || { echo "data check failed"; exit 1; }
mkdir -p "$OUT"

for s in $SEEDS; do
  nice -n 10 $PY -u -m dreamdesk.bc --seed "$s" --out "$OUT" --threads 2 > "$OUT/seed${s}_train.log" 2>&1 &
done
wait
for s in $SEEDS; do [ -f "$OUT/seed$s.pt" ] || { echo "seed $s did not train"; exit 1; }; done
echo "training finished"

# Each line: name, split, tasks, task seed, checkpoint (blank plays randomly).
JOBS=()
for s in $SEEDS; do
  JOBS+=("seed${s}_test test 100 12345 $OUT/seed$s.pt" "seed${s}_train train 50 54321 $OUT/seed$s.pt")
done
JOBS+=("random_test test 100 12345 ")

run_slot() {  # one private desktop, working through every third job
  local slot="$1" i job name split tasks seed ckpt
  for ((i = slot; i < ${#JOBS[@]}; i += 3)); do
    read -r name split tasks seed ckpt <<< "${JOBS[$i]}"
    nice -n 10 bash scripts/private.sh $((93 + slot)) $PY -u -m dreamdesk.evaluate ${ckpt:+--checkpoint "$ckpt"} \
      --split "$split" --tasks "$tasks" --task-seed "$seed" --out "$OUT/$name.jsonl" > "$OUT/$name.log" 2>&1 < /dev/null
  done
}
for slot in 0 1 2; do run_slot "$slot" & done
wait
echo "testing finished"
$PY -m dreamdesk.report_arm_a "$OUT" | tee "$OUT/report.txt"
