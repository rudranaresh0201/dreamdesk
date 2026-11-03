# Arm A pre-registration: behaviour cloning on the calculator

Written 2026-11-02, before any behaviour cloning model was fully trained or any held-out real-app result was seen.

**Deviation, recorded when it happened:** the code smoke test, on partial data, printed one held-out number by accident: offline accuracy 0.51 on 47 presses, from a throwaway 30-epoch model trained on 56 episodes. Under the tuning rule below, that ends tuning. The configuration in this file is therefore frozen as written, with no tuning at all.

**Deviations during the run, recorded when they happened:**
- The laptop powered off during data collection, which ended at 1,547 episodes (17,050 steps, data check passed), not about 1,900.
- The laptop powered off again during training. Seeds 1 to 4 had finished; seed 0 had not. Seed 0 was retrained from scratch with identical settings (`scripts/arm_a.sh --resume`), and the unfinished files are kept in `runs/arm_a/interrupted/`.
- The laptop powered off a third time during real-app testing. Finished test runs were kept; the 3 unfinished ones (seed 1 train-side, seed 2 held-out and train-side) were set aside in `runs/arm_a/interrupted/` and rerun from their first task.

## Question
Can a small policy, trained only by copying a scripted expert from the accessibility tree, finish calculator sums it never trained on, in the real app?

## Data
- `data/calculator/`, all files that pass `dreamdesk.check_data`. About 1,900 episodes, of which about 30% are expert.
- Train on `expert` episodes in the `train` split only. `noisy` and `random` episodes are not used here, because their actions aren't expert labels.
- Validation: the 1 in 10 train-split expert episodes where `crc32(id) % 10 == 0`. Used for checkpoint choice and any tuning.
- Tuning may use train and validation only. Any held-out result ends tuning for this arm; a change after that gets a new pre-registration.

## The held-out split, stated exactly
`is_test_task` is `(a*100 + b + ord(op)) % 5 == 0`. Because `a*100` is divisible by 5, `a` has no effect. A task is held out when:

| Op | Held out when `b` ends in |
|---|---|
| `+` | 2 or 7 |
| `*` | 3 or 8 |
| `-` | 0 or 5 |

So this tests unseen combinations of op and last digit, not randomly unseen sums. It's stricter than a random split, and the results describe only this kind of generalization. The split stays fixed because episodes were sampled under it.

## Model
- Pointer policy: goal characters and on-screen elements go in as tokens to a small transformer, which scores each pressable element.
- 64 dimensions, 3 layers, 4 heads.
- Elements with no name, no text and no press action are dropped. Tree depth is an input; the absolute path isn't.
- Window controls and the main menu can't be chosen (`BLOCKED`).
- Adam, learning rate 1e-3, batch size 64, up to 150 epochs, stop after 25 epochs with no better validation loss.
- 5 seeds: 0 to 4.

## Evaluation
All in the real app on private displays, always pressing the top-scoring element, up to 15 steps.

| Set | Tasks | Purpose |
|---|---|---|
| Held-out | 100 fixed tasks, task seed 12345, same for every seed | **Primary** |
| Train-side | 50 fixed tasks, task seed 54321 | Generalization gap. These tasks may have appeared in training |
| Random player | Same 100 held-out tasks | The baseline to beat |

**Primary metric:** real success rate on the held-out tasks. Report median, p10 and p90 across seeds. With 5 seeds, p10 and p90 sit close to the worst and best seed.

**Secondary:** offline per-step accuracy on held-out expert episodes, success by op, and the step and button of the first wrong press in each failed episode.

Episodes that error out are retried once with the same task. Any still failing count as failures and are reported.

## Gate
From `PLAN.md`, week 4: passes if the p10 held-out success rate is above the random player's rate. That only shows it beats random. It doesn't show the policy is good.

## Prediction
Median held-out success above 80%, because the job is mostly copying characters from the goal. If it falls short, I expect first mistakes on unseen op and last-digit pairs. Expert-only data contains no recovery from a wrong press, so one mistake should usually fail the whole episode.

## Limits
- One app, one kind of task, one app version, and very short episodes.
- The expert never makes mistakes, so this says little about off-path behaviour.
