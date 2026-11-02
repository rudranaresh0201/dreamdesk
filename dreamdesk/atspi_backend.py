"""Linux backend: reads and presses real apps through AT-SPI, the Linux accessibility system."""
import subprocess
import time

import gi

gi.require_version("Atspi", "2.0")
from gi.repository import Atspi

from .core import Element

Atspi.init()


class AtspiBackend:
    def __init__(self, command, app_name, min_elements=20, start_timeout=20):
        self.command = command
        self.app_name = app_name.lower()
        self.min_elements = min_elements
        self.start_timeout = start_timeout
        self.proc = None
        self.app = None

    def _find_app(self):
        desktop = Atspi.get_desktop(0)
        for i in range(desktop.get_child_count()):
            child = desktop.get_child_at_index(i)
            if child and self.app_name in (child.get_name() or "").lower():
                return child
        return None

    def start(self):
        self.proc = subprocess.Popen(self.command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        start = time.perf_counter()
        while time.perf_counter() - start < self.start_timeout:
            self.app = self._find_app()
            if self.app and len(self.read()) >= self.min_elements:
                return
            time.sleep(0.05)
        raise RuntimeError(f"{self.command} never appeared in the accessibility tree")

    def stop(self):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
            time.sleep(0.2)  # let it leave the accessibility tree
        self.proc, self.app = None, None

    def read(self):
        if not self.app or (self.proc and self.proc.poll() is not None):
            return []
        out = []
        self._walk(self.app, "0", out)
        return out

    def _walk(self, node, path, out):
        try:
            role = node.get_role_name()
            name = node.get_name() or ""
            text = ""
            text_iface = node.get_text_iface()
            if text_iface:
                length = min(Atspi.Text.get_character_count(text_iface), 200)
                text = Atspi.Text.get_text(text_iface, 0, length)
            pressable = False
            action_iface = node.get_action_iface()
            if action_iface:
                names = [Atspi.Action.get_action_name(action_iface, i) for i in range(Atspi.Action.get_n_actions(action_iface))]
                pressable = "click" in names
            out.append(Element(path, role, name, text, pressable, node))
            for i in range(node.get_child_count()):
                child = node.get_child_at_index(i)
                if child:
                    self._walk(child, f"{path}.{i}", out)
        except Exception:
            return  # a node can vanish mid-read; the next read sees the new tree

    def press(self, element):
        iface = element.handle.get_action_iface()
        for i in range(Atspi.Action.get_n_actions(iface)):
            if Atspi.Action.get_action_name(iface, i) == "click":
                Atspi.Action.do_action(iface, i)
                return
