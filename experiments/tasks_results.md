# Stage 5 step 2 results: real tasks on held-out apps after a short exploration

Run 2026-11-06, 14:53–17:41, once, on the sealed seed 5, as pre-registered in `experiments/tasks_prereg.md` (8185ab5). 63 real runs (3 apps × [Random + Graph and Planner at 3 budgets] × 3 seeds), 150 goals (50 per app). No errors or interruptions. Raw files: `runs/s5_final/*.jsonl`. Report: `runs/s5_final/report.md` (`python3 -m dreamdesk.stage5_report runs/s5_final --split final`).

## Gates: H1 FAILED, H2 FAILED

| Hypothesis | Result | Verdict |
|---|---|---|
| H1: Planner − Graph at B = 300, pooled | +2.2 points [−5.1, +9.1] | **FAIL** |
| H2: Planner − Random at every budget | B = 100: +0.0 [−8.0, +8.4]; B = 300: +10.2 [+3.3, +17.1]; B = 1,000: +16.4 [+9.1, +23.3] | **FAIL** (fails at B = 100) |

## Real success (per goal mean of 3 seeds, then over goals)

| Arm | All | disk-usage | files | logs |
|---|---|---|---|---|
| Random | 43.6% | 49.3% | 36.7% | 44.7% |
| Graph-100 | 49.1% | 30.0% | 55.3% | 62.0% |
| Planner-100 | 43.6% | 21.3% | 50.7% | 58.7% |
| Graph-300 | 51.6% | 30.0% | **56.7%** | **68.0%** |
| Planner-300 | **53.8%** | **54.7%** | 44.7% | 62.0% |
| Graph-1000 | **63.3%** | 45.3% | **76.7%** | 68.0% |
| Planner-1000 | 60.0% | **49.3%** | 60.7% | **70.0%** |

**Planner − Graph, pooled:**
- B = 100: −5.6 [−13.1, +1.8]
- B = 300: +2.2 [−5.1, +9.1]
- B = 1,000: −3.3 [−9.6, +3.1]

Every interval contains 0.

**Subgroups:** 135, 142 and 146 of the 150 goals are map-covered at B = 100, 300 and 1,000. The few goals that aren't map-covered (15, 8 and 4) are too few to say anything.

## Predictions vs outcome

| Prediction | Outcome |
|---|---|
| H1 holds | **Wrong.** A tie (+2.2, interval across 0). The pilot's +17 was 30-goal noise |
| Graph improves more with budget than the planner | Right: Graph +14 points from 100 to 1,000, Planner +16 but from a lower start; their gap stays small |
| Almost all goals are map-covered | Right (90–97%) |

## What it means

1. **On apps it never trained on, after a short exploration, the dream planner does real tasks about as well as a map of the same clicks, but not better.** Both beat Random from 300 clicks on, and both improve with more exploration.
2. **The dream doesn't help with 100 clicks.** Planner-100 equals Random (43.6%). Step 1b's better *predictions* at 100 clicks didn't turn into better *tasks*.
3. **The apps split** (per app, exploratory, no interval pre-registered):
   - **disk-usage:** the planner wins at 300 (54.7% vs 30.0%) and 1,000 (49.3% vs 45.3%). The Graph is *below Random* at every budget here.
   - **files:** the Graph wins at every budget, by up to 16 points at 1,000. Files has the largest, most changing screens (folder lists) and the weakest predictions in step 1b (0.45).
   - **logs:** about even.
4. **The goals don't test imagination.** Over 90% are on a screen the map already saw, even after 100 clicks. On these, the map just needs to route, and imagination has little to add. A fair test of "imagining unseen screens" needs longer goals that the exploration didn't reach. That isn't tested here.

## Caveats

- **Goals are navigation goals** (up to 3 elements on screen within 10 steps), as in Stage 4.
- **Random is strong** (43.6%): the goals are short, and disk-usage is small.
- **One prior** (7-app model, seed 0), and only 3 held-out apps.
