"""Speed spike: headless Chrome through its DevTools accessibility tree, instead of AT-SPI.

Measures a real page: read the whole tree, press a button, read until it changes. No network, no
extra libraries. Talks to Chrome over a pipe.
  scripts/sandbox.sh python3 -m dreamdesk.spike_cdp
"""
import base64
import json
import statistics as stats
import sys
import time

from .web_backend import Chrome

PAGE = """<!doctype html><title>Todo</title><h1>Todo</h1>
<label>New item <input id=box></label><button id=add>Add</button><ul id=list></ul><p id=count>0 items</p>
<script>
let n=0;
add.onclick=()=>{n++;const li=document.createElement('li');li.textContent='Item '+n;
const del=document.createElement('button');del.textContent='Delete '+n;
del.onclick=()=>{li.remove();n--;count.textContent=n+' items'};li.append(del);list.append(li);count.textContent=n+' items'};
</script>"""


def name_of(node):
    return (node.get("name") or {}).get("value", "")


def role_of(node):
    return (node.get("role") or {}).get("value", "")


def fingerprint(nodes):
    return {(role_of(n), name_of(n)) for n in nodes if not n.get("ignored")}


def main():
    url = "data:text/html;base64," + base64.b64encode(PAGE.encode()).decode()
    t0 = time.perf_counter()
    chrome = Chrome()
    chrome.open_page(url)
    time.sleep(0.3)
    startup_ms = (time.perf_counter() - t0) * 1000
    read_ms, step_ms, reset_ms, sizes, misses = [], [], [], [], 0
    for episode in range(10):
        t0 = time.perf_counter()
        chrome.call("Page.navigate", url=url)
        while not any(role_of(n) == "button" and name_of(n) == "Add" for n in chrome.tree()):
            time.sleep(0.005)
        reset_ms.append((time.perf_counter() - t0) * 1000)
        for step in range(20):
            t0 = time.perf_counter()
            nodes = chrome.tree()
            read_ms.append((time.perf_counter() - t0) * 1000)
            sizes.append(len(nodes))
            before = fingerprint(nodes)
            add = next(n for n in nodes if role_of(n) == "button" and name_of(n) == "Add")
            chrome.press(add)
            for _ in range(200):
                if fingerprint(chrome.tree()) != before:
                    break
            else:
                misses += 1
            step_ms.append((time.perf_counter() - t0) * 1000 + read_ms[-1])
    final = chrome.tree()
    roles = sorted({role_of(n) for n in final if not n.get("ignored")})
    chrome.close()
    n = len(step_ms)
    print(json.dumps({
        "startup_ms": round(startup_ms),
        "steps": n,
        "changes_missed": misses,
        "step_ms_median": round(stats.median(step_ms), 1),
        "step_ms_p90": round(sorted(step_ms)[int(0.9 * n)], 1),
        "steps_per_second_one_env": round(1000 / stats.median(step_ms), 1),
        "read_ms_median": round(stats.median(read_ms), 2),
        "reset_ms_median": round(stats.median(reset_ms), 1),
        "nodes_min_max": [min(sizes), max(sizes)],
        "roles": roles,
    }))


if __name__ == "__main__":
    sys.exit(main())
