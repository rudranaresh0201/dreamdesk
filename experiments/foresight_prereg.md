# Foresight pre-registration: does the dream know, before any real try, which tasks a policy will fail?

Written 2026-11-06 18:10, before any agent is run on the seed-5 goals of these apps. Changes later go under "Deviations".

## Background (exploratory, Stage 4 test split, found after its gate)
- **The signal:** a policy's success rate in the dream on a goal predicted its real success on that goal with AUROC 0.883 [0.853, 0.912].
- **The strongest real-try baseline:** the success of 3 Random runs, AUROC 0.766. The dream beat it by +0.117 [+0.074, +0.165].
- **Same goal, two policy runs:** the dream picked the one that succeeded in 89% of 264 pairs.

`dreamdesk/foresight_report.py` reproduces these numbers from `runs/real_test`. This test repeats the analysis unchanged on new data.

## Data
- **Recordings:** sealed seed 5 for all 10 apps, as split "final" (`dreamdesk/add_split.py` → `data/wm_s5`, every old id kept). It's the same seed-5 recording used for the 3 held-out apps in Stage 5 step 2, but these goals (rule "new", 30 per app) and these agents weren't run there.
- **Goals:** `pick_goals(rule="new", 30)` on "final", 295 in total (image-viewer has 25).

## Agents (nothing retrained)
- **Policies:** the 6 Stage 4 policies (`runs/ach/{dream,penalty}_seed{0,1,2}`), the frozen Stage 3 ensemble, thresholds 0.7/0.7.
- **Real runs:** each policy once (seed = its training seed), Random seeds 0–2 and Graph seed 0. Run with `DATA=data/wm_s5 scripts/real_eval.sh runs/s5_foresight final 30 3 ...`.
- **Dream runs:** each policy's dream success per goal, 5 tries (`achiever dream_eval --data data/wm_s5 --split final --goals 30`).

## Hypotheses (`python3 -m dreamdesk.foresight_report runs/s5_foresight --split final`)
- **F1 (primary):** the dream's AUROC is above 0.5, and above the Random-success AUROC. Both use 95% bootstrap intervals over goals: the lower bound of AUROC > 0.5, and the lower bound of dream − random > 0.
- **F2:** within a goal, between two policy runs that differ in real outcome and in dream rate, the higher dream rate wins more than half the time (bootstrap lower bound > 50%).
- **Also reported, no pass/fail:** AUROC of graph, goal length and other runs' dream rate, the calibration table, and per app.

## Predictions
- **F1 and F2 hold.** AUROC about 0.85.
- **Dream − other stays about 0:** the forecast is mostly "how hard is this goal in the dream". F2 is the part that is specific to the policy.

## Deviations
(none yet)
