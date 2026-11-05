"""Stage 4 report from the raw per-goal files (experiments/stage4_prereg.md).

Reads {app}_{arm}_{split}_seed{s}.jsonl from real_eval and {arm}_seed{s}_dream_{split}.json from
achiever dream_eval. Per goal, each arm's success is averaged over its seeds; arms are compared with a paired
bootstrap over goals (2,000 resamples, 95% percentile interval).

"Never practised" (the H1 subgroup): the goal's keys are in no Dream seed's practised_goals.json.

  python3 -m dreamdesk.stage4_report runs/real_test --split test
  python3 -m dreamdesk.stage4_report runs/real_pilot --split val --arms random graph dev --dream-arm dev \
      --practised runs/ach_dev/practised_goals.json      # pilot check of the script
"""
import argparse
import glob
import json
import random
import re
import statistics as stats
from collections import defaultdict
from pathlib import Path

RESAMPLES = 2000


def canon(keys):
    return tuple(tuple(tuple(x) if isinstance(x, list) else x for x in k) for k in keys)


def load_real(folder, split, arms):
    """{arm: {seed: {app: [rows in goal order]}}}"""
    out = defaultdict(lambda: defaultdict(dict))
    pat = re.compile(rf"^(.+)_({'|'.join(map(re.escape, arms))})_{split}_seed(\d+)\.jsonl$")
    for p in sorted(Path(folder).glob(f"*_{split}_seed*.jsonl")):
        m = pat.match(p.name)
        if not m:
            continue
        app, arm, seed = m.group(1), m.group(2), int(m.group(3))
        rows = [json.loads(l) for l in open(p)]
        out[arm][seed][app] = sorted(rows, key=lambda r: r["goal"])
    return out


def goal_table(real, apps):
    """One entry per goal: app, index, keys, kind; checked identical across every arm and seed."""
    goals = []
    for app in apps:
        ref = None
        for arm in real:
            for seed, by_app in real[arm].items():
                rows = by_app.get(app)
                if rows is None:
                    continue
                keys = [canon(r["keys"]) for r in rows]
                if ref is None:
                    ref = (keys, [r["kind"] for r in rows], [r["goal_steps"] for r in rows])
                elif keys != ref[0]:
                    raise SystemExit(f"goal lists differ for {app} ({arm} seed {seed})")
        if ref:
            goals += [{"app": app, "i": i, "keys": k, "kind": kd, "steps": s} for i, (k, kd, s) in enumerate(zip(*ref))]
    return goals


def per_goal(real, arm, goals):
    """Success averaged over the arm's seeds, per goal; None if any seed lacks that app."""
    seeds = sorted(real[arm])
    out = []
    for g in goals:
        vals = [real[arm][s][g["app"]][g["i"]]["success"] for s in seeds if g["app"] in real[arm][s]]
        out.append(stats.mean(vals) if len(vals) == len(seeds) else None)
    return out


def boot(diff, rng):
    n = len(diff)
    if not n:
        return float("nan"), float("nan"), float("nan")
    means = sorted(sum(diff[rng.randrange(n)] for _ in range(n)) / n for _ in range(RESAMPLES))
    return sum(diff) / n, means[int(0.025 * RESAMPLES)], means[int(0.975 * RESAMPLES) - 1]


