"""Generalisation test report (experiments/generalise_prereg.md): seen vs combo goals, map vs dream vs random.

"seen": an explored screen showed every goal element together (a map can aim at it).
"combo": every goal element was seen while exploring, never all on one screen (a map has nothing to aim at).
Reads {app}_{arm}-B{b}_{split}_seed{s}.jsonl. Per goal, success is averaged over seeds. Items are (budget, goal)
pairs, pooled over budgets; intervals are paired bootstraps over items (2,000 resamples, percentile).

  python3 -m dreamdesk.gen_report runs/gen_final --split final6
"""
import argparse
import json
import random
import statistics as st
from pathlib import Path

from .stage4_report import canon

ARMS = ["random", "graph", "planner"]
RESAMPLES = 2000


def load(folder, split, app, budgets):
    """{budget: [{"kind", "keys", arm: mean success}]}"""
    out = {}
    for b in budgets:
        goals = None
        per = {}
        for arm in ARMS:
            runs = sorted(Path(folder).glob(f"{app}_{arm}-B{b}_{split}_seed*.jsonl"))
            if not runs:
                continue
            rows = [sorted((json.loads(l) for l in open(p)), key=lambda r: r["goal"]) for p in runs]
            keys = [canon(r["keys"]) for r in rows[0]]
            for rs in rows:
                assert [canon(r["keys"]) for r in rs] == keys, f"goal lists differ in {arm} B{b}"
            if goals is None:
                goals = [{"kind": r["kind"], "keys": k} for r, k in zip(rows[0], keys)]
            assert [g["keys"] for g in goals] == keys, f"goal lists differ between arms at B{b}"
            per[arm] = [st.mean(rs[i]["success"] for rs in rows) for i in range(len(keys))]
            per[f"{arm}_seeds"] = len(runs)
        if goals:
            for i, g in enumerate(goals):
                for arm in ARMS:
                    if arm in per:
                        g[arm] = per[arm][i]
            out[b] = (goals, {a: per.get(f"{a}_seeds", 0) for a in ARMS})
    return out


def boot(xs, rng):
    n = len(xs)
    if not n:
        return float("nan"), float("nan"), float("nan")
    m = sorted(sum(xs[rng.randrange(n)] for _ in range(n)) / n for _ in range(RESAMPLES))
    return sum(xs) / n, m[int(0.025 * RESAMPLES)], m[int(0.975 * RESAMPLES) - 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--split", default="final6")
    ap.add_argument("--app", default="files")
    ap.add_argument("--budgets", nargs="+", type=int, default=[100, 300])
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    data = load(args.folder, args.split, args.app, args.budgets)
    items = [dict(g, budget=b) for b, (gs, _) in data.items() for g in gs]
    rep = {"success": {}, "comparisons": {}}
    pct = lambda x: f"{100 * x:.1f}%"
    print(f"# Generalisation test ({args.app}, {args.split})\n")
    print("| Budget | Kind | n | " + " | ".join(ARMS) + " |\n|---|---|---|" + "---|" * len(ARMS))
    for b, (gs, seeds) in data.items():
        for kind in ("seen", "combo"):
            sel = [g for g in gs if g["kind"] == kind]
            cells = [pct(st.mean(g[a] for g in sel)) if sel and a in sel[0] else "-" for a in ARMS]
            rep["success"][f"B{b}|{kind}"] = {a: st.mean(g[a] for g in sel) for a in ARMS if sel and a in sel[0]}
            print(f"| {b} | {kind} | {len(sel)} | " + " | ".join(cells) + " |")
    print(f"\nSeeds per arm: {', '.join(f'B{b}: ' + str(s) for b, (_, s) in data.items())}\n")
    print("| Comparison | Items | n | Difference | 95% interval |\n|---|---|---|---|---|")
    for a, c in (("planner", "graph"), ("planner", "random"), ("graph", "random")):
        for kind in ("combo", "seen"):
            d = [g[a] - g[c] for g in items if g["kind"] == kind and a in g and c in g]
            m, lo, hi = boot(d, random.Random(f"{a}-{c}-{kind}"))
            rep["comparisons"][f"{a}-{c}|{kind}"] = {"n": len(d), "diff": m, "lo": lo, "hi": hi}
            print(f"| {a} − {c} | {kind} | {len(d)} | {100 * m:+.1f} | [{100 * lo:+.1f}, {100 * hi:+.1f}] |")
    # the memorise/generalise signature: how much more the map loses than the dream when going seen -> combo
    rng = random.Random("interaction")
    seen = [g["planner"] - g["graph"] for g in items if g["kind"] == "seen"]
    combo = [g["planner"] - g["graph"] for g in items if g["kind"] == "combo"]
    vals = sorted(st.mean(rng.choices(combo, k=len(combo))) - st.mean(rng.choices(seen, k=len(seen)))
                  for _ in range(RESAMPLES)) if seen and combo else []
    if vals:
        m = st.mean(combo) - st.mean(seen)
        lo, hi = vals[int(0.025 * RESAMPLES)], vals[int(0.975 * RESAMPLES) - 1]
        rep["comparisons"]["interaction"] = {"diff": m, "lo": lo, "hi": hi}
        print(f"| (planner − graph) on combo − on seen | interaction | {len(combo)}+{len(seen)} | {100 * m:+.1f} | [{100 * lo:+.1f}, {100 * hi:+.1f}] |")
    g1 = rep["comparisons"].get("planner-graph|combo")
    g2 = rep["comparisons"].get("planner-random|combo")
    if g1 and g2:
        rep["G1"], rep["G2"] = g1["lo"] > 0, g2["lo"] > 0
        print(f"\n**G1 (dream beats the map on combo goals): {'PASS' if rep['G1'] else 'FAIL'}**")
        print(f"**G2 (dream beats random on combo goals): {'PASS' if rep['G2'] else 'FAIL'}**")
    if args.json:
        Path(args.json).write_text(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
