"""Foresight (experiments/foresight_prereg.md): does a policy's success in the dream tell, before any real try,
whether that policy will succeed at that goal in the real app?

Items: one per (policy run, goal). x = the run's dream success rate on the goal (achiever dream_eval, 5 tries),
y = its real success (0/1). Baselines score the same items with other per-goal signals:
  random   mean real success of 3 Random runs on the goal (costs real tries)
  graph    real success of the Graph run on the goal (costs a real try)
  short    minus the goal's length in recorded steps
  other    mean dream success of the *other* policy runs on the goal (goal difficulty as the dream sees it)
Intervals: bootstrap resampling goals (all items of a goal together), 2,000 resamples, percentile.

  python3 -m dreamdesk.foresight_report runs/s5_foresight --split final
  python3 -m dreamdesk.foresight_report runs/real_test --split test      # reproduces the exploratory numbers
"""
import argparse
import json
import random
import statistics as st
from collections import defaultdict
from pathlib import Path

RESAMPLES = 2000
RUNS = [(arm, s) for arm in ("dream", "penalty") for s in range(3)]


def auroc(xs, ys):
    """Probability a random success item scores above a random failure item (ties count half)."""
    pos = sorted(x for x, y in zip(xs, ys) if y)
    neg = sorted(x for x, y in zip(xs, ys) if not y)
    if not pos or not neg:
        return float("nan")
    # rank-based, O(n log n)
    allv = sorted([(x, 1) for x in pos] + [(x, 0) for x in neg])
    rank, i, rsum = 0, 0, 0.0
    while i < len(allv):
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]:
            j += 1
        avg = (i + 1 + j) / 2
        rsum += avg * sum(1 for k in range(i, j) if allv[k][1])
        i = j
    return (rsum - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def load(folder, split):
    f = Path(folder)
    dream = {r: json.loads((f / f"{r[0]}_seed{r[1]}_dream_{split}.json").read_text()) for r in RUNS}
    items = []  # dicts: goal id, x per signal, y
    for (arm, s) in RUNS:
        for app, rates in dream[(arm, s)].items():
            rows = [json.loads(l) for l in open(f / f"{app}_{arm}_{split}_seed{s}.jsonl")]
            rnd = [[json.loads(l)["success"] for l in open(f / f"{app}_random_{split}_seed{k}.jsonl")] for k in range(3)]
            gr = [json.loads(l)["success"] for l in open(f / f"{app}_graph_{split}_seed0.jsonl")]
            assert len(rows) == len(rates) == len(gr), app
            for i, r in enumerate(sorted(rows, key=lambda r: r["goal"])):
                items.append({"goal": (app, i), "y": int(r["success"]), "dream": rates[i],
                              "random": st.mean(x[i] for x in rnd), "graph": int(gr[i]), "short": -r["goal_steps"],
                              "other": st.mean(dream[o][app][i] for o in RUNS if o != (arm, s))})
    return items


def pairs_right(items):
    """Same goal, two runs that differ in real outcome and in dream rate: does the higher dream rate win?"""
    by = defaultdict(list)
    for it in items:
        by[it["goal"]].append(it)
    right = tot = 0
    for l in by.values():
        for a in range(len(l)):
            for b in range(a + 1, len(l)):
                if l[a]["y"] != l[b]["y"] and l[a]["dream"] != l[b]["dream"]:
                    tot += 1
                    right += (l[a]["dream"] > l[b]["dream"]) == (l[a]["y"] > l[b]["y"])
    return right, tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--split", default="final")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    items = load(args.folder, args.split)
    goals = sorted({it["goal"] for it in items})
    by = defaultdict(list)
    for it in items:
        by[it["goal"]].append(it)
    signals = ["dream", "random", "graph", "short", "other"]
    point = {k: auroc([it[k] for it in items], [it["y"] for it in items]) for k in signals}
    rng = random.Random("foresight")
    boots = defaultdict(list)
    pr_boot = []
    for _ in range(RESAMPLES):
        sample = [it for g in (rng.choice(goals) for _ in goals) for it in by[g]]
        ys = [it["y"] for it in sample]
        a = {k: auroc([it[k] for it in sample], ys) for k in signals}
        for k in signals:
            boots[k].append(a[k])
            if k != "dream":
                boots[f"dream-{k}"].append(a["dream"] - a[k])
        r, t = pairs_right(sample)
        pr_boot.append(r / t if t else float("nan"))
    ci = lambda v: (sorted(v)[int(0.025 * RESAMPLES)], sorted(v)[int(0.975 * RESAMPLES) - 1])
    rep = {"items": len(items), "goals": len(goals), "auroc": {}, "diff": {}}
    print(f"# Foresight ({args.split}): {len(items)} items (6 policy runs x {len(goals)} goals), "
          f"real success {st.mean(it['y'] for it in items):.1%}\n")
    print("| Signal | AUROC | 95% interval |\n|---|---|---|")
    for k in signals:
        lo, hi = ci(boots[k])
        rep["auroc"][k] = {"auroc": point[k], "lo": lo, "hi": hi}
        print(f"| {k} | {point[k]:.3f} | [{lo:.3f}, {hi:.3f}] |")
    print("\n| Dream − baseline | Difference | 95% interval |\n|---|---|---|")
    for k in signals[1:]:
        lo, hi = ci(boots[f"dream-{k}"])
        rep["diff"][k] = {"diff": point["dream"] - point[k], "lo": lo, "hi": hi}
        print(f"| dream − {k} | {point['dream'] - point[k]:+.3f} | [{lo:+.3f}, {hi:+.3f}] |")
    r, t = pairs_right(items)
    lo, hi = ci([x for x in pr_boot if x == x])
    rep["pairs"] = {"right": r, "total": t, "rate": r / t if t else None, "lo": lo, "hi": hi}
    print(f"\nWithin-goal pairs: the higher dream rate wins in {r} of {t} ({r / max(t, 1):.1%}), 95% [{lo:.1%}, {hi:.1%}]")
    print("\nCalibration (dream rate bin -> real success):")
    for a, b in [(0, 0.001), (0.001, 0.5), (0.5, 0.999), (0.999, 1.01)]:
        sel = [it["y"] for it in items if a <= it["dream"] < b]
        print(f"  [{a}, {b}): n={len(sel)}, real success {st.mean(sel):.2f}" if sel else f"  [{a}, {b}): n=0")
    d = rep["diff"]["random"]
    rep["F1"] = rep["auroc"]["dream"]["lo"] > 0.5 and d["lo"] > 0
    rep["F2"] = lo > 0.5
    print(f"\n**F1 (dream AUROC above chance and above the Random-success baseline): {'PASS' if rep['F1'] else 'FAIL'}**")
    print(f"**F2 (within goal, the dream picks the run that succeeds more than half the time): {'PASS' if rep['F2'] else 'FAIL'}**")
    if args.json:
        Path(args.json).write_text(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
