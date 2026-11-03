"""Turns exploration recordings into a compact dataset for the world model.

Every distinct element (role, name, text, states) gets an integer id per app, and every distinct screen
is stored once as a tuple of (element id, depth) in tree order. A transition is then three small things:
the screen before, the action, and the screen after. This keeps 50,000 transitions in tens of MB of RAM,
instead of the several GB that raw snapshot lists take (which crashed the laptop once).

Split by seed, fixed before any model is trained: seeds 0-2 train, seed 3 validation, seed 4 test.

Run:  python3 -m dreamdesk.wm_data data/explore data/wm
"""
import gzip
import json
import pickle
import sys
from collections import defaultdict
from pathlib import Path

SPLIT = {0: "train", 1: "train", 2: "train", 3: "val", 4: "test"}


def token(row):
    """An element as the world model sees it. Path and box are left out: they're layout, not state."""
    return (row[1], row[2], row[3], bool(row[4]), tuple(sorted(row[5])))


class AppData:
    def __init__(self, app):
        self.app = app
        self.vocab = {}  # token -> id
        self.tokens = []  # id -> token
        self.boxes = []  # id -> last box seen, only for drawing the dream
        self.screens = {}  # tuple of (id, depth) -> screen index
        self.screen_list = []
        self.transitions = defaultdict(list)  # split -> [(before, verb, target id, word, after, explorer, seed, episode, t)]

    def element_id(self, row):
        tok = token(row)
        i = self.vocab.get(tok)
        if i is None:
            i = self.vocab[tok] = len(self.tokens)
            self.tokens.append(tok)
            self.boxes.append(tuple(row[6]))
        else:
            self.boxes[i] = tuple(row[6])
        return i

    def screen_id(self, rows):
        key = tuple((self.element_id(r), r[0].count(".")) for r in rows)
        s = self.screens.get(key)
        if s is None:
            s = self.screens[key] = len(self.screen_list)
            self.screen_list.append(key)
        return s

    def add_episode(self, ep, explorer, seed):
        rows = ep["start"]
        before = self.screen_id(rows)
        by_path = {r[0]: r for r in rows}
        for t, s in enumerate(ep["steps"]):
            if "error" in s or not s["next"]:
                break  # an error or a closed app ends what we can learn from this episode
            verb, _, rest = s["action"].partition("|")
            word = rest.split("|")[-1] if verb == "type" else ""
            target_row = by_path.get(s["path"])
            if target_row is None:
                break
            target = self.element_id(target_row)
            after = self.screen_id(s["next"])
            self.transitions[SPLIT[seed]].append((before, verb, target, word, after, explorer, seed, ep["episode"], t))
            before, by_path = after, {r[0]: r for r in s["next"]}

    def save(self, path):
        with open(path, "wb") as f:
            pickle.dump({"app": self.app, "tokens": self.tokens, "boxes": self.boxes, "screens": self.screen_list,
                         "transitions": dict(self.transitions)}, f)


def load(path):
    with open(path, "rb") as f:
        return pickle.load(f)


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    runs = defaultdict(list)
    for p in sorted(src.glob("*.jsonl.gz")):
        app, explorer, seed = p.name.replace(".jsonl.gz", "").rsplit("_", 2)
        runs[app].append((p, explorer, int(seed[4:])))
    for app, files in sorted(runs.items()):  # one app in memory at a time
        data = AppData(app)
        for p, explorer, seed in files:
            with gzip.open(p, "rt", encoding="utf-8") as f:
                for line in f:
                    try:
                        data.add_episode(json.loads(line), explorer, seed)
                    except json.JSONDecodeError:
                        break
        data.save(out / f"{app}.pkl")
        n = {k: len(v) for k, v in data.transitions.items()}
        print(f"{app:13} elements {len(data.tokens):6}  screens {len(data.screen_list):6}  "
              f"train {n.get('train', 0):5}  val {n.get('val', 0):5}  test {n.get('test', 0):5}", flush=True)


if __name__ == "__main__":
    main()
