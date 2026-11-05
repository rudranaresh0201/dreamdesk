# Stage 4 results: a policy trained only in the dream, tested in the real apps

Run 2026-11-06 on the test seed, once, as pre-registered in `experiments/stage4_prereg.md` (with Deviations 1 and 2). Raw per-goal files: `runs/real_test/*.jsonl`; dream evaluation: `runs/real_test/*_dream_test.json`; full report: `runs/real_test/report.md` (from `python3 -m dreamdesk.stage4_report runs/real_test --split test`).

- **Goals:** 294 (30 per app, 24 in image-viewer, which has no more), 31 novel. None is identical to a goal recorded in training.
- **Never practised:** 221 goals were never practised by any of the 3 Dream seeds, not even as a goal made up in the dream. The other 73 were practised as dreamed goals.
- **Runs:** 100 real runs (10 apps × Random 3 seeds, Graph 1, Dream 3, Penalty 3). No errors, no interruptions.
- **Where seed 2 trained:** on Kaggle's T4 (finished in about 11.5 of its 12 allowed hours), so Deviation 2's laptop fallback wasn't needed. Seeds 0 and 1 trained on the laptop.

## Gate (H1): FAILED

Dream beats Random pooled, but not on never-practised goals, and H1 needs both.

| Dream − Random | n | Difference | 95% interval |
|---|---|---|---|
| All goals | 294 | +5.4 points | [+0.8, +9.8] |
| **Never practised** | 221 | **−0.2 points** | **[−5.1, +4.8]** |
| Practised | 73 | +22.4 points | [+15.1, +30.1] |

## Real success

Per goal, success is averaged over the arm's seeds, then over goals.

| Arm | All | Familiar | Novel | Never practised | Practised | Per-seed (median, range) |
|---|---|---|---|---|---|---|
| Random | 33.6% | 37.5% | 0.0% | 23.5% | 63.9% | 33.0% [32.0, 35.7] |
| Graph | **59.9%** | **66.9%** | 0.0% | **48.4%** | **94.5%** | 1 run |
| Dream | 39.0% | 43.6% | 0.0% | 23.4% | 86.3% | 39.1% [36.7, 41.2] |
| Penalty | 36.5% | 40.7% | 1.1% | 20.5% | 84.9% | 37.4% [34.7, 37.4] |

**Per app:**

| App | n | Random | Graph | Dream | Penalty |
|---|---|---|---|---|---|
| calculator | 30 | 13.3% | 63.3% | 47.8% | 44.4% |
| characters | 30 | 35.6% | 66.7% | 48.9% | 54.4% |
| clocks | 30 | 31.1% | 90.0% | 37.8% | 30.0% |
| disk-usage | 30 | 45.6% | 60.0% | **0.0%** | **0.0%** |
| files | 30 | 30.0% | 66.7% | 46.7% | 32.2% |
| font-viewer | 30 | 81.1% | 100.0% | 92.2% | 95.6% |
| image-viewer | 24 | 41.7% | 37.5% | **8.3%** | **8.3%** |
| logs | 30 | 21.1% | 60.0% | 52.2% | 51.1% |
| resources | 30 | 14.4% | 20.0% | 11.1% | 10.0% |
| text-editor | 30 | 23.3% | 30.0% | 38.9% | 33.3% |

## Also reported

| Comparison | All | Never practised | Familiar |
|---|---|---|---|
| Dream − Graph | −20.9 [−26.9, −15.3] | −25.0 [−31.8, −18.1] | −23.3 [−29.5, −16.6] |
| Penalty − Dream | −2.5 [−4.6, −0.3] | −2.9 [−5.3, −0.3] | −2.9 [−5.4, −0.5] |
| Graph − Random | +26.3 [+20.5, +32.3] | +24.9 [+17.5, +32.3] | +29.4 [+22.9, +35.5] |

On novel goals, every arm got 0 except one Penalty win, so those differences are all about 0.

**Dream vs real (the gap), on the same goals:**

