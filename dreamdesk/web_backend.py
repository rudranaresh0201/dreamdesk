"""Web backend: real web apps in headless Chrome, read through its DevTools accessibility tree.

Same Element format as the desktop backend, so everything above a Backend works on both.
Run it only inside scripts/sandbox.sh, which has no network and no access to your files.
"""
import fcntl
import json
import os
import shutil
import subprocess
import tempfile

from .core import Element

# DevTools role -> the AT-SPI role name the desktop backend reports.
ROLES = {
    "RootWebArea": "document web",
    "StaticText": "label",
    "LabelText": "label",
    "textbox": "text",
    "searchbox": "text",
    "checkbox": "check box",
    "radio": "radio button",
    "combobox": "combo box",
    "listitem": "list item",
    "menuitem": "menu item",
    "tab": "page tab",
    "generic": "panel",
    "paragraph": "paragraph",
}
PRESSABLE = {"button", "link", "checkbox", "radio", "menuitem", "tab", "switch", "combobox", "treeitem"}
SKIP = {"InlineTextBox", "ListMarker", "none", "presentation"}


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


def _value(node, key):
    return str((node.get(key) or {}).get("value", ""))


WEB_STATES = {"focused", "focusable", "checked", "pressed", "expanded", "selected", "editable", "disabled", "modal", "multiline"}


def _states(node):
    """DevTools properties -> state names like the desktop backend's."""
    out = set()
    for prop in node.get("properties", []):
        name, value = prop.get("name"), (prop.get("value") or {}).get("value")
        if name in WEB_STATES and value not in (False, "false", None, ""):
            out.add({"multiline": "multi_line"}.get(name, name))
    if "disabled" not in out:
        out.add("enabled")
    out.discard("disabled")
    return frozenset(out)


def to_elements(nodes):
    """Turn a DevTools tree into Elements, in document order. Ignored nodes are skipped but walked through."""
    by_id = {n["nodeId"]: n for n in nodes}
    child_ids = {c for n in nodes for c in n.get("childIds", [])}
    roots = [n for n in nodes if n["nodeId"] not in child_ids]
    out = []

    def walk(node, path):
        role = _value(node, "role")
        visible = not node.get("ignored") and role not in SKIP
        if visible:
            name = _value(node, "name")
            text = _value(node, "value") or (name if role in ("StaticText", "LabelText") else "")
            # Web boxes need a call per element; left empty until the playable dream needs them.
            out.append(Element(path, ROLES.get(role, role), name, text, role in PRESSABLE, node, _states(node)))
        index = 0
        for child in node.get("childIds", []):
            if child in by_id:
                walk(by_id[child], f"{path}.{index}" if visible else f"{path}.i{index}")
                index += 1

    for i, root in enumerate(roots):
        walk(root, str(i))
    return out


# Pages settle in milliseconds, so wait for a much shorter quiet spell than desktop apps need.
ENV_TIMING = {"change_timeout": 0.15, "settle": 0.01, "quiet": 0.04}


class WebBackend:
    """Reset reloads the page, so Chrome stays open between episodes. Call close() at the end.
    Use DeskEnv(backend, **ENV_TIMING)."""

    def __init__(self, url):
        self.url = url
        self.chrome = None

    def start(self):
        if self.chrome is None:
            self.chrome = Chrome()
            self.chrome.open_page(self.url)
        else:
            self.chrome.call("Page.navigate", url=self.url)
        for _ in range(2000):
            if any(e.pressable for e in self.read()):
                return
        raise RuntimeError(f"{self.url} never showed anything to press")

    def stop(self):
        pass

    def close(self):
        if self.chrome:
            self.chrome.close()
            self.chrome = None

    def read(self):
        return to_elements(self.chrome.tree())

    def press(self, element):
        self.chrome.press(element.handle)

    def focus(self, element):
        self.chrome.call("DOM.focus", backendNodeId=element.handle["backendDOMNodeId"])

    def type_text(self, element, text):
        """Focus the field, put the caret at the end, and type, so pages see real input events."""
        self.focus(element)
        obj = self.chrome.call("DOM.resolveNode", backendNodeId=element.handle["backendDOMNodeId"])["object"]["objectId"]
        self.chrome.call("Runtime.callFunctionOn", objectId=obj,
                         functionDeclaration="function(){if(this.setSelectionRange){const n=this.value.length;this.setSelectionRange(n,n)}}")
        self.chrome.call("Input.insertText", text=text)
