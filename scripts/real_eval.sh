#!/usr/bin/env bash
# Stage 4 real-app tests, inside the sandbox: every app x agent, finished runs kept, unfinished redone.
#   scripts/real_eval.sh OUT SPLIT GOALS PARALLEL "AGENT[:NAME[:CKPT]] ..."
# e.g. scripts/real_eval.sh runs/real_pilot val 20 2 "random graph achiever:dev:runs/ach_dev/achiever.pt"
set -u
cd "$(dirname "$0")/.."
OUT="$(realpath -m "$1")"; SPLIT="$2"; GOALS="$3"; PARALLEL="$4"; AGENTS="$5"
APPS="calculator characters clocks disk-usage files font-viewer image-viewer logs resources text-editor"
mkdir -p "$OUT/logs" "$OUT/interrupted"
JOBS=()
for agent in $AGENTS; do for app in $APPS; do JOBS+=("$app $agent"); done; done
run_one() {
  local app="$1" spec="$2"
  IFS=: read -r agent name ckpt <<< "$spec"
  name="${name:-$agent}"
  local base="${app}_${name}_${SPLIT}_seed0"
  if grep -q '^finished:' "$OUT/logs/$base.log" 2>/dev/null; then return; fi
  for f in "$OUT/$base.jsonl" "$OUT/logs/$base.log"; do [ -e "$f" ] && mv "$f" "$OUT/interrupted/$(date +%s)_$(basename "$f")"; done
  local extra=""; [ -n "${ckpt:-}" ] && extra="--ckpt $ckpt"
  nice -n 10 timeout 2h bash scripts/sandbox.sh --out "$OUT" /usr/bin/bash -c \
    ".venv/bin/python -u -W ignore -m dreamdesk.real_eval --app $app --agent $agent --name $name $extra --split $SPLIT --goals $GOALS --out $OUT 2>&1" \
    2>&1 | grep -v dbind | grep -v '^$' > "$OUT/logs/$base.log"
}
export -f run_one
export OUT SPLIT GOALS
printf '%s\n' "${JOBS[@]}" | xargs -P "$PARALLEL" -L 1 bash -c 'run_one "$0" "$1"'
echo "all real runs finished"
