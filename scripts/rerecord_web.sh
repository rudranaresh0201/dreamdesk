#!/usr/bin/env bash
# The first web recording offered typing on text *inside* fields (fixed in web_backend.TEXT_FIELDS), so it is set
# aside (data/explore_web_v0) and every web app is recorded again with the fix, then data/wm_web is rebuilt.
set -u
cd "$(dirname "$0")/.."
until grep -q "web recordings done" runs/night_scale.log; do sleep 30; done
until [ -e data/wm_web ] && grep -q "math smoke\|FAILED" runs/night_scale.log; do sleep 10; done
mv data/explore_web data/explore_web_v0; mv data/explore_web.log data/explore_web_v0.log; mv data/wm_web data/wm_web_v0
bash scripts/explore_web.sh 2 > data/explore_web.log 2>&1
.venv/bin/python -m dreamdesk.wm_data data/explore_web data/wm_web
echo "$(date +%H:%M) rerecord_web finished"
