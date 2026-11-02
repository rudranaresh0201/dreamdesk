"""The first app: tasks, success checks and a scripted expert for GNOME Calculator."""
from .atspi_backend import AtspiBackend

OPS = {"+": ("+", lambda a, b: a + b), "*": ("×", lambda a, b: a * b), "-": ("−", lambda a, b: a - b)}

# The agent can't press these. Window controls end or hide the app, and the menu can open other programs.
BLOCKED = {"Close", "Minimize", "Maximize", "Main Menu", "Basic"}


def is_test_task(a, op, b):
    """A fixed split: about 1 in 5 sums never appears in training data.

    a*100 is divisible by 5, so only op and b's last digit decide: + holds out b ending 2 or 7,
    * ending 3 or 8, - ending 0 or 5. That tests unseen op and last-digit pairs, not random sums.
    """
    return (a * 100 + b + ord(op)) % 5 == 0


def make_backend():
    return AtspiBackend(["gnome-calculator"], "calculator")


class ComputeTask:
    """Compute `a op b`. Done only if the real app shows the sum AND the result.

    Checking the sum too means that typing the answer directly doesn't count.
    """

    def __init__(self, a, op, b):
        self.a, self.op, self.b = a, op, b
        symbol, fn = OPS[op]
        self.symbol = symbol
        result = fn(a, b)
        self.result = str(result).replace("-", "−")
        self.expression = f"{a}{symbol}{b}"
        self.description = f"compute {a} {op} {b}"

    def is_done(self, elements):
        shows_result = any(e.role == "text" and e.text == self.result for e in elements)
        shows_sum = any(e.role == "label" and e.text == self.expression for e in elements)
        return shows_result and shows_sum

    def expert_presses(self):
        return list(str(self.a)) + [self.symbol] + list(str(self.b)) + ["="]
