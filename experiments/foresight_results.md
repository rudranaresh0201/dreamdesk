# Foresight results: the dream knows, before any real try, which tasks a policy will fail

Run 2026-11-06, 17:55–20:25, once, on the sealed seed 5, as pre-registered in `experiments/foresight_prereg.md` (a5ed3c2).
- **Runs:** 100 real runs (10 apps × [6 policies + Random ×3 + Graph]) and 6 dream evaluations. No errors.
- **Items:** 1,770 (6 policy runs × 295 goals). Real success 37.9%.
- **Files:** `runs/s5_foresight/foresight.md`, raw files in `runs/s5_foresight/`.

## Both hypotheses PASS

| Hypothesis | Result | Verdict |
|---|---|---|
| F1: dream AUROC above chance and above the Random-success baseline | AUROC **0.879** [0.848, 0.910]; dream − random **+0.168** [+0.119, +0.224] | **PASS** |
| F2: within a goal, the higher dream rate picks the run that succeeds | **92.2%** of 344 pairs [83.9%, 97.1%] | **PASS** |

## All signals (AUROC for real success of a policy run on a goal)

| Signal | Needs real tries? | AUROC | 95% interval |
|---|---|---|---|
| **Dream success of this policy** | **no** | **0.879** | [0.848, 0.910] |
| Dream success of the *other* 5 policy runs | no | 0.867 | [0.834, 0.900] |
| Success of 3 Random runs | yes, 3 | 0.711 | [0.658, 0.759] |
| Success of the Graph run | yes, 1 | 0.689 | [0.647, 0.730] |
| Goal length | no | 0.543 | [0.487, 0.601] |

**Calibration (dream success rate → real success):**

| Dream success | n | Real success |
|---|---|---|
| 0 of 5 | 1,070 | 10% |
| 1–2 of 5 | 52 | 56% |
| 3–4 of 5 | 84 | 62% |
| 5 of 5 | 564 | 87% |

**Per app (exploratory):**

| App | Real success | Dream AUROC |
|---|---|---|
| calculator | 44% | 0.65 |
| characters | 61% | 0.82 |
| clocks | 33% | 0.92 |
| files | 38% | 0.89 |
| font-viewer | 91% | 0.93 |
| image-viewer | 4% | 1.00 (only 6 successes) |
| logs | 50% | 0.90 |
| resources | 17% | 0.87 |
| text-editor | 36% | 0.84 |
| disk-usage | 0% | undefined (no success) |

## Predictions vs outcome

| Prediction | Outcome |
|---|---|
| F1 and F2 hold, AUROC about 0.85 | Right: 0.879, the same as the exploratory 0.883 |
| Dream − other about 0 | Nearly: +0.011 [+0.001, +0.022]. It's small but above 0 |

## What it means

1. **The finding replicates on fresh data.** With zero real tries, a policy's success in the dream predicts its real success (AUROC 0.88), and does so better than 3 real Random tries (0.71) or a real Graph try (0.69).
2. **It's mostly goal difficulty, but not only that.** The other policies' dream success is almost as good (0.867), so most of the signal is "the dream knows which goals are hard". The small extra for the policy's own dream run, and the 92% within-goal pair accuracy, show the dream also knows *which policy* will make it.
3. **It's calibrated at the ends.** "Never in the dream" means a 10% real chance, and "always in the dream" means 87%.
4. **It's weakest in calculator** (0.65), where Stage 4 found the dream most pessimistic.

## Caveats
- **These are the Stage 4 policies, which mostly memorised.** Foresight is measured for these policies, not for a planner.
- **Disk-usage had no real successes** (the Stage 4 collapse), so it adds no information to the AUROC.
