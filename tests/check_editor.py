"""Checks recorder v2 on the real text editor: states, boxes, focus and typing. Run inside the sandbox:

  scripts/sandbox.sh python3 tests/check_editor.py
"""
import statistics as stats
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dreamdesk.atspi_backend import AtspiBackend
from dreamdesk.core import DeskEnv

failed = []


def check(ok, message):
    print(f"{'pass' if ok else 'FAIL'}: {message}", flush=True)
    if not ok:
        failed.append(message)


class Contains:
    description = "the document contains 'hello world'"

    def is_done(self, elements):
        return any(e.editable and "hello world" in e.text for e in elements)


backend = AtspiBackend(["gnome-text-editor", "--standalone"], "text-editor", min_elements=20, start_timeout=30)
env = DeskEnv(backend, max_steps=10, blocked_names={"Close", "Minimize", "Maximize", "Main Menu"}, words=("hello", " world"))
task = Contains()
t0 = time.perf_counter()
elements = env.reset(task)
time.sleep(1)
elements = env.elements = backend.read()
print(f"reset {1000 * (time.perf_counter() - t0):.0f} ms, {len(elements)} elements")

editable = [e for e in elements if e.editable]
check(len(editable) >= 1, f"an editable text field is found ({[(e.role, e.name) for e in editable][:3]})")
check(any(e.states for e in elements), "elements carry states")
check(sum(bool(e.box) and e.box[2] > 0 for e in elements) > len(elements) // 2, "most elements have a box with a width")
verbs = {a.verb for a in env.actions()}
check(verbs == {"press", "focus", "type"}, f"actions offer press, focus and type ({sorted(verbs)})")

document = next((e for e in editable if e.role in ("text", "paragraph", "entry")), editable[0] if editable else None)
if document:
    focus = next(a for a in env.actions() if a.verb == "focus" and a.element.path == document.path)
    _, _, _, info = env.act(focus)
    now = next((e for e in env.elements if e.path == document.path), None)
    check(now is not None and "focused" in now.states, f"focusing sets the focused state ({sorted(now.states) if now else None})")

    reward = 0
    for word in ("hello", " world"):
        action = next(a for a in env.actions() if a.verb == "type" and a.text == word and a.element.path == document.path)
        _, reward, done, info = env.act(action)
        check(info["changed"] > 0, f"typing {word!r} changes the screen ({info['action']})")
    check(reward == 1.0, "the document now holds 'hello world', checked from the real app")

reads = []
for _ in range(5):
    t0 = time.perf_counter()
    backend.read()
    reads.append((time.perf_counter() - t0) * 1000)
backend.detail = False
plain = []
for _ in range(5):
    t0 = time.perf_counter()
    backend.read()
    plain.append((time.perf_counter() - t0) * 1000)
print(f"read with states and boxes: median {stats.median(reads):.0f} ms; without: {stats.median(plain):.0f} ms")
backend.stop()
print("VERDICT:", "FAIL" if failed else "PASS")
sys.exit(1 if failed else 0)
