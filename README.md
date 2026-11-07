# DreamDesk

Openpilot for computers: drop a small agent into an app it has never seen. With no instructions, no LLM and no human, it explores, builds a simulator of the app in its head, practises inside it, then does real tasks.

**Status:** early. The calculator pipeline, the sandbox and two simple explorers work. On 10 real apps, count-based novelty didn't beat random pressing on screens found (4 of 10 apps; see `experiments/explore_results.md`). A small world model trained only on that exploration predicts 5 steps ahead better than memorising, including in situations it never saw (6 of 6 apps, 153× real speed; see `experiments/world_model_results.md`). A policy trained only inside that dream reached goals it had practised (86% vs 64% for random) but not new ones (23% vs 24%), while the dream's own forecast of real success was off by just 2 points pooled. So the dream was mostly honest; the learned policy just didn't generalise (see `experiments/stage4_results.md`).

**Test 1 (2026-11-08):** does a prior trained on more apps (7, 15, 23) give a new app a better dream? Narrowly no on the pre-registered test (+0.052 delta F1, interval [-0.010, +0.119] over 8 held-out apps). Every prior beats training from scratch on 8 of 8 apps. More web apps help web apps; they don't help desktop apps (see `experiments/scale_results.md`).

- The plan and evidence: [PLAN.md](PLAN.md)
- Run a command with no access to your real files, drives, network or desktop: `scripts/sandbox.sh COMMAND...`
- Prove the sandbox holds: `python3 tests/check_sandbox.py`
- Needs Linux with bubblewrap, Xvfb, AT-SPI and GNOME Calculator.
