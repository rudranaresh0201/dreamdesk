# Generalisation test pre-registration: the map memorises, does the dream generalise?

Written 2026-11-06 19:50, before the test data (seed 6) is recorded. Changes later go under "Deviations".

## Why
In Stage 5 step 2 the dream planner tied the map on held-out apps. Over 90% of those goals were on a screen the map had already seen, so the map only had to replay a memorised route. This test separates the two kinds of goals:

- **seen:** some screen in the first B explored clicks showed every goal element together, so a map can aim at it;
- **combo:** every goal element was seen while exploring, but **never all on one screen**, so a map has nothing to aim at. Reaching it needs a model that combines what it saw.

Goals with an element never seen while exploring are left out: neither agent can produce them, because the dream picks what appears from its bank of seen elements.

## Setup (all fixed from earlier steps unless stated)
- **App:** files. It's the only held-out app with enough combo goals: about 60 at B = 100 and 38 at B = 300 in seed 5, against at most 6 in logs and 1 in disk-usage.
- **Budgets:** B = 100 and 300 (`data/budget/B{b}`).
- **Dreams:** the step 1b fine-tuned models `runs/ft/finetune_files_B{b}_seed{0,1,2}.pt`, as a 3-member ensemble, thresholds 0.7/0.7. Nothing is retrained.
- **Test data:** a new sealed seed 6 of files, recorded after this file is committed (`scripts/record_seed6.sh`: same explorers and settings as seeds 0–5). It's added as split "final6" with every old id kept (`add_split.py` → `data/wm_s6`, `data/budget_s6`). The budgets' training clicks are checked identical to those the models trained on.
- **Goals:** `real_eval.pick_split_goals`. Goals are reached within 10 steps of a fresh start in final6, with up to 3 new elements (`GoalSet`, horizon 10), and tagged against the first B clicks. Up to 60 seen and up to 60 combo goals per budget, sampled with a fixed seed.
- **Agents (3 seeds each, per budget, the same goals):**
  - Random;
  - Graph (a map of the first B clicks);
  - Planner (beam width 8, λ 0, match 0.8). **Look-ahead depth is 10, not Stage 4's 5,** chosen on the val pilot only: on files B = 100, combo 6/30 vs 5/30 and seen 16/30 vs 15/30 (`runs/gen_pilot`, `runs/gen_pilot_d10`).
- **Success:** all goal elements show in the real app within 10 steps (Stage 4).
- **Run:** `scripts/gen_night.sh 10` → `runs/gen_final`. Analysis: `python3 -m dreamdesk.gen_report runs/gen_final --split final6`.

## Hypotheses
Items are (budget, goal) pairs pooled over both budgets. Success is averaged over seeds per goal, with paired bootstrap 95% intervals over items.

- **G1 (primary):** on combo goals, Planner − Graph > 0 (interval above 0).
- **G2:** on combo goals, Planner − Random > 0.
- **Also reported, no pass/fail:**
  - the same differences on seen goals, and per budget;
  - the interaction (Planner − Graph on combo minus on seen), the "memorise vs generalise" signature.

## Predictions
- **G1 holds; G2 is uncertain.** In the val pilot (1 seed, 30 combo goals): Planner 20%, Random 10%, Graph 3%.
- **On seen goals the three are close** (pilot: 47–53%).

## Limits known now
- **One app and one recording seed;** about 100 combo items in total.
- **Goals are navigation goals.**
- **"Combo" is defined against the explored screens.** An element the dream can't produce is excluded, so this tests combining known pieces, not imagining new ones.

## Deviations
(none yet)
