"""Tests a player in the real calculator on a fixed list of tasks. Writes one JSON line per episode.

Run on a private desktop:
  scripts/private.sh 93 .venv/bin/python -m dreamdesk.evaluate --checkpoint runs/arm_a/seed0.pt \
      --split test --tasks 100 --task-seed 12345 --out runs/arm_a/seed0_test.jsonl
Leave out --checkpoint to play randomly.
"""
import argparse
import json
import random
import time

import torch

from .calculator import BLOCKED, make_backend
from .collect import MAX_STEPS, sample_task, snapshot
from .core import DeskEnv
from .policy import choose_action, load_checkpoint


def fixed_tasks(split, count, seed):
    """The same list every time, with no repeated sums."""
    rng = random.Random(seed)
    tasks = {}
    while len(tasks) < count:
        task = sample_task(rng, split == "test")
        tasks.setdefault(task.description, task)
    return list(tasks.values())


def play(env, task, pick):
    rows = snapshot(env.reset(task))
    plan = task.expert_presses()
    pressed, first_wrong = [], None
    done, reward, closed = False, 0.0, False
    while not done:
        index = pick(task, rows)
        name = env.pressable()[index].name
        k = len(pressed)
        if first_wrong is None and (k >= len(plan) or name != plan[k]):
            first_wrong = {"step": k, "pressed": name, "expected": plan[k] if k < len(plan) else None}
        pressed.append(name)
        elements, reward, done, info = env.step(index)
        rows = snapshot(elements)
        closed = info["app_closed"]
    display = next((r[3] for r in rows if r[1] == "text"), "")
    return {"task": task.description, "op": task.op, "goal": task.expression, "success": reward == 1.0, "steps": len(pressed),
            "pressed": pressed, "first_wrong": first_wrong, "display": display, "app_closed": closed}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint")
    parser.add_argument("--split", choices=["train", "test"], required=True)
    parser.add_argument("--tasks", type=int, required=True)
    parser.add_argument("--task-seed", type=int, required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--random-seed", type=int, default=0)
    args = parser.parse_args()

    torch.set_num_threads(1)
    if args.checkpoint:
        model, chars, roles = load_checkpoint(args.checkpoint)
        pick = lambda task, rows: choose_action(model, task.expression, rows, BLOCKED, chars, roles)
    else:
        rng = random.Random(args.random_seed)
        pick = lambda task, rows: rng.randrange(len(env.pressable()))

    env = DeskEnv(make_backend(), max_steps=MAX_STEPS, blocked_names=BLOCKED)
    tasks = fixed_tasks(args.split, args.tasks, args.task_seed)
    start = time.perf_counter()
    wins, errors = 0, 0
    with open(args.out, "x", encoding="utf-8") as f:  # never overwrite a result
        for n, task in enumerate(tasks):
            record = None
            for attempt in range(2):
                try:
                    record = play(env, task, pick)
                    break
                except Exception as err:
                    errors += 1
                    print(f"{task.description}: attempt {attempt + 1} failed: {err}", flush=True)
            if record is None:  # pre-registered: still failing after a retry counts as a failure
                record = {"task": task.description, "op": task.op, "goal": task.expression, "success": False, "steps": 0,
                          "pressed": [], "first_wrong": None, "display": "", "app_closed": False, "errored": True}
            wins += record["success"]
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            if (n + 1) % 25 == 0:
                print(f"{n + 1}/{len(tasks)}: {wins} succeeded, {time.perf_counter() - start:.0f} s", flush=True)
    env.backend.stop()
    print(f"finished: {wins}/{len(tasks)} succeeded, {errors} errors, {time.perf_counter() - start:.0f} s", flush=True)


if __name__ == "__main__":
    main()
