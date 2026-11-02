#!/usr/bin/env bash
# Surveys candidate apps inside the sandbox, one at a time, reading only.
# Terminals, Disks, Update Manager, keyring, online accounts, email and Discord are never on this list.
#   scripts/survey_apps.sh data/survey
set -u
OUT="$1"
cd "$(dirname "$0")/.."
mkdir -p "$OUT"
FILE="$(realpath "$OUT")/apps.jsonl"
while read -r name command; do
  [ -z "$name" ] && continue
  command -v "${command%% *}" > /dev/null || { echo "{\"app\": \"$name\", \"started\": false, \"note\": \"not installed\"}" | tee -a "$FILE"; continue; }
  timeout 90 nice -n 10 bash scripts/sandbox.sh --out "$OUT" /usr/bin/python3 -m dreamdesk.survey_apps "$name" "$FILE" $command 2>&1 | grep -E '^\{' \
    || { echo "{\"app\": \"$name\", \"started\": false, \"note\": \"sandbox run failed or timed out\"}" | tee -a "$FILE"; }
done <<'APPS'
calculator gnome-calculator
text-editor gnome-text-editor
files nautilus --new-window
characters gnome-characters
clocks gnome-clocks
disk-usage baobab
font-viewer gnome-font-viewer
image-viewer loupe
document-viewer papers
logs gnome-logs
settings env XDG_CURRENT_DESKTOP=GNOME gnome-control-center
writer libreoffice26.8 --norestore --writer
sheet libreoffice26.8 --norestore --calc
slides libreoffice26.8 --norestore --impress
draw libreoffice26.8 --norestore --draw
math libreoffice26.8 --norestore --math
resources resources
dialog-list zenity --list --column=Item a b c
chrome google-chrome --no-sandbox --test-type --no-first-run --password-store=basic --force-renderer-accessibility --user-data-dir=/tmp/chrome-profile about:blank
APPS
