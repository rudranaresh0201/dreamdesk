"""The dream: a batched copy of a real app, run by the world-model ensemble instead of the app.

Each of B parallel episodes starts from a real fresh-start screen recorded in training, gets a goal
(a few elements to bring onto the screen), and steps through the ensemble's predictions. The actions
offered are the ones the real environment would offer on that screen: the same blocked names, the same
skip of disabled elements, press / focus / type a word from the app's list.

Every step also reports the members' disagreement (1 - mean pairwise delta F1 of their own predictions,
as in Stage 3), which the penalised arms subtract from the reward.

  python3 -m dreamdesk.dream --app clocks     # speed check and random-policy success in the dream
"""
import argparse
import itertools
import random
import statistics as stats
import time

import torch

from .apps import APPS
from .goals import GoalSet, goal_key
from .wm_data import load
from .wm_eval import App, delta_f1

MAX_STEPS = int(__import__('os').environ.get('MAX_STEPS', '10'))  # 10 everywhere except the long-task test


def screen_actions(app, screen, blocked, words):
    """(verb, element id, word) for every action the real DeskEnv would allow on this screen."""
    out = []
    for e in sorted(screen):
        role, name, text, pressable, states = app.tokens[e]
        if name in blocked:
            continue
        if states and not (set(states) & {"sensitive", "enabled"}):
            continue
        if pressable:
            out.append(("press", e, ""))
        if "editable" in states:
            out.append(("focus", e, ""))
            out.extend(("type", e, w) for w in words)
    return out


class Dream:
    def __init__(self, ensemble, app_name, data_dir="data/wm", seed=0):
        self.wm = ensemble
        self.app = App(load(f"{data_dir}/{app_name}.pkl"))
        self.wm.fit(self.app)
        spec = APPS[app_name]
        self.blocked = spec.blocked_names()
        self.words = tuple(spec.words)
        self.gkey = [goal_key(t) for t in self.app.tokens]
        self.starts = sorted({ep[0][0] for ep in self.app.episodes("train") if ep and ep[0][8] == 0})
        self.rng = random.Random(seed)

    def keys(self, screen):
        return {self.gkey[i] for i in screen}

    def reset(self, goals):
        """goals: list of goal dicts (with 'keys'); one episode per goal, each from a random real start."""
        self.goals = [set(g["keys"]) for g in goals]
        self.screens = [self.app.screens[self.rng.choice(self.starts)] for _ in goals]
        self.t = 0
        self.done = [False] * len(goals)
        return self.screens

    def actions(self, screen):
        return screen_actions(self.app, screen, self.blocked, self.words)

    def step(self, chosen):
        """chosen: one (verb, element id, word) per episode (ignored for finished ones).
        Returns rewards-relevant info: success flags and disagreement per episode."""
        live = [b for b in range(len(chosen)) if not self.done[b]]
        ts = [(None, chosen[b][0], chosen[b][1], chosen[b][2]) for b in live]
        screens = [self.screens[b] for b in live]
        success, disagree = [False] * len(chosen), [0.0] * len(chosen)
        if live:
            nxt, dis = self.predict(screens, ts)
            for b, s, d in zip(live, nxt, dis):
                self.screens[b] = s
                disagree[b] = d
                success[b] = self.goals[b] <= self.keys(s)
        self.t += 1
        for b in live:
            if success[b] or self.t >= MAX_STEPS:
                self.done[b] = True
        return self.screens, success, disagree

    def predict(self, screens, ts):
        """Ensemble prediction (mean probabilities, then thresholds) plus member disagreement."""
        p, rows, outs = self.wm.probabilities(self.app, screens, ts)
        vt, at = self.wm.vt, self.wm.at
        ens, dis = [], []
        for b, (r, s) in enumerate(zip(rows, screens)):
            members = []
            for v, a in [(o[0][b], o[1][b]) for o in outs] + [(None, None)]:
                if v is None:  # the ensemble itself: mean of the members
                    v = torch.stack([o[0][b] for o in outs]).mean(0)
                    a = torch.stack([o[1][b] for o in outs]).mean(0)
                gone = {e for j, e in enumerate(r) if v[j] > vt}
                came = {p.bank_ids[k] for k in torch.nonzero(a > at).flatten().tolist()} - s
                members.append(frozenset((s - gone) | came))
            ens.append(members.pop())
            pairs = [delta_f1(s, x, y) for x, y in itertools.combinations(members, 2)]
            dis.append(1 - stats.mean(pairs) if pairs else 0.0)
        return ens, dis


def main():
    from .world_model import Neural
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument("--app", required=True)
    ap.add_argument("--members", nargs="+", default=[f"runs/wm/member_seed{k}.pt" for k in range(5)])
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--split", default="val")
    args = ap.parse_args()
    th = json.loads(open("runs/wm/thresholds.json").read())
    dream = Dream(Neural(args.members, "data/wm", th["vanish"], th["appear"]), args.app)
    goals = [g for g in GoalSet(dream.app, args.split).goals if g["kind"] != "unreachable"]
    rng = random.Random(0)
    batch = [rng.choice(goals) for _ in range(args.batch)]
    screens = dream.reset(batch)
    t0, steps, dis_all = time.time(), 0, []
    wins = [False] * len(batch)
    while not all(dream.done):
        chosen = [rng.choice(dream.actions(s) or [("press", next(iter(s)), "")]) for s in screens]
        n_live = sum(not d for d in dream.done)
        screens, success, dis = dream.step(chosen)
        steps += n_live
        wins = [w or s for w, s in zip(wins, success)]
        dis_all += [d for d in dis if d]
    sec = time.time() - t0
    print(f"{args.app}: {steps} dream steps in {sec:.1f} s = {steps / sec:.0f}/s; random policy reaches "
          f"{sum(wins)}/{len(batch)} goals within {MAX_STEPS} steps in the dream; mean disagreement {stats.mean(dis_all or [0]):.3f}")


if __name__ == "__main__":
    main()
