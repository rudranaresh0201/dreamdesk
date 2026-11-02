"""Checks the policy's plumbing. Needs no display.

Run:  .venv/bin/python tests/check_policy.py
"""
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dreamdesk.calculator import BLOCKED, is_test_task
from dreamdesk.evaluate import fixed_tasks
from dreamdesk.policy import PointerPolicy, build_vocab, choose_action, collate, encode

ROWS = [
    ["0", "application", "calculator", "", False],
    ["0.0", "panel", "", "", False],  # dropped: nothing to read or press
    ["0.1", "text", "", "12+", False],
    ["0.2", "button", "7", "", True],
    ["0.3", "button", "Close", "", True],  # blocked
    ["0.4", "button", "=", "", True],
]
LONGER = ROWS + [[f"0.{i}", "label", f"filler{i}", "x", False] for i in range(5, 40)]

chars = build_vocab("12+37=calculatorClosefiller0456789x")
roles = build_vocab(["application", "panel", "text", "button", "label"])
torch.manual_seed(0)
model = PointerPolicy(len(chars), len(roles)).eval()

# Option indices must follow the same order and rules as DeskEnv.pressable().
sample = encode("12+37", ROWS, BLOCKED, chars, roles)
assert len(sample["role"]) == 5, "the empty panel should be dropped"
assert sample["options"].tolist() == [2, 4], "the options should be '7' and '=', never 'Close'"

with torch.no_grad():
    # A blocked element can never win.
    scores = model(collate([sample]))[0]
    assert torch.isinf(scores[3]) and scores[3] < 0, "Close must be impossible to choose"
    assert choose_action(model, "12+37", ROWS, BLOCKED, chars, roles) in (0, 1)

    # Padding must not change the answer: a short tree scores the same alone or beside a long one.
    alone = model(collate([sample]))[0]
    together = model(collate([sample, encode("12+37", LONGER, BLOCKED, chars, roles)]))[0][: len(alone)]
    allowed = sample["options"]
    assert torch.allclose(alone[allowed], together[allowed], atol=1e-5), "padding changed the scores"

    # The goal and the screen must both affect the choice, or the policy can't follow a task.
    a = model(collate([sample]))[0][allowed]
    assert not torch.allclose(a, model(collate([encode("98-1", ROWS, BLOCKED, chars, roles)]))[0][allowed]), "the goal is ignored"
    other_screen = [r[:3] + (["999"] if r[1] == "text" else [r[3]]) + r[4:] for r in ROWS]
    assert not torch.allclose(a, model(collate([encode("12+37", other_screen, BLOCKED, chars, roles)]))[0][allowed]), "the screen is ignored"

# Evaluation lists must be repeatable and from the correct side of the split.
first, again = fixed_tasks("test", 100, 12345), fixed_tasks("test", 100, 12345)
assert [t.description for t in first] == [t.description for t in again], "the task list changed between runs"
assert len({t.description for t in first}) == 100
assert all(is_test_task(t.a, t.op, t.b) for t in first), "a train task is in the held-out list"
assert not any(is_test_task(t.a, t.op, t.b) for t in fixed_tasks("train", 50, 54321)), "a held-out task is in the train list"

print("all policy checks passed")
