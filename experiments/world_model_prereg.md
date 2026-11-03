# Stage 3 pre-registration: can a small world model predict real apps better than memorising?

Draft, written 2026-11-04 before any model is scored on the test seed. Development uses only the train and val seeds. This file is committed before the single test run, and anything changed after that commit is listed under "Deviations".

## Question
Trained only on the agent's own task-free exploration (Stage 2), can a small neural world model predict what real desktop apps do, including for (screen, action) pairs it never saw, and especially several steps ahead, better than a lookup table of what it saw?

## Data
- **Source:** all 100 Stage 2 runs (`data/explore/`), converted by `dreamdesk/wm_data.py` into `data/wm/`. That's 10 apps and 49,632 transitions.
- **Split by seed, fixed before any training:**

  | Seed | Use |
  |---|---|
  | 0, 1, 2 | Train |
  | 3 | Val: all model, threshold and design choices |
  | 4 | Test: run once |

  Both explorers go in every split.
- **A screen** is the set of element tokens (role, name, text, pressable, states). Paths and boxes are left out, and duplicates collapse.
- **An unvisited item:** its first step's (abstract screen, action) pair never appears in training. The abstract screen is `explore.screen_key`. The action is the verb plus the target's role and name, plus the typed word.

## Models
- **Copy:** nothing changes.
- **Memo:** the most frequent training change for, in order:
  1. this exact screen and action
  2. else the same abstract screen and action
  3. else the same action anywhere
  4. else nothing changes

  The change is applied to the current screen.
- **World model** (`dreamdesk/world_model.py`):
  - Element features: role, name and text character trigrams, states, depth.
  - A 2-layer transformer over the screen's elements plus an action token.
  - Outputs: a vanish probability for each current element, and an appear probability for each element in the app's training bank.
  - One model is shared across all 10 apps.
  - **Ensemble:** 5 members trained with seeds 0–4, each on a bootstrap sample of the training transitions. The ensemble averages probabilities, then thresholds them.
  - Thresholds and the final configuration are chosen on val and frozen here at commit time.

## Measures
- **Delta F1.** Compare the changes predicted from the start screen with the real changes, where a change is an element that vanished or appeared. If both sets are empty, the score is 1.
- **Horizon 1:** each transition.
- **Horizon 5:** every window of 5 consecutive steps in an episode. Each model rolls forward on its own predictions, using the real actions, and is scored on the screen after step 5 against the start screen.

## Gate
- **Gate apps:** apps with at least 50 unvisited horizon-5 windows in the test split. This is a count from the data, independent of any model.
- **The world model ensemble passes if, on unvisited horizon-5 windows:**
  1. **Majority of apps:** its mean delta F1 is higher than both Copy's and Memo's in a majority of gate apps.
  2. **Across apps:** the average over gate apps, with each app weighted equally, is higher than Memo's. The 95% paired bootstrap interval of the difference must exclude 0. Resampling is over windows within each app, with 2,000 resamples.
  3. **Speed:** batched ensemble predictions on the laptop CPU run at least 100× faster than a real step. That's at least 113 predictions per second against the 884 ms Stage 2 median, measured during the test evaluation.

## Also reported
- Horizon 1 and horizon 5 on all, visited and unvisited items, per app.
- **Spread across members:** each single member's score as median, p10 and p90 over the 5 members, next to the ensemble's.
- **Bank coverage:** the share of real appearing elements in test that were never seen in training. No model here can predict those.
- **Uncertainty**, which feeds Stage 4:
  - Disagreement is 1 minus the mean pairwise delta F1 between members' predictions.
  - Report AUROC of disagreement for picking out wrong predictions (delta F1 below 0.5), at horizon 1, on test.
  - Report the Spearman correlation between disagreement and error.
- Apps outside the gate: the visited cases show how much memorising alone achieves.

## Prediction
- Memo will be close to perfect on visited items and hard to beat there.
- The world model will beat Memo on unvisited items at horizon 5 in apps with reusable structure (clocks, files, text-editor), and may not in calculator and resources, where many changes are text the model has never seen.
- Disagreement will be clearly higher on wrong predictions (AUROC above 0.7). That isn't a gate.

## Deviations
None yet.
