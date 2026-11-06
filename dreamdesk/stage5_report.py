"""Stage 5 task report (experiments/tasks_prereg.md): real task success on held-out apps against exploration budget.

Reads {app}_{arm}_{split}_seed{s}.jsonl from scripts/stage5_tasks.sh. Per goal, success is averaged over seeds;
arms are compared with a paired bootstrap over goals pooled across the 3 apps (stage4_report.boot).
"In bank" (per budget): every goal element was seen somewhere in the first B clicks.
"Map-covered" (per budget): some screen in the first B clicks showed every goal element together.

  python3 -m dreamdesk.stage5_report runs/s5_final --split final
"""
import argparse
import json
import random
import statistics as stats
from pathlib import Path

from .goals import keys_of
from .stage4_report import boot, canon, goal_table, load_real, per_goal, pct
from .wm_data import load
from .wm_eval import App

BUDGETS = [100, 300, 1000]


def budget_screens(app_name, b):
    """Goal-key sets of every screen seen in the first B clicks."""
    app = App(load(Path("data/budget_final") / f"B{b}" / f"{app_name}.pkl"))
    ids = {t[0] for t in app.transitions["train"]} | {t[4] for t in app.transitions["train"]}
    return [{canon([k])[0] for k in keys_of(app, app.screens[i])} for i in ids]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--split", default="final")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    arms = ["random"] + [f"{a}-B{b}" for b in BUDGETS for a in ("graph", "planner")]
    real = load_real(args.folder, args.split, arms)
    arms = [a for a in arms if a in real]
    apps = sorted({app for a in arms for s in real[a] for app in real[a][s]})
    goals = goal_table(real, apps)
    screens = {(app, b): budget_screens(app, b) for app in apps for b in BUDGETS}
    for g in goals:
        sc = {b: screens[(g["app"], b)] for b in BUDGETS}
        g["in_bank"] = {b: all(any(k in s for s in sc[b]) for k in g["keys"]) for b in BUDGETS}
        g["covered"] = {b: any(set(g["keys"]) <= s for s in sc[b]) for b in BUDGETS}
    succ = {a: per_goal(real, a, goals) for a in arms}
    rep = {"goals": len(goals), "success": {}, "comparisons": {}}

    print(f"# Stage 5 tasks ({args.split}, {len(goals)} goals over {', '.join(apps)})\n")
    print("## Real success (mean over seeds per goal, then over goals)\n")
    print("| Arm | Seeds | All | " + " | ".join(apps) + " |")
    print("|---|---|---|" + "---|" * len(apps))
    for a in arms:
        cells = []
        for app in apps:
            v = [s for s, g in zip(succ[a], goals) if g["app"] == app and s is not None]
            cells.append(pct(stats.mean(v)) if v else "n/a")
        v = [s for s in succ[a] if s is not None]
        rep["success"][a] = stats.mean(v)
        print(f"| {a} | {len(real[a])} | **{pct(stats.mean(v))}** | " + " | ".join(cells) + " |")

    print("\n## Paired differences, pooled over apps (bootstrap 95% interval over goals)\n")
    print("| Budget | Comparison | Group | n | Difference | 95% interval |")
    print("|---|---|---|---|---|---|")
    for b in BUDGETS:
        p, gr = f"planner-B{b}", f"graph-B{b}"
        for a, c in ((p, gr), (p, "random"), (gr, "random")):
            if a not in succ or c not in succ:
                continue
            rng = random.Random(f"{a}-{c}")
            for name, f in (("all", lambda g: True), ("map-covered", lambda g: g["covered"][b]),
                            ("not map-covered", lambda g: not g["covered"][b]),
                            ("not in bank", lambda g: not g["in_bank"][b])):
                d = [x - y for x, y, g in zip(succ[a], succ[c], goals) if f(g) and x is not None and y is not None]
                m, lo, hi = boot(d, rng)
                print(f"| {b} | {a} − {c} | {name} | {len(d)} | {100 * m:+.1f} | [{100 * lo:+.1f}, {100 * hi:+.1f}] |")
                rep["comparisons"][f"{a}|{c}|{name}"] = {"n": len(d), "diff": m, "lo": lo, "hi": hi}

    print("\n## Gate (primary: B = 300)\n")
    c = rep["comparisons"].get("planner-B300|graph-B300|all")
    r = [rep["comparisons"].get(f"planner-B{b}|random|all") for b in BUDGETS]
    if c:
        rep["pass_primary"] = c["lo"] > 0
        print(f"**H1 (dream planner beats the map at 300 clicks): {100 * c['diff']:+.1f} "
              f"[{100 * c['lo']:+.1f}, {100 * c['hi']:+.1f}] -> {'PASS' if c['lo'] > 0 else 'FAIL'}**")
    if all(r):
        rep["pass_random"] = all(x["lo"] > 0 for x in r)
        print(f"**H2 (dream planner beats random at every budget): {'PASS' if rep['pass_random'] else 'FAIL'}**")
    if args.json:
        Path(args.json).write_text(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
