# Stage 4 val pilot (development only, not a pre-registered result)

2026-11-05. 20 val goals (seed 3 recordings) per app, 10 apps, real apps in the sandbox, at most 10 steps.
The dev achiever was trained 600 PPO iterations in the dream (about 60 per app, 1 h on CPU, `runs/ach_dev`).

| Agent | Real successes / 200 |
|---|---|
| Random | 70 (35%) |
| Graph (map of training exploration) | **121 (60%)** |
| Dev achiever (trained only in the dream) | 84 (42%) |
| Dev achiever, success in the dream on the same goals (5 tries each) | 81 (41%) |

By goal group (real successes):

| Group | Random | Graph | Achiever |
|---|---|---|---|
| Repeat: identical to a training goal (67) | 35 | 55 | 41 |
| Familiar: elements seen together in training, not a training goal (124) | 35 | 66 | 43 |
| Novel (9, 8 of them in resources) | 0 | 0 | 0 |

Per app, real (dream): calculator 2 (3.2), characters 9 (12.4), clocks 8 (3.6), disk-usage 2 (4.0), files 12 (13.4),
font-viewer 15 (15.0), image-viewer 14 (14.0), logs 13 (8.0), resources 3 (4.0), text-editor 6 (3.4).
Graph per app: calculator 10, characters 15, clocks 16, disk-usage 9, files 15, font-viewer 20, image-viewer 16, logs 10, resources 4, text-editor 6.

## What this says
- **A policy trained only in the dream works in the real app:** 42% against random's 35%. It beats Graph in logs (13 vs 10).
- **The dream predicts real success well in aggregate:** 41% in the dream, 42% for real. There is no sign of the policy exploiting the dream yet. Per app, the dream is both too pessimistic (clocks, logs) and too optimistic (disk-usage).
- **The bottleneck is the policy, not the dream.** The achiever fails val goals inside the dream too (41%), and its dream success on training goals was still rising when training stopped. More or better RL should carry over to the real app.
- **Graph is strong** because 95% of goals are familiar. Novel goals are too few (9) to say anything.

## Fixed during the pilot (before any pre-registration)
- Graph baseline: abstract screens and per-step replanning oscillated. Late effects created spurious edges. Now it uses exact screens, follows its plan, and keeps the most common outcome per action.
- Known shared limitation: unnamed identical elements (e.g. GNOME "About" menu item) can't be told apart by any agent.
