"""Stage 5: a held-out app's data with only the first B real steps of exploration as its training split.

Element ids and screens are kept as they are (so val/test stay identical); only transitions["train"] is cut to
the first B transitions in a fixed order: seed 0 random, seed 0 novelty, seed 1 random, ... (each in episode
and step order). See experiments/transfer_prereg.md.

  python3 -m dreamdesk.budget --apps disk-usage files logs --budgets 100 300 1000
"""
import argparse
import pickle
from pathlib import Path

from .wm_data import load

ORDER = {"random": 0, "novelty": 1}


def cut(data, budget):
    ts = sorted(data["transitions"]["train"], key=lambda t: (t[6], ORDER.get(t[5], 9), t[7], t[8]))
    out = dict(data)
    out["transitions"] = dict(data["transitions"])
    out["transitions"]["train"] = ts[:budget]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apps", nargs="+", required=True)
    ap.add_argument("--budgets", nargs="+", type=int, required=True)
    ap.add_argument("--data", default="data/wm")
    ap.add_argument("--out", default="data/budget")
    args = ap.parse_args()
    for app in args.apps:
        data = load(Path(args.data) / f"{app}.pkl")
        for b in args.budgets:
            folder = Path(args.out) / f"B{b}"
            folder.mkdir(parents=True, exist_ok=True)
            d = cut(data, b)
            with open(folder / f"{app}.pkl", "wb") as f:
                pickle.dump(d, f)
            ts = d["transitions"]["train"]
            print(f"{app:12} B={b:5}: {len(ts)} train transitions (of {len(data['transitions']['train'])}), "
                  f"{len({t[0] for t in ts} | {t[4] for t in ts})} screens", flush=True)


if __name__ == "__main__":
    main()
