# Stage 5 step 1b results: a 7-app prior, fine-tuned on a short exploration of a new app

Run 2026-11-06, 12:23–14:19 on the laptop, once, as pre-registered in `experiments/finetune_prereg.md` (commit 1902071). 54 models (3 held-out apps × 3 budgets × 2 arms × 3 seeds), each trained for 500 steps (about 95 s) and scored on val. Raw results: `runs/ft/*.json`. Report: `python3 -m dreamdesk.finetune report` (`runs/ft_report.txt`).

## Gates (B = 300, horizon 5, unvisited windows, mean of 3 seeds): both PASS, 3 of 3 apps

| App | Copy | Memo | Scratch (best seed) | **Fine-tuned (worst seed)** | G1 (> Memo) | G2 (> scratch) |
|---|---|---|---|---|---|---|
| disk-usage | 0.043 | 0.418 | 0.441 (0.449) | **0.698** (0.688) | yes | yes |
| files | 0.003 | 0.404 | 0.302 (0.335) | **0.446** (0.442) | yes | yes |
| logs | 0.012 | 0.449 | 0.430 (0.456) | **0.526** (0.521) | yes | yes |

- **G1, the dream is worth having:** PASS, 3 of 3.
- **G2, the prior helps:** PASS, 3 of 3, with the worst fine-tuned seed above the best scratch seed in every app.

## All budgets (horizon 5, unvisited; seeds in brackets)

| App | B | n windows | Copy | Memo | Zero-shot (step 1) | Fine-tuned | Scratch |
|---|---|---|---|---|---|---|---|
| disk-usage | 100 | 279 | 0.022 | 0.382 | 0.339 | **0.627** (0.636, 0.617, 0.627) | 0.422 (0.376, 0.471, 0.419) |
| disk-usage | 300 | 70 | 0.043 | 0.418 | 0.326 | **0.698** (0.688, 0.703, 0.703) | 0.441 (0.431, 0.449, 0.443) |
| disk-usage | 1000 | 5 | 0.000 | 0.470 | 0.206 | **0.812** (0.826, 0.808, 0.802) | 0.594 (0.488, 0.668, 0.626) |
| files | 100 | 396 | 0.003 | **0.413** | 0.283 | 0.402 (0.402, 0.400, 0.403) | 0.280 (0.325, 0.308, 0.207) |
| files | 300 | 313 | 0.003 | 0.404 | 0.286 | **0.446** (0.450, 0.446, 0.442) | 0.302 (0.334, 0.335, 0.238) |
| files | 1000 | 203 | 0.000 | 0.439 | 0.274 | **0.462** (0.461, 0.464, 0.460) | 0.291 (0.361, 0.244, 0.268) |
| logs | 100 | 595 | 0.013 | 0.422 | 0.254 | **0.505** (0.506, 0.502, 0.509) | 0.416 (0.411, 0.403, 0.434) |
| logs | 300 | 425 | 0.012 | 0.449 | 0.269 | **0.526** (0.530, 0.527, 0.521) | 0.430 (0.424, 0.411, 0.456) |
| logs | 1000 | 230 | 0.004 | 0.521 | 0.275 | **0.523** (0.524, 0.525, 0.520) | 0.443 (0.427, 0.443, 0.459) |

Horizon 1, unvisited (mean of seeds), fine-tuned vs scratch: disk-usage 0.78 / 0.83 / 0.70 vs 0.40 / 0.31 / 0.35; files 0.37 / 0.40 / 0.40 vs 0.22 / 0.22 / 0.20; logs 0.59 / 0.54 / 0.52 vs 0.43 / 0.42 / 0.41 (B = 100 / 300 / 1,000).

## Predictions vs outcome

| Prediction | Outcome |
|---|---|
| Fine-tuned beats scratch at B = 100 and 300 | Right, in all 3 apps |
| The gap shrinks by B = 1,000 | **Wrong.** It stays about 0.08–0.22 |
| G1 uncertain (Memo strong) | Passed 3 of 3, but narrowly in files (+0.04) and logs (+0.08) |

## What it means

1. **Zero-shot transfer failed, but a prior plus a short exploration works.** Given 100–300 real steps of a new app, the dream that already knows 7 other apps learns it much better than a dream starting from nothing. It also beats memorising those same steps.
2. **The prior is worth more than 10× the data for scratch training.** Scratch at 1,000 steps is below fine-tuned at 100 steps in all 3 apps (disk-usage 0.59 vs 0.63, files 0.29 vs 0.40, logs 0.44 vs 0.51).
3. **Disk-usage is the strongest case.** At 300 steps, fine-tuned reaches 0.70, near the Stage 3 in-app model trained on the app's full data (0.79, from step 1).

## Caveats

- **This measures prediction, not tasks.** It doesn't yet show that the agent *does tasks* in a new app with fewer real steps. That needs the planner on held-out apps, in the real app, under a new pre-registration.
- **The margins over Memo are small in files (+0.04) and logs (+0.08).** No bootstrap interval over windows was pre-registered; the windows within an app are correlated (overlapping episodes).
- **Disk-usage B = 1,000 has only 5 unvisited windows,** so that row is noise.
- **One prior** (one 7-app model, seed 0), and only 3 held-out apps, all GNOME apps of similar style.
- **Fixed recipe, not tuned:** 500 steps and lr 3e-4 for both arms. Scratch might do better with a different recipe; that isn't tested.
