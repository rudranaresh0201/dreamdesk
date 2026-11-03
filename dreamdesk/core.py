"""The shared layer: everything above a Backend works on any app and any OS.

    Agent / world model
           |  list of Elements, "press this element"
         DeskEnv + Task
           |
        Backend  <- one per platform: Linux AT-SPI today; Windows UI Automation and Chrome later
"""
import time
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class Element:
    """One thing on screen, in a form that's the same on every platform."""

    path: str  # position in the tree, e.g. "0.3.1"
    role: str  # "button", "label", "text", ...
    name: str
    text: str
    pressable: bool
    handle: Any = None  # the platform's own object; never shown to the agent
    states: frozenset = frozenset()  # e.g. {"focused", "checked", "expanded", "editable"}
    box: tuple = ()  # (x, y, width, height) in the window, for drawing; empty if unknown

    @property
    def editable(self):
        return "editable" in self.states

    def key(self):
        """What counts as a change. The box is left out: layout jitter isn't a change of state."""
        return (self.path, self.role, self.name, self.text, self.pressable, tuple(sorted(self.states)))


@dataclass(frozen=True)
class Action:
    """One thing the agent can do: press or focus an element, or type a word into it."""

    element: Element
    verb: str  # "press", "focus" or "type"
    text: str = ""

    def describe(self):
        return f"{self.verb} {self.element.role} {self.element.name!r}" + (f" {self.text!r}" if self.text else "")


class Backend(Protocol):
    def start(self) -> None: ...  # open the app in a clean state
    def stop(self) -> None: ...
    def read(self) -> list[Element]: ...  # empty list means the app is gone
    def press(self, element: Element) -> None: ...
    def focus(self, element: Element) -> None: ...
    def type_text(self, element: Element, text: str) -> None: ...
    # Optional: can_type(element) -> bool, when an element says it's editable but refuses text.


class Task(Protocol):
    description: str

    def is_done(self, elements: list[Element]) -> bool: ...


def changed_elements(before, after):
    """Elements that appeared, vanished or changed: what the world model will predict."""
    a, b = {e.key() for e in before}, {e.key() for e in after}
    return len(a ^ b)


class DeskEnv:
    """A Gym-style environment.

    step(i) presses pressable()[i], as in the first calculator experiments.
    act(action) takes any Action from actions(): press, focus, or type a word from `words`.
    """

    def __init__(self, backend, max_steps=15, change_timeout=0.6, settle=0.1, quiet=0.25, max_wait=3.0,
                 blocked_names=(), words=()):
        self.backend = backend
        self.blocked_names = set(blocked_names)
        self.max_steps = max_steps
        self.change_timeout = change_timeout
        self.settle = settle
        self.quiet = quiet
        self.max_wait = max_wait
        self.words = tuple(words)
        self.task = None
        self.elements = []
        self.steps = 0

    def pressable(self):
        return [e for e in self.elements if e.pressable and e.name not in self.blocked_names]

    def actions(self):
        """Every allowed action now, in a fixed order: presses first, then focus and typing on text fields."""
        allowed = [e for e in self.elements if e.name not in self.blocked_names]
        out = [Action(e, "press") for e in allowed if e.pressable]
        can_type = getattr(self.backend, "can_type", lambda e: True)
        for e in allowed:
            if e.editable:
                out.append(Action(e, "focus"))
                if can_type(e):
                    out.extend(Action(e, "type", w) for w in self.words)
        return out

    def reset(self, task):
        """Relaunch the app, because that's the only way to get an exactly clean state."""
        self.backend.stop()
        self.backend.start()
        self.task = task
        self.steps = 0
        self.elements = self.backend.read()
        return self.elements

    def _wait_for_change(self, before):
        """Return once the tree has changed and then stayed the same for `quiet` seconds.

        Waiting for a quiet spell, not just two equal reads, catches updates that arrive in parts,
        such as a result shown slightly after the sum. No change within change_timeout means no change.
        """
        start = time.perf_counter()
        current = before
        while time.perf_counter() - start < self.change_timeout:
            current = self.backend.read()
            if not current or changed_elements(before, current):
                break
        else:
            return current, False
        last_change = time.perf_counter()
        while current and time.perf_counter() - last_change < self.quiet and time.perf_counter() - start < self.max_wait:
            time.sleep(self.settle)
            next_read = self.backend.read()
            if changed_elements(current, next_read):
                last_change = time.perf_counter()
            current = next_read
        return current, True

    def step(self, action):
        """Press pressable()[action]."""
        return self.act(Action(self.pressable()[action], "press"))

    def act(self, action):
        before = self.elements
        self.steps += 1
        if action.verb == "press":
            self.backend.press(action.element)
        elif action.verb == "focus":
            self.backend.focus(action.element)
        elif action.verb == "type":
            self.backend.type_text(action.element, action.text)
        else:
            raise ValueError(f"unknown verb {action.verb!r}")
        self.elements, _ = self._wait_for_change(before)

        crashed = not self.elements
        success = not crashed and self.task.is_done(self.elements)
        done = crashed or success or self.steps >= self.max_steps
        info = {"pressed": action.element.name, "action": action.describe(),
                "changed": changed_elements(before, self.elements), "app_closed": crashed}
        return self.elements, 1.0 if success else 0.0, done, info
