# Generalisation test (files, final6)

| Budget | Kind | n | random | graph | planner |
|---|---|---|---|---|---|
| 100 | seen | 60 | 26.7% | 39.4% | 47.2% |
| 100 | combo | 32 | 11.5% | 4.2% | 19.8% |
| 300 | seen | 60 | 27.8% | 47.2% | 46.7% |
| 300 | combo | 23 | 5.8% | 0.0% | 5.8% |

Seeds per arm: B100: {'random': 3, 'graph': 3, 'planner': 3}, B300: {'random': 3, 'graph': 3, 'planner': 3}

| Comparison | Items | n | Difference | 95% interval |
|---|---|---|---|---|
| planner − graph | combo | 55 | +11.5 | [+5.5, +18.8] |
| planner − graph | seen | 120 | +3.6 | [-3.6, +10.6] |
| planner − random | combo | 55 | +4.8 | [-2.4, +12.7] |
| planner − random | seen | 120 | +19.7 | [+12.2, +27.2] |
| graph − random | combo | 55 | -6.7 | [-12.7, -1.8] |
| graph − random | seen | 120 | +16.1 | [+9.7, +22.5] |
| (planner − graph) on combo − on seen | interaction | 55+120 | +7.9 | [-2.2, +18.3] |

**G1 (dream beats the map on combo goals): PASS**
**G2 (dream beats random on combo goals): FAIL**
