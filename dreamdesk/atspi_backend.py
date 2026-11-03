"""Linux backend: reads and presses real apps through AT-SPI, the Linux accessibility system."""
import subprocess
import time

import gi

gi.require_version("Atspi", "2.0")
from gi.repository import Atspi

from .core import Element

Atspi.init()


# States worth showing the agent. AT-SPI has many more; most never change.
STATES = {"focused", "focusable", "checked", "pressed", "expanded", "collapsed", "selected", "editable",
          "enabled", "sensitive", "visible", "showing", "active", "busy", "modal", "multi_line", "indeterminate"}


class AtspiBackend:
    """detail=True also reads states and boxes. That costs extra calls per element, so it can be switched off."""

    def __init__(self, command, app_name, min_elements=20, start_timeout=20, detail=True):
        self.command = command
        self.app_name = app_name.lower()
        self.min_elements = min_elements
        self.start_timeout = start_timeout
        self.detail = detail
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
            states, box = frozenset(), ()
            if self.detail:
                states = frozenset(s.value_nick for s in node.get_state_set().get_states()) & STATES
                component = node.get_component_iface()
                if component:
                    r = Atspi.Component.get_extents(component, Atspi.CoordType.WINDOW)
                    box = (r.x, r.y, r.width, r.height)
            out.append(Element(path, role, name, text, pressable, node, states, box))
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

    def focus(self, element):
        """Ask through accessibility first. GTK4 refuses for some widgets, so fall back to a real
        click in the middle of the element, on the private display only."""
        component = element.handle.get_component_iface()
        if not component:
            raise RuntimeError(f"{element.role} {element.name!r} can't take focus")
        try:
            if Atspi.Component.grab_focus(component):
                return
        except Exception:
            pass
        if self._is_focused(element):
            return
        r = Atspi.Component.get_extents(component, Atspi.CoordType.SCREEN)
        if r.width <= 0 or r.height <= 0:
            raise RuntimeError(f"{element.role} {element.name!r} has no box to click")
        subprocess.run(["xdotool", "mousemove", str(r.x + r.width // 2), str(r.y + r.height // 2), "click", "1"], check=True, timeout=5)

    @staticmethod
    def _is_focused(element):
        try:
            return any(s.value_nick == "focused" for s in element.handle.get_state_set().get_states())
        except Exception:
            return False

    def type_text(self, element, text):
        """Insert text at the caret, like typing. Focuses the field first."""
        editable = element.handle.get_editable_text_iface()
        if not editable:
            raise RuntimeError(f"{element.role} {element.name!r} doesn't accept text")
        if not self._is_focused(element):
            self.focus(element)
        text_iface = element.handle.get_text_iface()
        caret = Atspi.Text.get_caret_offset(text_iface) if text_iface else 0
        Atspi.EditableText.insert_text(editable, max(caret, 0), text, len(text.encode("utf-8")))
