# Stage 5, step 1 pre-registration: does the world model transfer to an app it never trained on?

Written 2026-11-06, before any model for this step is trained or scored. Changes later go under "Deviations".

## Question
A world model is trained on 7 apps only. Given a short exploration of a new app, used only to know which elements exist there, does it predict that app's next screens better than Copy and Memo fitted on the same short exploration?

## Held-out apps
- **The apps:** disk-usage, files, logs.
- **How they were chosen:** `sorted(random.Random('dreamdesk-stage5-heldout').sample(sorted(APPS), 3))`, drawn before this file was written.
- **Training apps:** the other 7.

## Budgets
- **Sizes:** 100, 300 and 1,000 real steps of the held-out app.
- **Where they come from:** the first B transitions of its training-seed recordings, in a fixed order (seed 0 random, seed 0 novelty, seed 1 random, ...). Built by `dreamdesk/budget.py`.
- **Model:** the 7-app model never trains on budget data. The budget decides only the app's element bank, which elements may appear.
- **Copy and Memo:** fitted on the budget.

## Model
- **Architecture:** Stage 3 `world_model.CONFIG`, 8 epochs, seed 0, one member (no ensemble in this step).
- **Thresholds:** the frozen Stage 3 thresholds, 0.7/0.7.

## Measure
- **Scored on:** the held-out app's **val** split (seed 3).
- **Metric:** mean delta F1 at horizon 5 on windows not visited in the budget, as in Stage 3 (`wm_eval.evaluate`).

## Gate (go or stop for Stage 5)
- **Go:** the transferred model beats Memo (and Copy) at horizon 5 on unvisited windows at budget 300, in at least 2 of the 3 held-out apps.
- **Stop:** otherwise. Stage 5's paper section becomes "within-app dreams work, cross-app transfer does not (yet)".
- **Also reported, no pass/fail:** budgets 100 and 1,000, all windows, and horizon 1.

## Deviations
(none yet)
