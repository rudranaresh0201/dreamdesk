"""Measures one app: does it start in the sandbox, how big is its tree, how fast can we read it?

Only reads the tree. It presses nothing.
  scripts/sandbox.sh --out data/survey python3 -m dreamdesk.survey_apps NAME OUT_FILE COMMAND...
"""
import json
import statistics as stats
import subprocess
import sys
import time

from .atspi_backend import AtspiBackend, Atspi


def biggest_app(backend, ignore):
    """Pick the accessible app with the most elements. This script also shows up as a tiny app."""
    desktop = Atspi.get_desktop(0)
    best, best_elements = None, []
    for i in range(desktop.get_child_count()):
        child = desktop.get_child_at_index(i)
        if child and (child.get_name() or "") not in ignore:
            backend.app = child
            elements = backend.read()
            if len(elements) > len(best_elements):
                best, best_elements = child, elements
    backend.app = best
    return best_elements


def main():
    name, out_file, command = sys.argv[1], sys.argv[2], sys.argv[3:]
    result = {"app": name, "command": command, "started": False}
    backend = AtspiBackend(command, name)
    ignore = {"at-spi-bus-launcher", "at-spi2-registryd"}
    try:
        started_at = time.perf_counter()
        backend.proc = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elements = []
        while time.perf_counter() - started_at < 40:
            elements = biggest_app(backend, ignore)
            if len(elements) >= 10:
                break
            time.sleep(0.2)
        result["seconds_to_tree"] = round(time.perf_counter() - started_at, 2)
        if len(elements) >= 10:
            time.sleep(3)  # let the first screen finish loading
            times, sizes = [], []
            for _ in range(5):
                t0 = time.perf_counter()
                elements = backend.read()
                times.append((time.perf_counter() - t0) * 1000)
                sizes.append(len(elements))
            idle_a = {e.key() for e in elements}
            time.sleep(5)
            idle_b = {e.key() for e in backend.read()}
            result.update(
                started=True,
                a11y_name=backend.app.get_name(),
                nodes=sizes[-1],
                read_ms_median=round(stats.median(times), 1),
                pressable=sum(e.pressable for e in elements),
                named_pressable=sum(e.pressable and bool(e.name) for e in elements),
                editable_text=sum(e.role in ("text", "entry", "password text", "paragraph") for e in elements),
                roles=sorted({e.role for e in elements}),
                idle_changed_in_5s=len(idle_a ^ idle_b),
                sample_buttons=[e.name for e in elements if e.pressable and e.name][:12],
            )
    finally:
        if backend.proc and backend.proc.poll() is None:
            backend.proc.kill()
        result["exit_code_after_kill"] = backend.proc.wait() if backend.proc else None
        with open(out_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
        print(json.dumps({k: result.get(k) for k in ("app", "started", "nodes", "read_ms_median", "pressable", "named_pressable", "idle_changed_in_5s")}), flush=True)


if __name__ == "__main__":
    main()
