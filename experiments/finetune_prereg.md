# Stage 5, step 1b pre-registration: does a 7-app prior make a new app's dream better after a short exploration?

Written 2026-11-06, after step 1 (zero-shot transfer, STOP) and before any model for this step is trained or scored. Changes later go under "Deviations".

## Question
Step 1 never let the model learn from the new app. Here it does: after exploring a held-out app for B real steps, a dream is trained on those B steps, either

- **fine-tuned:** starting from the 7-app model of step 1 (`runs/wm7/member_seed0.pt`), or
- **scratch:** starting from random weights.

Does the fine-tuned dream predict the app better than Memo (the dream is worth having) and better than scratch (the prior helps)?

## Fixed from step 1
- **Held-out apps:** disk-usage, files, logs.
- **Budgets:** 100, 300 and 1,000, built by `dreamdesk/budget.py` (`data/budget/B{b}`).
- **Thresholds:** frozen Stage 3, 0.7/0.7.
- **Measure:** val split (seed 3), mean delta F1 at horizon 5 on windows unvisited in the budget (`wm_eval.evaluate`).
- **Copy and Memo:** fitted on the budget; numbers are the same as in step 1.

## Training (identical for both arms, not tuned)
- **Data:** only the app's B budget transitions. No bootstrap resample (single members).
- **Architecture and optimiser:** Stage 3 `CONFIG`, AdamW, lr 3e-4, weight decay 0.01.
- **Schedule:** exactly 500 gradient steps (epochs repeat as needed), warmup 50 steps, cosine to 0.
- **Seeds:** 0, 1 and 2 per arm, budget and app (54 models). The seed sets batch order, dropout and, for scratch, the initial weights.
- **Model selection:** none. The model after step 500 is scored.

## Gates (at B = 300, horizon 5, unvisited, mean over the 3 seeds)
- **G1, the dream is worth having:** fine-tuned beats Memo and Copy in at least 2 of 3 apps.
- **G2, the prior helps:** fine-tuned beats scratch in at least 2 of 3 apps, and in each of those apps the worst fine-tuned seed beats the best scratch seed.
- **GO for Stage 5's "new app" claim:** both G1 and G2. Otherwise the paper says which part held.
- **Also reported, no pass/fail:** budgets 100 and 1,000, all windows, horizon 1, per-seed numbers, and the step-1 zero-shot and Stage 3 in-app numbers for reference.

## Predictions (written before running)
- Fine-tuned beats scratch at B = 100 and 300; the gap shrinks by 1,000.
- G1 is uncertain: Memo is strong at 0.40-0.45.

## Deviations
(none yet)
