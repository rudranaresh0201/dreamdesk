"""Test 1 (experiments/scale_prereg.md): does a prior trained on more apps make a new app's dream better?

  python3 -m dreamdesk.scale_report baselines     # Copy and Memo on every held-out app and budget
  python3 -m dreamdesk.scale_report report        # tables, S1, S2

Fine-tuned runs live in runs/scale_ft/{prior7,prior15,prior23}, scratch in runs/scale_ft/scratch
(written by `finetune run`, see scripts/scale_score.sh). Score: val, horizon 5, unvisited windows, delta F1.
"""
import argparse
import json
import random
import statistics as stats
from pathlib import Path

from .wm_data import load
from .wm_eval import App, Copy, Memo, evaluate, summary

DESKTOP = ["disk-usage", "files", "logs"]
WEB = ["web-chat", "web-fitness", "web-quiz", "web-todo", "web-weather"]
APPS = DESKTOP + WEB
BUDGETS = [100, 300]
PRIORS = ["prior7", "prior15", "prior23"]
ARMS = PRIORS + ["scratch"]
BUDGET_DIR = Path("data/budget_scale")
FT = Path("runs/scale_ft")
BASE = FT / "baselines.json"


def baselines(args):
    res = {}
    for app in APPS:
        for b in BUDGETS:
            a = App(load(BUDGET_DIR / f"B{b}" / f"{app}.pkl"))
            for name, m in (("copy", Copy()), ("memo", Memo())):
                m.fit(a)
                _, many = evaluate(m, a, "val")
                res[f"{app}|{b}|{name}"] = summary(many)["unvisited"]
                print(f"{app:12} B{b:<4} {name:5} {res[f'{app}|{b}|{name}']:.3f}", flush=True)
    BASE.write_text(json.dumps(res, indent=1))


def scores():
    """{(arm, app, budget): [score per seed, in seed order]}"""
    out = {}
    for arm in ARMS:
        for f in sorted((FT / arm).glob("*.json")):
            r = json.loads(f.read_text())
            out.setdefault((arm, r["app"], r["budget"]), []).append((r["seed"], r["h5"]["unvisited"]))
    return {k: [v for _, v in sorted(x)] for k, x in out.items()}


def boot(diffs, n=10_000, seed=0):
    rng = random.Random(seed)
    means = sorted(stats.mean(rng.choice(diffs) for _ in diffs) for _ in range(n))
    return stats.mean(diffs), means[int(0.025 * n)], means[int(0.975 * n) - 1]


def report(args):
    s = scores()
    base = json.loads(BASE.read_text()) if BASE.exists() else {}
    f = lambda x: f"{x:.3f}" if x is not None else "-"
    missing = [(arm, app, b) for arm in ARMS for app in APPS for b in BUDGETS if len(s.get((arm, app, b), [])) != 3]
    if missing:
        print(f"NOTE: {len(missing)} cells lack 3 seeds, e.g. {missing[:4]}\n")
    for b in BUDGETS:
        print(f"\n### B = {b} (horizon 5, unvisited windows, val; mean of 3 seeds, seeds in brackets)\n")
        print("| App | Copy | Memo | Scratch | P7 | P15 | P23 | P23 − P7 |")
        print("|---|---|---|---|---|---|---|---|")
        for app in APPS:
            m = {arm: stats.mean(s[(arm, app, b)]) if s.get((arm, app, b)) else None for arm in ARMS}
            cell = lambda arm: f"**{f(m[arm])}** ({', '.join(f(x) for x in s.get((arm, app, b), []))})"
            d = m["prior23"] - m["prior7"] if m["prior23"] is not None and m["prior7"] is not None else None
            print(f"| {app} | {f(base.get(f'{app}|{b}|copy'))} | {f(base.get(f'{app}|{b}|memo'))} | "
                  f"{cell('scratch')} | {cell('prior7')} | {cell('prior15')} | {cell('prior23')} | {f(d) if d is None else f'{d:+.3f}'} |")
    print()
    for b in BUDGETS:
        for label, apps in (("all 8 held-out apps", APPS), ("desktop held-out apps", DESKTOP), ("web held-out apps", WEB)):
            for hi, lo in (("prior23", "prior7"), ("prior15", "prior7"), ("prior23", "prior15"), ("prior7", "scratch")):
                diffs = [stats.mean(s[(hi, a, b)]) - stats.mean(s[(lo, a, b)]) for a in apps if s.get((hi, a, b)) and s.get((lo, a, b))]
                if len(diffs) < 2:
                    continue
                mean, lo_ci, hi_ci = boot(diffs)
                tag = ""
                if b == 100 and (hi, lo) == ("prior23", "prior7") and apps in (APPS, DESKTOP):
                    tag = (" <- S1" if apps is APPS else " <- S2") + (" PASS" if lo_ci > 0 else " FAIL")
                print(f"B{b} {label:22} {hi} − {lo}: {mean:+.3f} [{lo_ci:+.3f}, {hi_ci:+.3f}] over {len(diffs)} apps{tag}")
        print()
    for b in BUDGETS:
        order = [app for app in APPS if all(s.get((p, app, b)) for p in PRIORS)
                 and stats.mean(s[("prior7", app, b)]) <= stats.mean(s[("prior15", app, b)]) <= stats.mean(s[("prior23", app, b)])]
        print(f"B{b}: P7 <= P15 <= P23 holds in {len(order)} of {len(APPS)} apps: {', '.join(order) or '-'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["baselines", "report"])
    args = ap.parse_args()
    baselines(args) if args.cmd == "baselines" else report(args)


if __name__ == "__main__":
    main()
