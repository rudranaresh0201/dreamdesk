#!/usr/bin/env bash
# Web apps, same explorers and settings as Stage 2 (scripts/explore_all.sh), into data/explore_web.
# Safe to run again after an interruption: finished runs are kept, unfinished ones are set aside and redone.
#   scripts/explore_web.sh [PARALLEL]
set -u
cd "$(dirname "$0")/.."
OUT="$PWD/data/explore_web"
PARALLEL="${1:-4}"
STEPS=500
APPS="$(.venv/bin/python -c "from dreamdesk.apps import WEB_APPS; print(' '.join('web-'+a for a in WEB_APPS))")"
mkdir -p "$OUT/interrupted" "$OUT/logs"
STAMP="$(date +%Y%m%d-%H%M%S)"

JOBS=()
for seed in 0 1 2 3 4; do
  for app in $APPS; do
    for explorer in random novelty; do
      JOBS+=("$app $explorer $seed")
    done
  done
done

run_one() {
  local app="$1" explorer="$2" seed="$3"
  local name="${app}_${explorer}_seed${seed}"
  if grep -q '^finished:' "$OUT/logs/$name.log" 2>/dev/null; then return; fi
  for f in "$OUT/$name.jsonl.gz" "$OUT/logs/$name.log"; do
    [ -e "$f" ] && mv "$f" "$OUT/interrupted/${STAMP}_$(basename "$f")"
  done
  nice -n 10 timeout 30m bash scripts/sandbox.sh --out "$OUT" /usr/bin/bash -c \
    "/usr/bin/python3 -u -m dreamdesk.explore --app $app --explorer $explorer --steps $STEPS --seed $seed --out $OUT 2>&1" \
    2>&1 | grep -v dbind > "$OUT/logs/$name.log"
}
export -f run_one
export OUT STEPS STAMP

printf '%s\n' "${JOBS[@]}" | xargs -P "$PARALLEL" -L 1 bash -c 'run_one "$0" "$1" "$2"'
echo "all runs finished"
python3 -m dreamdesk.coverage "$OUT" | tee "$OUT/report.txt"
