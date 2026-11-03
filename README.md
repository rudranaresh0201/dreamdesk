# DreamDesk

Openpilot for computers: drop a small agent into an app it has never seen. With no instructions, no LLM and no human, it explores, builds a simulator of the app in its head, practises inside it, then does real tasks.

**Status:** early. The calculator pipeline, the sandbox and two simple explorers work. On 10 real apps, count-based novelty didn't beat random pressing on screens found (4 of 10 apps; see `experiments/explore_results.md`). The world model and dream training aren't built yet.

- The plan and evidence: [PLAN.md](PLAN.md)
- Run a command with no access to your real files, drives, network or desktop: `scripts/sandbox.sh COMMAND...`
- Prove the sandbox holds: `python3 tests/check_sandbox.py`
- Needs Linux with bubblewrap, Xvfb, AT-SPI and GNOME Calculator.
