#!/usr/bin/env bash
# Fresh recordings (seed 5) for the Stage 4b test (dream forecast and planning), same explorers and settings as
# Stage 2 (scripts/explore_all.sh), kept in their own folder so the Stage 2/3 data stays untouched.
# Safe to rerun: finished runs are kept, unfinished ones set aside and redone.
set -u
cd "$(dirname "$0")/.."
OUT="$PWD/data/explore_seed5"
PARALLEL="${1:-4}"
STEPS=500
APPS="calculator text-editor files characters clocks disk-usage font-viewer image-viewer logs resources"
mkdir -p "$OUT/interrupted" "$OUT/logs"
STAMP="$(date +%Y%m%d-%H%M%S)"
JOBS=()
for app in $APPS; do for explorer in random novelty; do JOBS+=("$app $explorer 5"); done; done
run_one() {
  local app="$1" explorer="$2" seed="$3"
  local name="${app}_${explorer}_seed${seed}"
  if grep -q '^finished:' "$OUT/logs/$name.log" 2>/dev/null; then return; fi
  for f in "$OUT/$name.jsonl.gz" "$OUT/logs/$name.log"; do
    [ -e "$f" ] && mv "$f" "$OUT/interrupted/${STAMP}_$(basename "$f")"
  done
  nice -n 10 timeout 3h bash scripts/sandbox.sh --out "$OUT" /usr/bin/bash -c \
    "/usr/bin/python3 -u -m dreamdesk.explore --app $app --explorer $explorer --steps $STEPS --seed $seed --out $OUT 2>&1" \
    2>&1 | grep -v dbind > "$OUT/logs/$name.log"
}
export -f run_one
export OUT STEPS STAMP
printf '%s\n' "${JOBS[@]}" | xargs -P "$PARALLEL" -L 1 bash -c 'run_one "$0" "$1" "$2"'
echo "all seed 5 runs finished"
