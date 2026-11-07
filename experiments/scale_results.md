# Test 1 results: does a prior trained on more apps make a new app's dream better?

Run 2026-11-07/08 as pre-registered in `experiments/scale_prereg.md` (deviations listed there: Math dropped, so 8
held-out apps; priors trained on Kaggle CPU; last epoch of P23 seed 2 on the laptop). 9 priors (P7, P15, P23 ×
seeds 0–2) trained once, 192 fine-tune/scratch runs scored once on val. Raw: `runs/scale_ft/*/*.json`, report:
`runs/scale_ft/report.md` (`python3 -m dreamdesk.scale_report report`).

## Gates: S1 FAIL, S2 FAIL

| Hypothesis | Result (B = 100, h5, unvisited, mean of 3 seeds; bootstrap over apps) | Verdict |
|---|---|---|
| **S1:** P23 − P7 > 0 over all 8 held-out apps | **+0.052** [−0.010, +0.119] | **FAIL** (lower bound just below 0) |
| **S2:** P23 − P7 > 0 over the 3 desktop held-out apps | −0.019 [−0.100, +0.028] | **FAIL** |

| Prediction | Outcome |
|---|---|
| S1 holds, mostly through the web apps | **Wrong on the gate**, right on the direction: the mean is +0.052 and the web apps carry it |
| S2 uncertain | Failed: no gain on desktop apps from adding web apps |

## Also reported (pre-registered, no pass/fail)

**Every prior beats scratch, everywhere.** P7 − scratch at B = 100: +0.084 [+0.049, +0.129] over 8 apps; positive in
8 of 8 apps at both budgets, for all three priors. This extends step 1b (3 desktop apps) to 8 apps including 5 web.

**B = 300:** P23 − P7 = +0.050 [+0.004, +0.100] over 8 apps, 7 of 8 apps positive. (Not the gate; reported as planned.)

**Ordering P7 ≤ P15 ≤ P23** holds in 6 of 8 apps at both budgets.

**Per app, B = 100 (mean of 3 seeds):**

| App | Memo | Scratch | P7 | P15 | P23 | P23 − P7 |
|---|---|---|---|---|---|---|
| disk-usage | 0.382 | 0.422 | **0.634** | 0.576 | 0.534 | −0.100 |
| files | 0.413 | 0.281 | 0.397 | 0.416 | 0.414 | +0.016 |
| logs | 0.422 | 0.416 | 0.521 | 0.536 | **0.549** | +0.028 |
| web-chat | 0.407 | 0.721 | 0.738 | 0.742 | **0.746** | +0.008 |
| web-fitness | 0.355 | 0.685 | 0.749 | 0.802 | **0.807** | +0.058 |
| web-quiz | 0.553 | 0.538 | 0.597 | 0.793 | **0.834** | +0.238 |
| web-todo | 0.565 | 0.681 | 0.741 | 0.768 | **0.778** | +0.036 |
| web-weather | 0.614 | 0.538 | 0.573 | 0.634 | **0.704** | +0.131 |

## Exploratory (subsets not pre-registered as hypotheses; read as hints)

| B = 100 | P23 − P7 | P15 − P7 | P23 − P15 |
|---|---|---|---|
| 5 web held-out apps | **+0.094** [+0.029, +0.173] | +0.068 [+0.022, +0.135] | **+0.026** [+0.006, +0.051] |
| 3 desktop held-out apps | −0.019 [−0.100, +0.028] | −0.008 [−0.058, +0.019] | −0.011 [−0.042, +0.013] |

- On web held-out apps, more web apps in the prior help, and **P15 → P23 still helps** (+0.026), so the gain is not
  only from having seen web apps at all.
- On desktop held-out apps, web apps in the prior don't help; disk-usage gets worse as web apps are added (−0.100).
  The desktop part of every prior is the same 7 apps, so this tests cross-style transfer only.

## What this means
1. **Pre-training helps a new app's dream, firmly** (8/8 apps, all priors).
2. **More apps of the same style help** (web → web), but this is an exploratory subset, and **more apps of another
   style don't** (web → desktop). The pre-registered overall test narrowly fails.
3. A fair next test of "more apps help" on desktop needs more *desktop* training apps, not more web apps.

## Caveats
- 8 held-out apps, so the bootstrap over apps is wide; one app (web-quiz, +0.238) carries much of the mean.
- Prediction quality only; no real tasks were run here.
- One recipe (Stage 3 config, 8 epochs, 500 fine-tune steps), not tuned for larger priors.
