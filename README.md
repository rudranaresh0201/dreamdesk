# DreamDesk

Openpilot for computers: drop a small agent into an app it has never seen. With no instructions, no LLM and no human, it explores, builds a simulator of the app in its head, practises inside it, then does real tasks.

**Status:** early. The calculator pipeline, the sandbox and two simple explorers work. On 10 real apps, count-based novelty didn't beat random pressing on screens found (4 of 10 apps; see `experiments/explore_results.md`). A small world model trained only on that exploration predicts 5 steps ahead better than memorising, including in situations it never saw (6 of 6 apps, 153× real speed; see `experiments/world_model_results.md`). A policy trained only inside that dream reached goals it had practised (86% vs 64% for random) but not new ones (23% vs 24%), while the dream's own forecast of real success was off by just 2 points pooled. So the dream was mostly honest; the learned policy just didn't generalise (see `experiments/stage4_results.md`).

- The plan and evidence: [PLAN.md](PLAN.md)
- Run a command with no access to your real files, drives, network or desktop: `scripts/sandbox.sh COMMAND...`
- Prove the sandbox holds: `python3 tests/check_sandbox.py`
- Needs Linux with bubblewrap, Xvfb, AT-SPI and GNOME Calculator.
