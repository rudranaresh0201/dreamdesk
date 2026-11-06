# Stage 5 step 1 results: zero-shot transfer to held-out apps

Run 2026-11-06 as pre-registered in `experiments/transfer_prereg.md`. One world model trained on 7 apps (8 epochs, final loss 0.102), scored on the val split of the held-out apps. Raw output: `runs/wm7/transfer_val.txt` and `runs/wm7/transfer_val.json`.

## Gate: STOP (0 of 3)

At budget 300, horizon 5, unvisited windows, the transferred model beat Copy everywhere but Memo nowhere:

| App | Copy | Memo (300 steps) | Transfer (0 steps of training on the app) |
|---|---|---|---|
| disk-usage | 0.043 | **0.418** | 0.326 |
| files | 0.003 | **0.404** | 0.286 |
| logs | 0.012 | **0.449** | 0.269 |

## All budgets (horizon 5, unvisited windows)

| App | B | Copy | Memo | Transfer | In-app reference (Stage 3, full data) |
|---|---|---|---|---|---|
| disk-usage | 100 | 0.022 | 0.382 | 0.339 | (0.787, n=4) |
| disk-usage | 300 | 0.043 | 0.418 | 0.326 | |
| disk-usage | 1000 | 0.000 | 0.470 | 0.206 | (n=5 windows) |
| files | 100 | 0.003 | 0.413 | 0.283 | 0.561 |
| files | 300 | 0.003 | 0.404 | 0.286 | |
| files | 1000 | 0.000 | 0.439 | 0.274 | |
| logs | 100 | 0.013 | 0.422 | 0.254 | 0.670 |
| logs | 300 | 0.012 | 0.449 | 0.269 | |
| logs | 1000 | 0.004 | 0.521 | 0.275 | |

The in-app reference's "unvisited" is relative to its full training data, so its n differs. It's shown for scale only.

## What it means
- **The model carries over some general knowledge.** With zero training on the new app, it's far above Copy (0.25–0.34 vs about 0.01). At horizon 1 on unvisited transitions in disk-usage it even beats Memo (0.535–0.562 vs 0.386–0.510).
- **But a few hundred real steps memorised beat it** at horizon 5 in every held-out app, and its score doesn't grow with the budget, because it never trains on the new app. The budget only adds elements to its bank.
- **The in-app model is much better** (0.56–0.67). Knowing *this* app matters more than knowing apps in general, at this scale (7 apps).
- **Not tested here:** fine-tuning the 7-app model on the budget (prior + budget) against a model trained on the budget alone (scratch). That's the realistic setting for an agent that explores a new app briefly, and it needs its own pre-registration.
