"""The apps agents may use, all inside scripts/sandbox.sh. Terminals, Disks, Update Manager, keyring,
online accounts, email and Discord are never added here.

Blocked names stop actions that end the episode for reasons that teach nothing: closing or hiding
the window, quitting, or killing processes.
"""
from dataclasses import dataclass, field

from .atspi_backend import AtspiBackend

WINDOW = {"Close", "Minimize", "Maximize", "Quit", "Close Window", "Toggle Fullscreen"}


@dataclass(frozen=True)
class AppSpec:
    name: str
    command: tuple
    a11y_name: str  # as the app names itself on the accessibility bus
    blocked: frozenset = field(default_factory=frozenset)
    words: tuple = ("hello", "42", "test")  # what the agent may type into a text field
    min_elements: int = 20
    start_timeout: int = 30
    noisy: bool = False  # changes on its own while idle (the noisy-TV check)

    def backend(self):
        return AtspiBackend(list(self.command), self.a11y_name, min_elements=self.min_elements, start_timeout=self.start_timeout)

    def blocked_names(self):
        return WINDOW | self.blocked


def _spec(name, command, a11y_name, blocked=(), **kw):
    return AppSpec(name, tuple(command), a11y_name, frozenset(blocked), **kw)


APPS = {s.name: s for s in [
    _spec("calculator", ["gnome-calculator"], "calculator"),
    _spec("text-editor", ["gnome-text-editor", "--standalone"], "text-editor"),
    _spec("files", ["nautilus", "--new-window"], "nautilus"),
    _spec("characters", ["gnome-characters"], "characters"),
    _spec("clocks", ["gnome-clocks"], "clocks"),
    _spec("disk-usage", ["baobab"], "baobab", min_elements=10),
    _spec("font-viewer", ["gnome-font-viewer"], "font-viewer"),
    _spec("image-viewer", ["loupe"], "loupe", min_elements=10),
    _spec("logs", ["gnome-logs"], "logs"),
    _spec("resources", ["resources"], "resources", blocked={"End App", "Kill App", "Halt App", "Stop App"}, noisy=True),
]}
