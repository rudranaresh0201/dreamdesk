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

    def key(self):
        return (self.path, self.role, self.name, self.text, self.pressable)


class Backend(Protocol):
    def start(self) -> None: ...  # open the app in a clean state
    def stop(self) -> None: ...
    def read(self) -> list[Element]: ...  # empty list means the app is gone
    def press(self, element: Element) -> None: ...


class Task(Protocol):
    description: str

    def is_done(self, elements: list[Element]) -> bool: ...


def changed_elements(before, after):
    """Elements that appeared, vanished or changed: what the world model will predict."""
    a, b = {e.key() for e in before}, {e.key() for e in after}
    return len(a ^ b)


class DeskEnv:
    """A Gym-style environment. An action is an index into the pressable elements."""

    def __init__(self, backend, max_steps=15, change_timeout=0.6, settle=0.1, blocked_names=()):
        self.backend = backend
        self.blocked_names = set(blocked_names)
        self.max_steps = max_steps
        self.change_timeout = change_timeout
        self.settle = settle
        self.task = None
        self.elements = []
        self.steps = 0

    def pressable(self):
        return [e for e in self.elements if e.pressable and e.name not in self.blocked_names]

    def reset(self, task):
        """Relaunch the app, because that's the only way to get an exactly clean state."""
        self.backend.stop()
        self.backend.start()
        self.task = task
        self.steps = 0
        self.elements = self.backend.read()
        return self.elements

    def _wait_for_change(self, before):
        """Return as soon as the tree has changed and stopped changing, or after the timeout."""
        start = time.perf_counter()
        current = before
        while time.perf_counter() - start < self.change_timeout:
            current = self.backend.read()
            if not current or changed_elements(before, current):
                break
        else:
            return current, False
        # It changed. Keep reading until two reads in a row match.
        while current:
            time.sleep(self.settle)
            next_read = self.backend.read()
            if not changed_elements(current, next_read):
                break
            current = next_read
        return current, True

    def step(self, action):
        target = self.pressable()[action]
        before = self.elements
        self.steps += 1
        self.backend.press(target)
        self.elements, _ = self._wait_for_change(before)

        crashed = not self.elements
        success = not crashed and self.task.is_done(self.elements)
        done = crashed or success or self.steps >= self.max_steps
        info = {"pressed": target.name, "changed": changed_elements(before, self.elements), "app_closed": crashed}
        return self.elements, 1.0 if success else 0.0, done, info
