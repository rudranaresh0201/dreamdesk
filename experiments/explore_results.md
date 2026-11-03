# Stage 2 results: novelty vs random exploration

Pre-registration: [`explore_prereg.md`](explore_prereg.md). 100 runs (10 apps × 2 explorers × 5 seeds × 500 real steps) ran in the sandbox from 2026-11-03 20:36 to 2026-11-04 00:14 with `scripts/explore_all.sh 4`. There were no interruptions, and every run reached 500 steps. Raw recordings are in `data/explore/` (not in git). The numbers below come from `python3 -m dreamdesk.coverage data/explore` (`data/explore/report.txt`).

## Result
**Gate failed.** Novelty's median number of distinct screens was higher than random's in **4 of 10 apps**; the gate needed at least 6. It was lower in 3 apps and tied in 3. In no app did every seed of one explorer beat every seed of the other.

| App | Novelty median | Random median | Novelty seeds | Random seeds | Higher |
|---|---|---|---|---|---|
| calculator | 49 | 49 | 45, 47, 49, 54, 56 | 44, 47, 49, 52, 56 | tie |
| characters | 24 | 23 | 23, 24, 24, 24, 24 | 22, 22, 23, 23, 24 | novelty |
| clocks | 127 | 123 | 120, 125, 127, 127, 127 | 111, 122, 123, 139, 149 | novelty |
| disk-usage | 24 | 24 | all 24 | all 24 | tie |
| files | 164 | 160 | 132, 163, 164, 165, 182 | 127, 144, 160, 169, 177 | novelty |
| font-viewer | 6 | 6 | all 6 | all 6 | tie |
| image-viewer | 31 | 36 | 25, 27, 31, 32, 42 | 30, 36, 36, 42, 47 | random |
| logs | 115 | 127 | 89, 101, 115, 118, 159 | 120, 127, 127, 130, 140 | random |
| resources | 47 | 53 | 34, 45, 47, 51, 66 | 50, 52, 53, 61, 61 | random |
| text-editor | 147 | 134 | 134, 143, 147, 150, 158 | 105, 130, 134, 140, 142 | novelty |

The differences are small next to the spread between seeds. The largest gap in novelty's favour is text-editor, +13 screens (+10%). The largest in random's favour is logs, −12 (−9%).

## Secondary measures
Medians across 5 seeds, novelty / random.

| App | Elements found | Distinct transitions | No-op % | Screens at 100 / 250 / 500 steps, novelty | Same, random |
|---|---|---|---|---|---|
| calculator | 112 / 131 | 307 / 257 | 3 / 9 | 20 / 33 / 49 | 15 / 28 / 49 |
| characters | 10 / 10 | 142 / 128 | 14 / 17 | 17 / 22 / 24 | 18 / 21 / 23 |
| clocks | 47 / 47 | 411 / 358 | 19 / 16 | 34 / 68 / 127 | 42 / 83 / 123 |
| disk-usage | 9 / 9 | 95 / 94 | 11 / 14 | 13 / 22 / 24 | 20 / 22 / 24 |
| files | 67 / 64 | 361 / 332 | 9 / 6 | 48 / 106 / 164 | 46 / 83 / 160 |
| font-viewer | 8 / 8 | 64 / 53 | 24 / 26 | 6 / 6 / 6 | 6 / 6 / 6 |
| image-viewer | 22 / 22 | 118 / 149 | 36 / 34 | 13 / 21 / 31 | 20 / 26 / 36 |
| logs | 22 / 22 | 310 / 315 | 6 / 7 | 40 / 73 / 115 | 45 / 81 / 127 |
| resources | 17 / 17 | 190 / 208 | 13 / 11 | 20 / 29 / 47 | 19 / 45 / 53 |
| text-editor | 74 / 68 | 410 / 356 | 10 / 10 | 40 / 80 / 147 | 35 / 75 / 134 |

- **Elements:** both explorers found the same pressable and editable elements in 8 of 10 apps. Novelty's median was higher in 2. In calculator, random found more, because the calculator's history list adds an entry for every result.
- **Transitions:** novelty found more distinct (screen, action, next screen) triples in **7 of 10 apps**. That's expected from its rule, which tries each action on each screen once before repeating.
- **Small apps saturate:** disk-usage and font-viewer reached the same count in every run of both explorers, and characters nearly did. 500 steps is enough to see all of them.
- **Speed:** the median step took 884 ms (run medians ranged from 723 to 1,812 ms).
- **Errors:** files had 365 errors in 1,000 novelty and random steps combined (207 novelty, 158 random); text-editor had 3; the rest had none. 362 of the files errors were "entry '' doesn't accept text", typing into an unnamed field that refuses text. Each error ends the episode early, which also costs files some depth. No run closed the app.

## What it means
- **Random pressing is a strong explorer in these apps**, as GUI-testing studies warned. Count-based novelty didn't find more screens in a majority of apps.
- **Novelty does collect more varied data:** more distinct transitions in 7 of 10 apps, at the same number of screens. That may matter more for training a world model than screen count, but it isn't the pre-registered primary measure, so it's not claimed as a win.
- **Possible reasons it lost on screens.** These are not tested:
  - Novelty spends steps trying every action once per screen, including focus and typing actions that often change nothing. Random reaches deeper sooner in apps with long paths, such as logs and image-viewer.
  - In logs and resources, screens change by themselves, so per-screen counts keep resetting.
  - Relaunching every 30 steps keeps both explorers near the start screen.

## Decision, per the pre-registration
"If it fails: use the best simple explorer and report it."
- Neither explorer is clearly best on the primary measure. **Stage 3 trains the world model on all 100 runs**, both explorers together: 50,000 real transitions.
- The curious explorer in Stage 3 has to beat **both** random and novelty, on screens and on transitions, before it's called better. That comparison gets its own pre-registration.
- Before Stage 3, fix the files typing error: skip editable elements that refuse text. This is a recorder fix and doesn't change any result above.
