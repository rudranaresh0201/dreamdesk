"""Speed probe: how fast can an agent step a real Linux app through its accessibility tree?

Run through spikes/run_probe.sh, which starts a private display and D-Bus session.
Your own desktop is not touched.
"""
import statistics as stats
import subprocess
import sys
import time

import gi

gi.require_version("Atspi", "2.0")
from gi.repository import Atspi

SETTLE_S = 0.45  # a press can take about 0.4 s to appear in the tree; 0.15 s missed every change
PRESSES = 40
RESETS = 5
APP = "gnome-calculator"


def find_app():
    desktop = Atspi.get_desktop(0)
    for i in range(desktop.get_child_count()):
        child = desktop.get_child_at_index(i)
        if child and "calculator" in (child.get_name() or "").lower():
            return child
    return None


def launch(timeout_s=20):
    proc = subprocess.Popen([APP], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    start = time.perf_counter()
    while time.perf_counter() - start < timeout_s:
        app = find_app()
        if app and app.get_child_count() > 0 and len(walk(app)) > 20:
            return proc, app, time.perf_counter() - start
        time.sleep(0.05)
    proc.kill()
    raise RuntimeError("the app never appeared in the accessibility tree")


def walk(node, path="0", out=None, nodes=None):
    """Return {path: (role, name, text)} for the tree, and optionally collect the node objects."""
    out = {} if out is None else out
    try:
        role = node.get_role_name()
        name = node.get_name() or ""
        text = ""
        iface = node.get_text_iface()
        if iface:
            text = Atspi.Text.get_text(iface, 0, min(Atspi.Text.get_character_count(iface), 200))
    except Exception:
        return out
    out[path] = (role, name, text)
    if nodes is not None:
        nodes.append((role, name, node))
    try:
        for i in range(node.get_child_count()):
            child = node.get_child_at_index(i)
            if child:
                walk(child, f"{path}.{i}", out, nodes)
    except Exception:
        pass
    return out


def button(app, label):
    nodes = []
    walk(app, nodes=nodes)
    for role, name, node in nodes:
        if "button" in role and name == label:
            return node
    available = sorted({n for r, n, _ in nodes if "button" in r and n})
    raise RuntimeError(f"no button {label!r}; buttons found: {available[:40]}")


def press(node):
    action = node.get_action_iface()
    Atspi.Action.do_action(action, 0)


def changed_nodes(before, after):
    return sum(1 for k in before.keys() | after.keys() if before.get(k) != after.get(k))


def rss_mb(pid):
    with open(f"/proc/{pid}/status") as f:
        for line in f:
            if line.startswith("VmRSS"):
                return int(line.split()[1]) / 1024
    return float("nan")


def spread(values):
    values = sorted(values)
    n = len(values)
    return f"median {stats.median(values):.1f}, p10 {values[n // 10]:.1f}, p90 {values[9 * n // 10]:.1f}, n={n}"


def main():
    Atspi.init()
    proc, app, launch_s = launch()
    print(f"nodes in tree: {len(walk(app))}, app memory: {rss_mb(proc.pid):.0f} MB")

    # How long after a press does the tree actually show a change?
    latency_ms, changed = [], []
    for i in range(12):
        node = button(app, ["7", "3", "1"][i % 3])
        before = walk(app)
        t0 = time.perf_counter()
        press(node)
        delay = None
        while time.perf_counter() - t0 < 2.0:
            now = walk(app)
            n = changed_nodes(before, now)
            if n:
                delay = (time.perf_counter() - t0) * 1000
                diff = [(k, before.get(k), now.get(k)) for k in before.keys() | now.keys() if before.get(k) != now.get(k)]
                changed.append(n)
                if i == 11:
                    print(f"example change: {diff[:3]}")
                break
        latency_ms.append(delay if delay is not None else float("inf"))
        time.sleep(0.5)
    print(f"ms until the tree shows a change: {[round(x) if x != float('inf') else None for x in latency_ms]}")
    print(f"changed nodes when a change was seen: {changed}")

    walk_ms, step_ms, deltas = [], [], []
    labels = ["7", "3", "1"]
    for i in range(PRESSES):
        node = button(app, labels[i % 3])
        t0 = time.perf_counter()
        before = walk(app)
        t1 = time.perf_counter()
        press(node)
        time.sleep(SETTLE_S)
        after = walk(app)
        t2 = time.perf_counter()
        if i > 0:  # discard the first step as warm-up
            walk_ms.append((t1 - t0) * 1000)
            step_ms.append((t2 - t1) * 1000)
            deltas.append(changed_nodes(before, after))
    print(f"tree read ms: {spread(walk_ms)}")
    print(f"step ms (act + {SETTLE_S}s settle + read): {spread(step_ms)}")
    print(f"changed nodes per press: {spread(deltas)}")
    print(f"sample display after presses: {[v[2] for v in walk(app).values() if v[2]][:3]}")
    proc.terminate()
    proc.wait(timeout=5)

    reset_ms = []
    for _ in range(RESETS):
        time.sleep(0.3)
        proc, _, seconds = launch()
        reset_ms.append(seconds * 1000)
        proc.terminate()
        proc.wait(timeout=5)
    print(f"reset ms (fresh app start): {spread(reset_ms)}")
    median_step = stats.median(step_ms) / 1000
    print(f"one env: about {1 / median_step:.1f} steps/s, about {3600 / median_step:,.0f} steps/hour")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"PROBE FAILED: {err}")
        sys.exit(1)
