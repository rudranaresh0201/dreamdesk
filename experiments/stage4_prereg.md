# Stage 4 pre-registration: does a policy trained only in the dream work in the real app?

Written 2026-11-05, before any training run of the arms below and before any agent is scored on the test seed. The val pilot (`experiments/stage4_pilot.md`) was seen. This file is committed before training starts, and anything changed later is listed under "Deviations".

## Question
1. A goal-conditioned policy is trained with PPO only inside the Stage 3 world-model ensemble, and never touches the real app. Does it reach goals in the real apps more often than random actions?
2. How does it compare with a planner over a map of the same exploration data, which is the strongest memory-based baseline?
3. How far does success inside the dream differ from real success, and does a disagreement penalty change that or real success?

## Apps, goals, budget
- **Apps:** the 10 Stage 2 apps, run in the sandbox.
- **Goals:**
  - Test split (seed 4 recordings), built by `dreamdesk/goals.py`. A goal is up to 3 elements that were showing within 5 steps of a fresh start and weren't showing at the start.
  - Selected with `real_eval.pick_goals(rule="new")`, 30 per app:
    1. No goal identical to a goal recorded in training.
    2. All novel goals (up to 30) are taken first.
    3. The rest are familiar goals chosen at random.
  - Unreachable goals (an element never seen in training) are excluded.
  - That's 294 goals, 31 of them novel. These are counts from the data only.
- **Each attempt:** a fresh app launch, at most 10 steps, and success when every goal element is on the screen. The actions are the explorers' actions.

## Agents
| Arm | What | Runs |
|---|---|---|
| Random | A random allowed action | 5 seeds |
| Graph | Exact-screen map of training exploration plus BFS. It follows its plan and keeps the most common outcome per action (`real_eval.GraphAgent`) | 1 run |
| Dream | Achiever trained in the dream, penalty 0 | 5 seeds |
| Penalty | Same, reward minus 0.5 × ensemble disagreement per step | 5 seeds |

- **Achiever configuration:** `achiever.CONFIG` at the commit of this file. 3,000 PPO iterations, which is 300 per app, cycling through apps. 64 episodes per iteration. Training goals are half recorded (train seeds) and half dreamed.
  - Trained on Kaggle (GPU) with `kaggle/stage4_train.ipynb`, with the code and data at this commit.
  - Every goal each run practised is saved (`practised_goals.json`).
- **Choices fixed without tuning on val:**
  - The 3,000 iterations: the pilot's dream success was still rising at 600.
  - The penalty of 0.5: the mean disagreement is about 0.3–0.5 per step, so the penalty is comparable to the success reward over a few steps.
- **At test time** the achiever samples from its policy.

## Measures
- **Real success rate:** per app, pooled over the 294 goals, and by group:
  - familiar / novel
  - never practised / practised (a goal counts as practised if it's in that run's `practised_goals.json`)
- **Dream success:** `achiever dream_eval` on the same goals, 5 tries each.
- **Gap:** dream success minus real success.
- **Seeds:** policy and random results are reported as median and range over 5 seeds.

## Primary test (the Stage 4 gate)
- **H1: Dream beats Random.**
  - For each goal, average success over the 5 Dream seeds and over the 5 Random seeds.
  - The pooled difference (Dream − Random) over the 294 goals has a 95% paired bootstrap interval above 0. The bootstrap uses 2,000 resamples over goals.
  - It must also be above 0 on never-practised goals, where "never practised" means not practised by any of the 5 Dream seeds.

## Also reported (no pass/fail)
- Dream vs Graph, and Penalty vs Dream: the same paired bootstrap difference and interval, pooled and by group.
- The gap for Dream and Penalty, per app and pooled.
- **Prediction:**
  - H1 holds.
  - Graph beats Dream on familiar goals.
  - On novel goals all agents are weak, and Dream ≥ Graph.
  - The gap is small (pilot: 41% dream vs 42% real).
  - Penalty changes real success by less than 5 points.

## Running the test
1. Train with the notebook. Download `achiever_results.zip` and unzip it into `runs/ach/`.
2. `achiever dream_eval --split test` for each policy run.
3. Real runs in the sandbox with `scripts/real_eval.sh` on `--split test --goals 30`, for all agents and seeds. Each run is done once. Finished runs are kept, and interrupted ones are redone from the start of that app.
4. Write `experiments/stage4_results.md` from the raw per-goal files.

## Deviations
None yet.
