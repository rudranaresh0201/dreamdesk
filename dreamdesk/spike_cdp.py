"""Speed spike: headless Chrome through its DevTools accessibility tree, instead of AT-SPI.

Measures a real page: read the whole tree, press a button, read until it changes. No network, no
extra libraries. Talks to Chrome over a pipe.
  scripts/sandbox.sh python3 -m dreamdesk.spike_cdp
"""
import base64
import fcntl
import json
import os
import shutil
import statistics as stats
import subprocess
import sys
import tempfile
import time

PAGE = """<!doctype html><title>Todo</title><h1>Todo</h1>
<label>New item <input id=box></label><button id=add>Add</button><ul id=list></ul><p id=count>0 items</p>
<script>
let n=0;
add.onclick=()=>{n++;const li=document.createElement('li');li.textContent='Item '+n;
const del=document.createElement('button');del.textContent='Delete '+n;
del.onclick=()=>{li.remove();n--;count.textContent=n+' items'};li.append(del);list.append(li);count.textContent=n+' items'};
</script>"""


class Chrome:
    def __init__(self):
        self.profile = tempfile.mkdtemp(prefix="chrome-")
        to_chrome_r, self.to_chrome = os.pipe()
        self.from_chrome, from_chrome_w = os.pipe()
        # Move Chrome's ends above fd 4, so dup2 onto 3 and 4 below can't collide with them.
        moved = [fcntl.fcntl(fd, fcntl.F_DUPFD_CLOEXEC, 10) for fd in (to_chrome_r, from_chrome_w)]
        os.close(to_chrome_r)
        os.close(from_chrome_w)
        to_chrome_r, from_chrome_w = moved
        command = [shutil.which("google-chrome"), "--headless=new", "--no-sandbox", "--no-first-run", "--password-store=basic",
                   "--disable-gpu", "--disable-extensions", "--remote-debugging-pipe", f"--user-data-dir={self.profile}", "about:blank"]

        def wire_pipes():  # DevTools pipe mode reads fd 3 and writes fd 4
            os.dup2(to_chrome_r, 3)
            os.dup2(from_chrome_w, 4)

        self.proc = subprocess.Popen(command, preexec_fn=wire_pipes, close_fds=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.close(to_chrome_r)
        os.close(from_chrome_w)
        self.next_id, self.buffer = 0, b""
        self.session = None

    def call(self, method, **params):
        self.next_id += 1
        message = {"id": self.next_id, "method": method, "params": params}
        if self.session:
            message["sessionId"] = self.session
        os.write(self.to_chrome, json.dumps(message).encode() + b"\0")
        while True:
            while b"\0" not in self.buffer:
                data = os.read(self.from_chrome, 1 << 20)
                if not data:
                    raise RuntimeError("Chrome closed the pipe")
                self.buffer += data
            raw, self.buffer = self.buffer.split(b"\0", 1)
            reply = json.loads(raw)
            if reply.get("id") == self.next_id:
                if "error" in reply:
                    raise RuntimeError(f"{method}: {reply['error']}")
                return reply["result"]

    def open_page(self, url):
        target = self.call("Target.createTarget", url=url)["targetId"]
        self.session = self.call("Target.attachToTarget", targetId=target, flatten=True)["sessionId"]
        self.call("Accessibility.enable")
        self.call("DOM.enable")

    def tree(self):
        return self.call("Accessibility.getFullAXTree")["nodes"]

    def press(self, node):
        obj = self.call("DOM.resolveNode", backendNodeId=node["backendDOMNodeId"])["object"]["objectId"]
        self.call("Runtime.callFunctionOn", objectId=obj, functionDeclaration="function(){this.click()}")

    def close(self):
        self.proc.kill()
        self.proc.wait()
        shutil.rmtree(self.profile, ignore_errors=True)


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
