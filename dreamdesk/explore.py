"""Task-free exploration of one app: press, focus and type with no goal, and record every transition.

Explorers:
  random   every allowed action equally likely
  novelty  in each screen, the action tried least often there, ties broken at random (count-based)

The recordings feed the world model, and dreamdesk/coverage.py scores how much each explorer found.
Run inside the sandbox:
  scripts/sandbox.sh --out data/explore python3 -m dreamdesk.explore --app clocks --explorer novelty \
      --steps 1000 --seed 0 --out data/explore
"""
import argparse
import gzip
import hashlib
import json
import random
import time
from collections import defaultdict
from pathlib import Path

from .apps import APPS
from .collect import snapshot
from .core import DeskEnv

EPISODE_STEPS = 30  # relaunch after this many steps, so the explorer keeps seeing the start too
FORMAT = 2

# States that mark a different screen. Focus and hover-like states are left out, since they change constantly.
SCREEN_STATES = {"checked", "pressed", "expanded", "selected", "modal"}


# Containers that mark a different screen by their kind alone; their names often hold typed text.
SCREEN_CONTAINERS = {"dialog", "alert", "menu", "popup menu", "file chooser", "page tab list", "tool tip", "window"}


def screen_key(elements):
    """The abstract screen: the interactive elements (role, name, important states) plus which kinds of
    dialog or menu are open. Text contents and window titles are left out, so typing doesn't create
    endless new screens. Fixed after the pilot, before the measured runs; see the pre-registration."""
    items = {(e.role, e.name, tuple(sorted(e.states & SCREEN_STATES))) for e in elements if e.pressable or e.editable}
    items |= {(e.role, "", ()) for e in elements if e.role in SCREEN_CONTAINERS}
    return hashlib.sha1(json.dumps(sorted(items), ensure_ascii=False).encode()).hexdigest()[:16]


def action_key(action):
    """An action by what it is, not where it sits in the tree."""
    e = action.element
    return f"{action.verb}|{e.role}|{e.name}|{action.text}"


def usable(env):
    """Allowed actions, minus elements that say they're disabled. Pressing those changes nothing."""
    out = []
    for action in env.actions():
        states = action.element.states
        if states and not (states & {"sensitive", "enabled"}):
            continue
        out.append(action)
    return out


class RandomExplorer:
    def __init__(self, rng):
        self.rng = rng

    def choose(self, screen, actions):
        return self.rng.choice(actions)


class NoveltyExplorer:
    def __init__(self, rng):
        self.rng = rng
        self.counts = defaultdict(int)

    def choose(self, screen, actions):
        least = min(self.counts[(screen, action_key(a))] for a in actions)
        action = self.rng.choice([a for a in actions if self.counts[(screen, action_key(a))] == least])
        self.counts[(screen, action_key(action))] += 1
        return action


EXPLORERS = {"random": RandomExplorer, "novelty": NoveltyExplorer}


class NoTask:
    description = "explore"

    def is_done(self, elements):
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app", required=True, choices=sorted(APPS))
    parser.add_argument("--explorer", required=True, choices=sorted(EXPLORERS))
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    app = APPS[args.app]
    rng = random.Random(f"{args.app}-{args.explorer}-{args.seed}")
    explorer = EXPLORERS[args.explorer](rng)
    env = DeskEnv(app.backend(), max_steps=EPISODE_STEPS, blocked_names=app.blocked_names(), words=app.words)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{args.app}_{args.explorer}_seed{args.seed}.jsonl.gz"

    steps, episode, errors = 0, 0, 0
    start = time.perf_counter()
    with gzip.open(path, "xt", encoding="utf-8") as f:  # never append to or replace a run
        while steps < args.steps:
            try:
                elements = env.reset(NoTask())
            except Exception as err:
                errors += 1
                print(f"reset failed: {err}", flush=True)
                if errors > 10:
                    raise
                continue
            record = {"format": FORMAT, "app": args.app, "explorer": args.explorer, "seed": args.seed, "episode": episode,
                      "start": snapshot(elements, detail=True), "start_screen": screen_key(elements), "steps": []}
            done = False
            while not done and steps < args.steps:
                actions = usable(env)
                if not actions:
                    break
                screen = screen_key(env.elements)
                action = explorer.choose(screen, actions)
                t0 = time.perf_counter()
                try:
                    elements, _, done, info = env.act(action)
                except Exception as err:  # the element vanished or refused: record it and start again
                    record["steps"].append({"action": action_key(action), "error": str(err)[:200]})
                    steps += 1
                    break
                steps += 1
                record["steps"].append({
                    "action": action_key(action),
                    "path": action.element.path,
                    "screen": screen,
                    "next_screen": screen_key(elements) if elements else None,
                    "next": snapshot(elements, detail=True),
                    "changed": info["changed"],
                    "app_closed": info["app_closed"],
                    "ms": round((time.perf_counter() - t0) * 1000, 1),
                })
                done = done or info["app_closed"]
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            episode += 1
            print(f"{args.app} {args.explorer} seed {args.seed}: {steps}/{args.steps} steps, {episode} episodes, {time.perf_counter() - start:.0f} s", flush=True)
    env.backend.stop()
    print(f"finished: {steps} steps, {episode} episodes, {errors} reset errors, {time.perf_counter() - start:.0f} s", flush=True)


if __name__ == "__main__":
    main()
