"""Add a new recording seed to existing app datasets as a new split, keeping every element and screen id.

Old ids stay as they are (new elements and screens get new ids at the end), so models trained on the old files
still read the new ones the same way. Used for the sealed seed 5 ("final" split) of the Stage 5 task test.

  python3 -m dreamdesk.add_split --src data/explore_seed5 --seed 5 --split final \
      --apps disk-usage files logs --data data/wm --out data/wm_final
"""
import argparse
import gzip
import json
import pickle
from collections import defaultdict
from pathlib import Path

from . import wm_data
from .wm_data import AppData, load


def restore(d):
    a = AppData(d["app"])
    a.tokens, a.boxes = list(d["tokens"]), list(d["boxes"])
    a.vocab = {t: i for i, t in enumerate(a.tokens)}
    a.screen_list = list(d["screens"])
    a.screens = {s: i for i, s in enumerate(a.screen_list)}
    a.transitions = defaultdict(list, {k: list(v) for k, v in d["transitions"].items()})
    return a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--split", required=True)
    ap.add_argument("--apps", nargs="+", required=True)
    ap.add_argument("--data", default="data/wm")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    assert args.seed not in wm_data.SPLIT, "seed already belongs to a split"
    wm_data.SPLIT[args.seed] = args.split
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for app in args.apps:
        old = load(Path(args.data) / f"{app}.pkl")
        a = restore(old)
        assert args.split not in a.transitions
        n_tok, n_scr = len(a.tokens), len(a.screen_list)
        for p in sorted(Path(args.src).glob(f"{app}_*_seed{args.seed}.jsonl.gz")):
            explorer = p.name.replace(".jsonl.gz", "").rsplit("_", 2)[1]
            with gzip.open(p, "rt", encoding="utf-8") as f:
                for line in f:
                    try:
                        a.add_episode(json.loads(line), explorer, args.seed)
                    except json.JSONDecodeError:
                        break
        assert a.tokens[:n_tok] == old["tokens"] and a.screen_list[:n_scr] == old["screens"]
        assert all(a.transitions[k] == old["transitions"][k] for k in old["transitions"])
        with open(out / f"{app}.pkl", "wb") as f:
            pickle.dump({"app": a.app, "tokens": a.tokens, "boxes": a.boxes, "screens": a.screen_list,
                         "transitions": dict(a.transitions)}, f)
        print(f"{app:12} {args.split}: {len(a.transitions[args.split])} transitions; "
              f"new elements {len(a.tokens) - n_tok}, new screens {len(a.screen_list) - n_scr}", flush=True)


if __name__ == "__main__":
    main()
