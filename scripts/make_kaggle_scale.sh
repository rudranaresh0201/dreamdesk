#!/usr/bin/env bash
# Test 1 (experiments/scale_prereg.md): build the three prior datasets and the Kaggle upload.
# Only training apps go in; no held-out app's data is uploaded.
set -eu
cd "$(dirname "$0")/.."
TRAIN_WEB=$(.venv/bin/python -c "
import random
from dreamdesk.apps import WEB_APPS
held = {'chat', 'fitness', 'quiz', 'todo', 'weather'}
train = [a for a in WEB_APPS if a not in held]
order = random.Random('dreamdesk-p15').sample(train, 16)
print(' '.join(order))")
echo "training web apps, P15 takes the first 8: $TRAIN_WEB"
rm -rf data/prior7 data/prior15 data/prior23
mkdir -p data/prior7 data/prior15 data/prior23
for d in data/prior7 data/prior15 data/prior23; do cp data/wm7/*.pkl $d/; done
i=0
for a in $TRAIN_WEB; do
  [ $i -lt 8 ] && cp "data/wm_web/web-$a.pkl" data/prior15/
  cp "data/wm_web/web-$a.pkl" data/prior23/
  i=$((i + 1))
done
for d in data/prior7 data/prior15 data/prior23; do echo "$d: $(ls $d | wc -l) apps"; done
rm -f kaggle/dreamdesk_scale.zip
zip -qr kaggle/dreamdesk_scale.zip dreamdesk/*.py data/prior7 data/prior15 data/prior23 -x '*/__pycache__/*'
ls -la kaggle/dreamdesk_scale.zip
