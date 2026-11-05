"""Goals for Stage 4: reach a screen that shows a few given elements, starting from a freshly opened app.

A goal comes from a recorded episode of the val or test seed: the app starts fresh, k steps later
(k = 1..HORIZON) some elements are showing that weren't at the start. Up to GOAL_SIZE of them, chosen at
random with a fixed seed, are the goal. Success means every goal element is on the screen.

Elements are compared by goal key: role, name, text, pressable, and only the screen-defining states
(checked, expanded, ...). Focus and hover come and go, so they're left out.

Each goal is tagged by what training saw:
  seen         some training screen already showed all goal elements together
  novel        each goal element was seen in training, but never all together on one screen
  unreachable  some goal element was never seen in training; no model that builds screens from the
               training bank can produce it, so these are counted but not scored

Run:  python3 -m dreamdesk.goals data/wm val
"""
import random
import sys
from collections import Counter
from pathlib import Path

from .explore import SCREEN_STATES
from .wm_data import load
from .wm_eval import App

HORIZON = 5
GOAL_SIZE = 3


def goal_key(token):
    role, name, text, pressable, states = token
    return (role, name, text, pressable, tuple(s for s in states if s in SCREEN_STATES))


def keys_of(app, screen):
    return {goal_key(app.tokens[i]) for i in screen}


class GoalSet:
    def __init__(self, app, split, seed=0, horizon=HORIZON, size=GOAL_SIZE):
        self.app = app
        self.train_screens = [keys_of(app, app.screens[s]) for s in self.train_screen_ids(app)]
        self.train_keys = set().union(*self.train_screens) if self.train_screens else set()
        rng = random.Random(f"{app.name}-{split}-{seed}")
        seen_goals = set()
        self.goals = []
        for ep in app.episodes(split):
            if not ep or ep[0][8] != 0:
                continue  # only episodes recorded from the fresh start
            start = keys_of(app, app.screens[ep[0][0]])
            for k, t in enumerate(ep[:horizon], 1):
                new = sorted(keys_of(app, app.screens[t[4]]) - start)
                if not new:
                    continue
                goal = tuple(sorted(rng.sample(new, min(size, len(new)))))
                if goal in seen_goals:
                    continue
                seen_goals.add(goal)
                self.goals.append({"keys": goal, "steps": k, "kind": self.kind(goal),
                                   "start": ep[0][0], "episode": (t[5], t[6], t[7])})

    @staticmethod
    def train_screen_ids(app):
        ids = set()
        for t in app.transitions["train"]:
            ids.add(t[0])
            ids.add(t[4])
        return sorted(ids)

    def kind(self, goal):
        if any(k not in self.train_keys for k in goal):
            return "unreachable"
        g = set(goal)
        if any(g <= s for s in self.train_screens):
            return "seen"
        return "novel"


def reached(app, screen, goal):
    return set(goal["keys"]) <= keys_of(app, screen)


def main():
    folder, split = Path(sys.argv[1]), sys.argv[2]
    print(f"{'app':13} goals  seen novel unreach | by steps 1..{HORIZON} | start screens")
    for p in sorted(folder.glob("*.pkl")):
        app = App(load(p))
        gs = GoalSet(app, split)
        kinds = Counter(g["kind"] for g in gs.goals)
        steps = Counter(g["steps"] for g in gs.goals)
        starts = len({g["start"] for g in gs.goals})
        print(f"{app.name:13} {len(gs.goals):5} {kinds['seen']:5} {kinds['novel']:5} {kinds['unreachable']:7} | "
              f"{' '.join(f'{steps[k]:3}' for k in range(1, HORIZON + 1))} | {starts}", flush=True)


if __name__ == "__main__":
    main()