def pct(x):
    return f"{100 * x:.1f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--split", default="test")
    ap.add_argument("--arms", nargs="+", default=["random", "graph", "dream", "penalty"])
    ap.add_argument("--dream-arm", default="dream")
    ap.add_argument("--practised", nargs="+", default=None,
                    help="practised_goals.json files (default: runs/ach/{dream-arm}_seed*/practised_goals.json)")
    ap.add_argument("--json", default=None, help="also write the numbers here")
    args = ap.parse_args()

    real = load_real(args.folder, args.split, args.arms)
    arms = [a for a in args.arms if a in real]
    apps = sorted({app for a in arms for s in real[a] for app in real[a][s]})
    goals = goal_table(real, apps)
    files = args.practised or sorted(glob.glob(f"runs/ach/{args.dream_arm}_seed*/practised_goals.json"))
    practised = defaultdict(set)
    for f in files:
        for app, gs in json.loads(Path(f).read_text()).items():
            practised[app].update(canon(g) for g in gs)
    for g in goals:
        g["practised"] = g["keys"] in practised[g["app"]]
    succ = {a: per_goal(real, a, goals) for a in arms}
    report = {"split": args.split, "goals": len(goals), "practised_files": files, "arms": {}, "comparisons": {}, "gap": {}}

    print(f"# Stage 4 report ({args.split}, {len(goals)} goals, {sum(g['kind'] == 'novel' for g in goals)} novel, "
          f"{sum(not g['practised'] for g in goals)} never practised by any {args.dream_arm} seed; "
          f"practised from {len(files)} file(s))\n")

    groups = {
        "all": lambda g: True,
        "familiar": lambda g: g["kind"] != "novel",
        "novel": lambda g: g["kind"] == "novel",
        "never practised": lambda g: not g["practised"],
        "practised": lambda g: g["practised"],
    }
    print("## Real success by arm (mean over seeds per goal, then over goals)\n")
    print("| Arm | Seeds | " + " | ".join(groups) + " | Per-seed pooled (median, range) |")
    print("|---|---|" + "---|" * len(groups) + "---|")
    for a in arms:
        row = []
        for name, f in groups.items():
            v = [s for s, g in zip(succ[a], goals) if f(g) and s is not None]
            row.append(f"{pct(stats.mean(v))} (n={len(v)})" if v else "n/a")
        seed_pooled = []
        for s in sorted(real[a]):
            v = [r["success"] for app in real[a][s] for r in real[a][s][app]]
            seed_pooled.append(stats.mean(v))
        rng_txt = f"{pct(stats.median(seed_pooled))} [{pct(min(seed_pooled))}, {pct(max(seed_pooled))}]"
        print(f"| {a} | {len(real[a])} | " + " | ".join(row) + f" | {rng_txt} |")
        report["arms"][a] = {"seeds": sorted(real[a]), "per_seed_pooled": seed_pooled}

    print("\n## Per app (real success)\n")
    print("| App | n | " + " | ".join(arms) + " |")
    print("|---|---|" + "---|" * len(arms))
    for app in apps:
        idx = [k for k, g in enumerate(goals) if g["app"] == app]
        cells = []
        for a in arms:
            v = [succ[a][k] for k in idx if succ[a][k] is not None]
            cells.append(pct(stats.mean(v)) if v else "n/a")
        print(f"| {app} | {len(idx)} | " + " | ".join(cells) + " |")

    pairs = [(args.dream_arm, "random"), (args.dream_arm, "graph"), ("penalty", args.dream_arm), ("graph", "random")]
    print("\n## Paired differences (bootstrap 95% interval over goals)\n")
    print("| Comparison | Group | n | Difference | 95% interval |")
    print("|---|---|---|---|---|")
    for a, b in pairs:
        if a not in arms or b not in arms or a == b:
            continue
        rng = random.Random(f"{a}-{b}")
        for name, f in groups.items():
            diff = [x - y for x, y, g in zip(succ[a], succ[b], goals) if f(g) and x is not None and y is not None]
            m, lo, hi = boot(diff, rng)
            print(f"| {a} − {b} | {name} | {len(diff)} | {100 * m:+.1f} | [{100 * lo:+.1f}, {100 * hi:+.1f}] |")
            report["comparisons"][f"{a}-{b}-{name}"] = {"n": len(diff), "diff": m, "lo": lo, "hi": hi}

    h1 = [report["comparisons"].get(f"{args.dream_arm}-random-{g}") for g in ("all", "never practised")]
    if all(h1):
        passed = all(c["lo"] > 0 for c in h1)
        print(f"\n**H1 ({args.dream_arm} beats random, pooled and on never-practised goals): {'PASS' if passed else 'FAIL'}**")
        report["h1_pass"] = passed

    print("\n## Dream success vs real success (the gap)\n")
    print("| Arm | Dream | Real (same goals) | Gap |")
    print("|---|---|---|---|")
    for a in arms:
        dfiles = sorted(Path(args.folder).glob(f"{a}_seed*_dream_{args.split}.json"))
        if not dfiles:
            continue
        dream = defaultdict(list)  # (app, i) -> per seed
        for f in dfiles:
            for app, v in json.loads(f.read_text()).items():
                for i, x in enumerate(v):
                    dream[(app, i)].append(x)
        pairs_dr = [(stats.mean(dream[(g["app"], g["i"])]), s) for g, s in zip(goals, succ[a])
                    if (g["app"], g["i"]) in dream and s is not None]
        if pairs_dr:
            d, r = stats.mean(p[0] for p in pairs_dr), stats.mean(p[1] for p in pairs_dr)
            print(f"| {a} ({len(dfiles)} seeds) | {pct(d)} | {pct(r)} | {100 * (d - r):+.1f} points |")
            report["gap"][a] = {"dream": d, "real": r, "seeds": len(dfiles)}
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
