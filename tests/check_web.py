"""Checks the web backend on a small real page. Run inside the sandbox:

  scripts/sandbox.sh python3 tests/check_web.py
"""
import base64
import statistics as stats
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dreamdesk.core import DeskEnv, changed_elements
from dreamdesk.spike_cdp import PAGE
from dreamdesk.web_backend import WebBackend


class CountTask:
    description = "get to 2 items"

    def is_done(self, elements):
        return any(e.role == "label" and e.text == "2 items" for e in elements)


url = "data:text/html;base64," + base64.b64encode(PAGE.encode()).decode()
backend = WebBackend(url)
env = DeskEnv(backend, max_steps=15, change_timeout=0.15, settle=0.01)
failed = []


def check(ok, message):
    print(f"{'pass' if ok else 'FAIL'}: {message}", flush=True)
    if not ok:
        failed.append(message)


task = CountTask()
first = env.reset(task)
roles = {e.role for e in first}
print("roles:", sorted(roles))
check("button" in roles and "text" in roles and "label" in roles, "web roles map to the shared names")
check(not any(e.role in ("InlineTextBox", "StaticText", "textbox") for e in first), "no raw DevTools roles leak through")
names = [e.name for e in env.pressable()]
check(names == ["Add"], f"the only pressable element is Add ({names})")

_, reward, done, info = env.step(names.index("Add"))
check(info["changed"] > 0 and reward == 0 and not done, "pressing Add changes the page, and isn't success yet")
names = [e.name for e in env.pressable()]
check("Delete 1" in names, f"the new Delete button can be pressed ({names})")
_, reward, done, _ = env.step(names.index("Add"))
check(reward == 1.0 and done, "the second Add completes the task, checked from the page's real text")

times = []
for _ in range(5):
    t0 = time.perf_counter()
    again = env.reset(task)
    times.append((time.perf_counter() - t0) * 1000)
    check(not changed_elements(first, again), "reset gives an identical start state")

steps, no_ops = [], []
for _ in range(10):
    env.reset(task)
    env.max_steps = 100
    for _ in range(10):
        names = [e.name for e in env.pressable()]
        t0 = time.perf_counter()
        env.task = type("Never", (), {"is_done": lambda self, e: False})()
        env.step(names.index("Add"))
        steps.append((time.perf_counter() - t0) * 1000)
print(f"step with settling: median {stats.median(steps):.1f} ms, p90 {sorted(steps)[int(0.9 * len(steps))]:.1f}, n={len(steps)}; about {1000 / stats.median(steps):.0f} steps/s")
print(f"reset: median {stats.median(times):.1f} ms, n={len(times)}")
backend.close()
print("VERDICT:", "FAIL" if failed else "PASS")
sys.exit(1 if failed else 0)
