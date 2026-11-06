# Generalisation results: on combo goals the map collapses, the dream doesn't

Run 2026-11-06, 20:28–22:47, once, on the sealed seed 6 of files, as pre-registered in `experiments/generalise_prereg.md` (38e9f3e).
- **Runs:** 18 real runs (3 arms × 2 budgets × 3 seeds). No errors.
- **Seed 6:** 999 transitions, of which 137 elements and 732 screens were new. The budget training clicks were checked identical to those the models trained on.
- **Goals:** 60 seen at each budget; 32 combo at B = 100 and 23 at B = 300 (fewer than the 60 allowed, because seed 6 had no more).
- **Files:** `runs/gen_final/report.md`, raw files in `runs/gen_final/`.

## G1 PASS, G2 FAIL

| Hypothesis | Result | Verdict |
|---|---|---|
| G1: on combo goals, Planner − Graph > 0 | **+11.5** points [+5.5, +18.8], n = 55 | **PASS** |
| G2: on combo goals, Planner − Random > 0 | +4.8 [−2.4, +12.7] | FAIL |

## Success

| Budget | Kind | n | Random | Graph (map) | Planner (dream) |
|---|---|---|---|---|---|
| 100 | seen | 60 | 26.7% | 39.4% | 47.2% |
| 100 | combo | 32 | 11.5% | 4.2% | **19.8%** |
| 300 | seen | 60 | 27.8% | 47.2% | 46.7% |
| 300 | combo | 23 | 5.8% | 0.0% | 5.8% |

## All comparisons (pooled over budgets)

| Comparison | Kind | n | Difference | 95% interval |
|---|---|---|---|---|
| Planner − Graph | combo | 55 | +11.5 | [+5.5, +18.8] |
| Planner − Graph | seen | 120 | +3.6 | [−3.6, +10.6] |
| Planner − Random | combo | 55 | +4.8 | [−2.4, +12.7] |
| Planner − Random | seen | 120 | +19.7 | [+12.2, +27.2] |
| Graph − Random | combo | 55 | −6.7 | [−12.7, −1.8] |
| Graph − Random | seen | 120 | +16.1 | [+9.7, +22.5] |
| Interaction: (Planner − Graph) on combo minus on seen | | 55 + 120 | +7.9 | [−2.2, +18.3] |

## Predictions vs outcome

| Prediction | Outcome |
|---|---|
| G1 holds | Right |
| G2 uncertain | Failed: the planner is ahead of Random on combo (+4.8) but the interval includes 0 |
| On seen goals the three are close (pilot 47–53%) | Wrong for Random: on seen goals both map and planner beat Random by 16–20 points |

## What it means
1. **The map memorises.** On seen goals it beats Random by 16 points. On combo goals it falls *below* Random (−6.7, interval below 0): it has nothing to aim at, so it heads for an old screen and spends its steps there. It reached 0 of 23 combo goals at B = 300.
2. **The dream keeps both.** It matches the map on seen goals (+3.6, interval includes 0) and beats it on combo goals (+11.5). Of the three agents, only the planner is good on both kinds.
3. **But "generalises" is only partly shown.** The dream doesn't significantly beat Random on combo goals, and the interaction interval includes 0. The honest claim is "the dream doesn't break where the map breaks", not "the dream solves new combinations well".
4. **Combo goals are hard for everyone at B = 300** (6% at best). With more exploration, the combos that are left are the rare, hard ones.

## Caveats
- **One app, one recording seed, 55 combo items.**
- **Navigation goals only, within 10 steps.**
- **Planner depth 10 was chosen on the val pilot** (as pre-registered). The graph and Random have no such setting.
- **Combo means combining known elements;** goals with elements never seen were left out.
