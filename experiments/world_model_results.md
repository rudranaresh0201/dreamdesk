# Stage 3 results: a small world model predicts real apps better than memorising

Run on 2026-11-05, as pre-registered in `experiments/world_model_prereg.md`, with thresholds frozen in commit `331e28e` before the single test run. The test split is seed 4, and no model had been scored on it before. Raw per-item scores are in `runs/wm/test_report.json`, and the printed report is in `runs/wm/test.log`.

## Gate: PASS
Gate apps are those with at least 50 unvisited horizon-5 test windows: calculator, clocks, files, logs, resources and text-editor.

| Rule | Needed | Result |
|---|---|---|
| 1. Beats Copy and Memo at horizon 5 on unvisited windows | Majority of the 6 gate apps | **6 of 6** |
| 2. Equal-weight mean difference vs Memo | 95% interval above 0 | **+0.221**, interval [+0.201, +0.239] |
| 3. Speed on the slowest app | ≥100× a real step (≥113 predictions/s) | **173 predictions/s** (files), **153×** a real step |

## Horizon 5, unvisited windows (delta F1, higher is better)
| App | Windows | Copy | Memo | Ensemble | Single members p10 / median / p90 |
|---|---|---|---|---|---|
| calculator | 149 | 0.013 | 0.288 | **0.483** | 0.413 / 0.450 / 0.458 |
| clocks | 300 | 0.003 | 0.441 | **0.637** | 0.565 / 0.573 / 0.604 |
| files | 258 | 0.000 | 0.363 | **0.585** | 0.507 / 0.530 / 0.536 |
| logs | 113 | 0.000 | 0.594 | **0.699** | 0.622 / 0.642 / 0.662 |
| resources | 91 | 0.011 | 0.373 | **0.625** | 0.532 / 0.571 / 0.583 |
| text-editor | 376 | 0.000 | 0.236 | **0.588** | 0.486 / 0.560 / 0.577 |

The other apps have too few unvisited windows to count: image-viewer 32, characters 1, disk-usage 1, font-viewer 0.
- **The ensemble beats its best single member in every gate app.** Averaging 5 members is worth about 0.03 to 0.06 delta F1 here.
- **Horizon 1 on unvisited items:** the ensemble beats Memo in all gate apps. The range is 0.51 to 0.67, against Memo's 0.26 to 0.54.

## Horizon 5, all windows and visited windows
| App | Memo, all | Ensemble, all | Memo, visited | Ensemble, visited |
|---|---|---|---|---|
| calculator | 0.369 | 0.519 | 0.386 | 0.526 |
| characters | 0.666 | 0.745 | 0.666 | 0.745 |
| clocks | 0.549 | 0.623 | 0.607 | 0.615 |
| disk-usage | 0.623 | 0.707 | 0.623 | 0.707 |
| files | 0.468 | 0.601 | 0.539 | 0.612 |
| font-viewer | 0.639 | 0.772 | 0.639 | 0.772 |
| image-viewer | **0.645** | 0.563 | **0.647** | 0.554 |
| logs | 0.638 | 0.714 | 0.645 | 0.716 |
| resources | 0.339 | 0.607 | 0.335 | 0.605 |
| text-editor | 0.308 | 0.565 | 0.364 | 0.547 |

- **Visited and unvisited here describe only a window's first step.** Later steps can still reach new situations, which is why Memo is far from perfect even on visited windows.
- **Image-viewer is the one app where Memo wins**, on both all and visited windows. This wasn't analysed further, because the per-app breakdown wasn't pre-registered for diagnosis.

## Bank coverage
This is the share of real appearing test elements never seen in training, which no model here can predict:

| App | Never seen |
|---|---|
| resources | 21.0% |
| calculator | 17.7% |
| text-editor | 12.9% |
| characters, files | 4.3% |
| clocks, font-viewer | 2.7% |
| logs | 1.4% |
| disk-usage | 1.0% |
| image-viewer | 0.8% |

The apps with the most unseen text (resources, calculator, text-editor) set a ceiling on any model that picks appearing elements from a bank.

## Uncertainty: does member disagreement flag wrong predictions?
Measured at horizon 1, where a wrong prediction means delta F1 below 0.5.
- **AUROC by app:** logs 0.805, files 0.791, disk-usage 0.758, clocks 0.708, text-editor 0.682, resources 0.648, calculator 0.642, image-viewer 0.641, font-viewer 0.613, characters 0.533.
- **Median AUROC is 0.665.** Spearman correlation with error is 0.14 to 0.61.
- The prediction was AUROC above 0.7. That held in **4 of 10 apps only**. Disagreement is a useful but weak signal, and it's weakest in calculator and resources, where unseen text dominates. Stage 4 relies on it to penalise dream rollouts, so this matters. See "What this means".

## Against the pre-registered prediction
| Prediction | Outcome |
|---|---|
| Memo close to perfect on visited items | **Wrong.** Memo scored 0.34 to 0.65 on visited horizon-5 windows, and the ensemble beat it there too in 9 of 10 apps |
| World model beats Memo on unvisited horizon 5 in clocks, files and text-editor | **Right** |
| It may not beat Memo in calculator and resources | **Too pessimistic.** It won both, by +0.20 and +0.25 |
| Disagreement AUROC above 0.7 | **Mostly wrong.** Above 0.7 in 4 of 10 apps, median 0.665 |

## Caveats
- **The chosen thresholds (0.7, 0.7) are at the top edge of the pre-registered grid.** Higher values might score better. The grid wasn't widened after the fact.
- **The unit is one app's exploration data.** Train, val and test are different seeds of the same 10 apps and the same explorers, not different apps. This shows generalisation to new situations within an app, not to new apps. That is Stage 5's question.
- Delta F1 is over element tokens. A prediction can miss only a changed text value and still lose the whole element.
- One laptop, one Linux version, accessibility trees only, discrete actions.

## What this means
- **The claim this supports:** a 2-layer transformer trained only on about 30,000 transitions of the agent's own task-free exploration predicts real app behaviour at 5 steps better than a lookup of past experience, including for situations it never saw. It runs at about 150 to 480× real speed (173 to 541 predictions/s) on a laptop CPU, so practising in it is cheap.
- **What's weak:** member disagreement flags errors only moderately. Before relying on it in Stage 4, compare it with simpler signals, such as the max vanish or appear probability near the threshold, and with rollout truncation alone.
- **Next:** the playable dream demo, and Stage 4 (a goal-conditioned policy trained in the dream, with real-app tests).
