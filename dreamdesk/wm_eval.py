"""Scoring world models: does a model predict the next screen correctly, one step and five steps ahead?

A screen is the set of element ids on it (see wm_data.py). A prediction is scored on what changed:
the elements that vanished and the elements that appeared, against what really happened.

  delta F1 = 2 |predicted changes ∩ real changes| / (|predicted changes| + |real changes|),  1 if both are empty

Copy (predict nothing changes) scores 0 whenever something really changed, so the metric rewards
getting the changes right, not the hundreds of elements that stay put.

Baselines:
  copy   nothing changes
  memo   the change recorded in training for this exact screen and action, then for the same abstract
         screen (explore.screen_key) and action, then for the same action anywhere, then copy

Run (val only until the pre-registration is committed):
  python3 -m dreamdesk.wm_eval data/wm val
"""
import random
import statistics as stats
import sys
from collections import Counter, defaultdict
from pathlib import Path

from .explore import SCREEN_CONTAINERS, SCREEN_STATES
from .wm_data import load

HORIZON = 5


class App:
    """One app's data, with screens as sets and episodes as ordered steps."""

    def __init__(self, data):
        self.name = data["app"]
        self.tokens = data["tokens"]
        self.screens = [frozenset(i for i, _ in s) for s in data["screens"]]
        self.depth = {}
        for s in data["screens"]:
            for i, d in s:
                self.depth.setdefault(i, d)
        self.transitions = data["transitions"]

    def action(self, t):
        verb, target, word = t[1], t[2], t[3]
        role, name = self.tokens[target][0], self.tokens[target][1]
        return (verb, target, word), (verb, role, name, word)

    def abstract(self, screen):
        """The same abstract screen as explore.screen_key, computed from element ids."""
        items = set()
        for i in screen:
            role, name, _, pressable, states = self.tokens[i]
            if pressable or "editable" in states:
                items.add((role, name, tuple(sorted(set(states) & SCREEN_STATES))))
            if role in SCREEN_CONTAINERS:
                items.add((role, "", ()))
        return frozenset(items)

    def episodes(self, split):
        eps = defaultdict(list)
        for t in self.transitions.get(split, []):
            eps[(t[5], t[6], t[7])].append(t)
        return [sorted(v, key=lambda t: t[8]) for v in eps.values()]


def delta(before, after):
    return {("-", i) for i in before - after} | {("+", i) for i in after - before}


def delta_f1(start, predicted, real):
    p, r = delta(start, predicted), delta(start, real)
    if not p and not r:
        return 1.0
    return 2 * len(p & r) / (len(p) + len(r))


def apply_change(screen, removed, added):
    return frozenset((screen - removed) | added)


class Copy:
    name = "copy"

    def fit(self, app):
        pass

    def predict(self, app, screen, t):
        return screen


class Memo:
    """A lookup table of what happened in training, backing off from exact to general."""
    name = "memo"

    def fit(self, app):
        self.tables = [defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)]
        for t in app.transitions["train"]:
            before, after = app.screens[t[0]], app.screens[t[4]]
            change = (frozenset(before - after), frozenset(after - before))
            exact, general = app.action(t)
            for table, key in zip(self.tables, self.keys(app, before, exact, general)):
                table[key][change] += 1

    @staticmethod
    def keys(app, screen, exact, general):
        return [(screen, exact), (app.abstract(screen), general), general]

    def predict(self, app, screen, t):
        exact, general = app.action(t)
        for table, key in zip(self.tables, self.keys(app, screen, exact, general)):
            if key in table:
                (removed, added), _ = table[key].most_common(1)[0]
                return apply_change(screen, removed & screen, added)
        return screen


def visited_pairs(app):
    return {(app.abstract(app.screens[t[0]]), app.action(t)[1]) for t in app.transitions["train"]}


def predict_many(model, app, screens, ts, chunk=512):
    if hasattr(model, "predict_batch"):
        out = []
        for i in range(0, len(ts), chunk):
            out += model.predict_batch(app, screens[i:i + chunk], ts[i:i + chunk])
        return out
    return [model.predict(app, s, t) for s, t in zip(screens, ts)]


def evaluate(model, app, split, horizon=HORIZON):
    """Per-transition scores at horizon 1, and per-window scores at `horizon`, rolling the model on its
    own predictions with the real actions. Each item is tagged visited or unvisited by whether its first
    step's (abstract screen, action) pair appears in training. All windows advance together, in batches."""
    seen = visited_pairs(app)
    flat, windows = [], []
    for ep in app.episodes(split):
        for k, t in enumerate(ep):
            flat.append(t)
            if k + horizon <= len(ep):
                windows.append(ep[k:k + horizon])
    unv = lambda t: (app.abstract(app.screens[t[0]]), app.action(t)[1]) not in seen
    starts = [app.screens[t[0]] for t in flat]
    preds = predict_many(model, app, starts, flat)
    one = [(unv(t), delta_f1(s, p, app.screens[t[4]])) for t, s, p in zip(flat, starts, preds)]
    screens = [app.screens[w[0][0]] for w in windows]
    for h in range(horizon):
        screens = predict_many(model, app, screens, [w[h] for w in windows])
    many = [(unv(w[0]), delta_f1(app.screens[w[0][0]], s, app.screens[w[-1][4]])) for w, s in zip(windows, screens)]
    return one, many


def summary(scores):
    unv = [s for u, s in scores if u]
    return {"all": stats.mean(s for _, s in scores) if scores else None, "unvisited": stats.mean(unv) if unv else None, "n_unvisited": len(unv)}


def bootstrap_diff(a, b, reps=2000, seed=0):
    """95% interval for mean(a) - mean(b) over paired items."""
    rng = random.Random(seed)
    d = [x - y for x, y in zip(a, b)]
    means = sorted(stats.mean(rng.choices(d, k=len(d))) for _ in range(reps))
    return stats.mean(d), means[int(0.025 * reps)], means[int(0.975 * reps)]


def main():
    folder, split = Path(sys.argv[1]), sys.argv[2]
    print(f"{'app':13} {'model':5} | h=1 all  unvisited (n) | h={HORIZON} all  unvisited (n)")
    for p in sorted(folder.glob("*.pkl")):
        app = App(load(p))
        for model in (Copy(), Memo()):
            model.fit(app)
            one, many = evaluate(model, app, split)
            a, b = summary(one), summary(many)
            fmt = lambda x: f"{x:.3f}" if x is not None else "  -  "
            print(f"{app.name:13} {model.name:5} | {fmt(a['all'])}  {fmt(a['unvisited'])} ({a['n_unvisited']:4}) | "
                  f"{fmt(b['all'])}  {fmt(b['unvisited'])} ({b['n_unvisited']:4})", flush=True)


if __name__ == "__main__":
    main()
