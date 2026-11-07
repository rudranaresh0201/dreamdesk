# Test 1 pre-registration: does a prior trained on more apps make a new app's dream better?

Written 2026-11-06 23:45, before any prior for this test is trained and before any web-app data is scored. Held-out
apps were frozen in `experiments/heldout_apps.md` (2705ddc). Changes later go under "Deviations".

## Question
Step 1b showed that a 7-app prior, fine-tuned on a new app's first B clicks, beats training from scratch. Does a
prior that has seen **more apps** do better still?

## Priors (trained once, then frozen)
| Prior | Training apps |
|---|---|
| **P7** | the 7 Stage 3 desktop apps (calculator, characters, clocks, font-viewer, image-viewer, resources, text-editor), as in step 1 |
| **P15** | P7's apps + 8 web apps: the first 8 of the 16 training web apps in the order `random.Random("dreamdesk-p15").sample(train_web, 16)` |
| **P23** | P7's apps + all 16 training web apps |

- **Training web apps** are the 21 in `dreamdesk/webapps`, minus the 5 held out (chat, fitness, quiz, todo, weather).
- **Data:** train split only (recording seeds 0–2, both explorers, 500 steps each, as in Stage 2; web apps are recorded with `scripts/explore_web.sh`).
- **Recipe:** Stage 3, unchanged: `world_model train`, `CONFIG`, 8 epochs, bootstrap sample per member, seeds 0, 1 and 2 per prior, so 9 priors in all. Run on Kaggle (GPU if faster, else CPU), with the same code.
- **No tuning or selection.** The model after epoch 8 is used.

## Held-out apps and scoring (as in step 1b)
- **Apps:** desktop disk-usage, files, logs and LibreOffice Math (if its recordings pass `check_data`); web chat, fitness, quiz, todo, weather.
- **Budgets:** the first B = 100 and 300 train clicks of each held-out app (`dreamdesk/budget.py`).
- **Fine-tuning:** `dreamdesk/finetune.py` exactly as in step 1b (500 steps, warmup 50, cosine). Prior seed k is fine-tuned with seed k. Scratch is trained with seeds 0–2.
- **Score:** val split (recording seed 3), mean delta F1 at horizon 5 on windows unvisited in the budget, thresholds 0.7/0.7.
- **Per app:** mean over the 3 seeds.

## Hypotheses
- **S1 (primary):** at B = 100, P23 − P7 > 0, averaged over all held-out apps. Bootstrap over apps (10,000 resamples, 95% percentile interval), so the lower bound must be above 0.
- **S2:** at B = 100, P23 − P7 > 0 averaged over the **desktop** held-out apps alone. This is the stricter test, because the web held-out apps share a style with the web training apps. Same bootstrap. With 3–4 apps this has little power; it is reported either way.
- **Also reported, no pass/fail:**
  - P15, and the ordering P7 ≤ P15 ≤ P23;
  - B = 300;
  - scratch, Memo and Copy;
  - per app and per seed.

## Predictions
- **S1 holds,** mostly through the web held-out apps.
- **S2 is uncertain.** Web training apps may help desktop apps little, because their elements and screens look different.

## Deviations
- 2026-11-07: **LibreOffice Math dropped** from the held-out apps. Its recordings fail: after one partial run (180/500 steps) it never appears in the accessibility tree (`runs/night_scale.log`). Held-out apps are now 8 (3 desktop, 5 web). No score had been seen.
- 2026-11-07: **Device.** The first Kaggle run used the GPU with 3 trainings sharing it; after 30 min no training had finished one epoch (a lone prior7 epoch should take ~3 min), so the jobs were thrashing the GPU. Stopped and rerun on CPU, 4 at a time. Same code, recipe and seeds; no results had been seen.
- 2026-11-07: **Last epoch of P23 seed 2 on the laptop.** Kaggle version 1 stopped at its 11.25 h limit with 8 of 9 priors done and P23 seed 2 after epoch 7 of 8. That last epoch is resumed exactly (`--resume`, saved optimizer and random state) on the laptop CPU, same code, before any prior is fine-tuned or scored.