| Arm | In the dream | Real | Gap |
|---|---|---|---|
| Dream (3 seeds) | 36.7% | 39.0% | −2.3 points |
| Penalty (3 seeds) | 34.0% | 36.5% | −2.5 points |

**Per app (dream − real, points):**

| App | Dream arm | Penalty arm |
|---|---|---|
| calculator | −19 | −17 |
| characters | +6 | +2 |
| clocks | −8 | −1 |
| disk-usage | **+20** | +7 |
| files | 0 | +2 |
| font-viewer | −1 | 0 |
| image-viewer | 0 | 0 |
| logs | −2 | −5 |
| resources | −1 | 0 |
| text-editor | −17 | −13 |

The pooled gap is small, but per app it ranges from −19 to +20. In 3 apps the dream misses by more than 10 points: calculator and text-editor, where the dream *under*-states real success, and disk-usage, where it over-states it. Disk-usage is the only clear case of the dream promising more than reality.

## Predictions vs outcome

| Prediction (pre-registered) | Outcome |
|---|---|
| H1 holds | **Wrong.** Pooled yes; never practised no |
| Graph beats Dream on familiar goals | Right (−23.3 points) |
| On novel goals all agents are weak, and Dream ≥ Graph | Right, trivially: all at about 0% |
| The gap is small | Right (−2.3 points; the dream slightly *under*-states real success) |
| Penalty changes real success by less than 5 points | Right (−2.5) |

## What it means

1. **The dream didn't lie; the policy didn't generalise.**
   - Pooled, dream success matched real success within 2.5 points for both arms, and within 8 points in 7 of 10 apps. Only disk-usage looks like exploitation (20% in the dream, 0% real); in calculator and text-editor the dream was too *pessimistic*. Overall, no systematic exploit.
   - The failures sit in the policy: 86% on goals it practised, but 23% on never-practised goals, the same as random clicking.
   - So PPO in the dream learned **a lookup of practised goals, not a skill of reaching goals**.
2. **The world model is good enough to plan with; the learned policy isn't.**
   - The Graph plans a fresh route for each goal and reaches 48% of never-practised goals, about double the Dream policy.
   - Since the dream predicts real outcomes this closely, planning *inside the dream* (search through the world model's predictions instead of a learned policy) is the obvious next test. This is exploratory and needs its own pre-registration.
3. **The disagreement penalty hurt slightly.** It avoided uncertain routes that actually work in reality: Clocks fell from 37.8% to 30.0% and Files from 46.7% to 32.2%. With no exploitation to prevent, a penalty only costs.
4. **Two collapses** (diagnosed after the gate, so exploratory):
   - **disk-usage, 0%:** the policy loops "Main Menu" → an unnamed menu item, and never presses the volume button that Random and Graph use. Its dream success on these goals is also only about 20%, so it had already failed in the dream.
   - **image-viewer, 8%:** it presses "Open Files…" on most steps. Dream success is 8% too.
   - In both cases the dream predicted the failure correctly.

## Caveats

- **Goals are navigation goals** (bring up to 3 given elements onto the screen within 10 steps), not full tasks with values.
- **Graph had 1 run.** Its only randomness is the fallback action, so seeds matter less, but its interval reflects goal variation only.
- **"Practised" means as a dreamed goal.** The 73 practised goals were made up by random play in the dream and happened to match test goals. They're mostly short, common goals, which also makes them easier for Random (63.9%).
- **Seed 2 trained on a GPU** and seeds 0–1 on a CPU. Results aren't bit-identical across devices. Pooled real success per seed: Dream 39.1%, 41.2% (laptop) and 36.7% (Kaggle); Penalty 34.7%, 37.4% (laptop) and 37.4% (Kaggle). Kaggle's Dream seed is the lowest, 2.4 points below the lower laptop seed; its Penalty seed ties the higher one. With 3 seeds, a device effect can't be told apart from seed noise.
- **The training budget was halved** (Deviation 1). Training success had nearly flattened by iteration 1,000, so more iterations probably wouldn't change the never-practised result much. That isn't tested.
