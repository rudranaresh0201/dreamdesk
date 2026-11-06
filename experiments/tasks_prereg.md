# Stage 5, step 2 pre-registration: does the agent do real tasks in an app it has only briefly explored?

Written 2026-11-06, after the val pilot (`runs/s5_pilot`, 10 goals per app, 1 seed, used only to find bugs) and before any agent is run on the final split. Changes later go under "Deviations".

## Question
After exploring a held-out app for B real clicks, does an agent that plans inside its fine-tuned dream reach real goals more often than an agent that plans on a map of the same B clicks?

## Fixed from earlier steps
- **Held-out apps:** disk-usage, files, logs (step 1).
- **Budgets:** the first 100, 300 and 1,000 training clicks (`dreamdesk/budget.py`).
- **Dreams:** the fine-tuned models of step 1b (`runs/ft/finetune_{app}_B{b}_seed{0,1,2}.pt`), used together as a 3-member ensemble; thresholds 0.7/0.7. Nothing is retrained.

## Test data: the sealed seed 5
- **What it is:** recordings `data/explore_seed5`, made 2026-11-06 with the same settings as seeds 0–4 and never scored. They're added as split "final" with every old id kept (`dreamdesk/add_split.py` → `data/wm_final`, `data/budget_final`). The budgets' training clicks are checked identical to those the models trained on.
- **Goals:** 50 per app (logs has 61 scorable, disk-usage 76, files 120), picked by `real_eval.pick_goals(rule="pilot")` from `data/wm_final`: any scorable goal, at random with the fixed seed. The same 150 goals for every agent and budget.
- **What counts as success:** the Stage 4 definition. All goal elements show in the real app's accessibility tree within 10 steps of a fresh start.

## Agents (in the sandbox, `scripts/stage5_tasks.sh runs/s5_final final 50 3 "0 1 2"`)
- **Random:** a random allowed action each step. Knows nothing, so there's one arm for all budgets.
- **Graph-B:** the Stage 4 map agent, built from the first B clicks only.
- **Planner-B:** the Stage 4 dream planner (beam width 8, depth 5, λ 0, plan-following with match 0.8), on the fine-tuned ensemble with the app's bank from the first B clicks.
- **Seeds:** 0, 1 and 2 for every arm. Real apps aren't fully repeatable, and per goal, success is averaged over seeds.

## Hypotheses and analysis (`python3 -m dreamdesk.stage5_report runs/s5_final --split final`)
- **H1 (primary):** at B = 300, pooled over the 3 apps, Planner − Graph > 0, with the 95% paired-bootstrap interval over goals above 0.
- **H2:** Planner − Random > 0 (interval above 0) at every budget.
- **Also reported, no pass/fail:** B = 100 and 1,000 comparisons, per-app success, Graph − Random, the success-against-budget curve, and subgroups:
  - map-covered goals: some screen in the first B clicks showed every goal element together;
  - goals not map-covered;
  - goals with an element never seen in the first B clicks.

## Predictions (written before running)
- **H1 holds.** In the pilot the planner was ahead at every budget (+10 to +17 points, 30 goals).
- **Graph improves more with budget than the planner** does, so the gap narrows at 1,000.
- **Almost all goals are map-covered, even at B = 100** (29 of 30 in the pilot). So any planner win comes from routing better on noisy real screens, not from reaching screens the map never saw. This is noted now so it isn't presented later as "imagining unseen screens".

## Deviations
(none yet)
