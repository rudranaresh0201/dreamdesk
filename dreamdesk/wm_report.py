"""Stage 3 report, as pre-registered in experiments/world_model_prereg.md.

  tune   choose vanish and appear thresholds on val (mean horizon-1 delta F1 over all items, apps equal)
  test   the single test run: Copy, Memo, the ensemble and each single member; gate, bootstrap,
         member spread, bank coverage, disagreement quality, speed

  python3 -m dreamdesk.wm_report tune --members runs/wm/member_seed*.pt
  python3 -m dreamdesk.wm_report test --members runs/wm/member_seed*.pt
"""
import argparse
import itertools
import json
import random
import statistics as stats
import time
from pathlib import Path

import torch

from .wm_data import load
from .wm_eval import HORIZON, App, Copy, Memo, delta_f1, evaluate
from .world_model import Neural

GRID = (0.3, 0.4, 0.5, 0.6, 0.7)
GATE_MIN_WINDOWS = 50
REAL_STEP_MS = 884  # Stage 2 median


def apps(data_dir, only=None):
    return [App(load(p)) for p in sorted(Path(data_dir).glob("*.pkl")) if not only or p.stem in only]


def tune(args):
    model = Neural(args.members, args.data, threads=args.threads)
    cached = []  # per app: list of (start, rows, vanish probs, appear probs, real after)
    for app in apps(args.data):
        model.fit(app)
        items = []
        ts = app.transitions["val"]
        for i in range(0, len(ts), 64):
            chunk = ts[i:i + 64]
            starts = [app.screens[t[0]] for t in chunk]
            p, rows, outs = model.probabilities(app, starts, chunk)
            for b, (s, t) in enumerate(zip(starts, chunk)):
                v = torch.stack([o[0][b] for o in outs]).mean(0)
                a = torch.stack([o[1][b] for o in outs]).mean(0)
                items.append((s, rows[b], v.tolist(), a, app.screens[t[4]], p.bank_ids))
        cached.append((app.name, items))
        print(f"cached {app.name}", flush=True)
    best = None
    for vt, at in itertools.product(GRID, GRID):
        per_app = []
        for name, items in cached:
            scores = []
            for s, r, v, a, real, bank in items:
                gone = {e for e, pv in zip(r, v) if pv > vt}
                came = {bank[k] for k in torch.nonzero(a > at).flatten().tolist()} - s
                scores.append(delta_f1(s, frozenset((s - gone) | came), real))
            per_app.append(stats.mean(scores))
        score = stats.mean(per_app)
        print(f"vanish {vt} appear {at}: {score:.4f}", flush=True)
        if best is None or score > best[0]:
            best = (score, vt, at)
    out = {"vanish": best[1], "appear": best[2], "val_h1_mean": round(best[0], 4), "members": args.members}
    Path(args.out).write_text(json.dumps(out, indent=1))
    print("chosen:", out)


def auroc(scores, labels):
    """Probability a random positive scores higher than a random negative (ties count half)."""
    pos = [s for s, l in zip(scores, labels) if l]
    neg = [s for s, l in zip(scores, labels) if not l]
    if not pos or not neg:
        return None
    ranked = sorted(scores)
    rank = {}
    i = 0
    while i < len(ranked):
        j = i
        while j < len(ranked) and ranked[j] == ranked[i]:
            j += 1
        rank[ranked[i]] = (i + j + 1) / 2
        i = j
    return (sum(rank[s] for s in pos) - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def spearman(x, y):
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j < len(order) and v[order[j]] == v[order[i]]:
                j += 1
            for k in range(i, j):
                r[order[k]] = (i + j - 1) / 2
            i = j
        return r
    rx, ry = ranks(x), ranks(y)
    mx, my = stats.mean(rx), stats.mean(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    return cov / (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5


def member_predictions(model, app, screens, ts):
    """Each member's own thresholded prediction."""
    p, rows, outs = model.probabilities(app, screens, ts)
    per_member = []
    for v, a in outs:
        preds = []
        for b, (r, s) in enumerate(zip(rows, screens)):
            gone = {e for j, e in enumerate(r) if v[b][j] > model.vt}
            came = {p.bank_ids[k] for k in torch.nonzero(a[b] > model.at).flatten().tolist()} - set(s)
            preds.append(frozenset((set(s) - gone) | came))
        per_member.append(preds)
    return per_member


def test(args):
    th = json.loads(Path(args.thresholds).read_text())
    ensemble = Neural(args.members, args.data, th["vanish"], th["appear"], args.threads)
    singles = [Neural([m], args.data, th["vanish"], th["appear"], args.threads) for m in args.members]
    report = {"thresholds": th, "split": args.split, "apps": {}}
    for app in apps(args.data, args.apps):
        r = {}
        for name, model in [("copy", Copy()), ("memo", Memo()), ("ensemble", ensemble)] + \
                           [(f"member{k}", m) for k, m in enumerate(singles)]:
            model.fit(app)
            t0 = time.time()
            one, many = evaluate(model, app, args.split)
            seconds = time.time() - t0
            r[name] = {"h1": one, "h5": many, "predictions_per_s": (len(one) + HORIZON * len(many)) / seconds}
        # bank coverage: real appearing elements in test never seen in training
        bank = set()
        for t in app.transitions["train"]:
            bank |= app.screens[t[0]] | app.screens[t[4]]
        appeared = [e for t in app.transitions[args.split] for e in app.screens[t[4]] - app.screens[t[0]]]
        # disagreement at horizon 1
        ts = app.transitions[args.split]
        dis, err = [], []
        for i in range(0, len(ts), 64):
            chunk = ts[i:i + 64]
            starts = [app.screens[t[0]] for t in chunk]
            per_member = member_predictions(ensemble, app, starts, chunk)
            ens = ensemble.predict_batch(app, starts, chunk)
            for b, (s, t) in enumerate(zip(starts, chunk)):
                pair = [delta_f1(s, per_member[x][b], per_member[y][b]) for x, y in itertools.combinations(range(len(per_member)), 2)]
                dis.append(1 - stats.mean(pair) if pair else 0.0)
                err.append(1 - delta_f1(s, ens[b], app.screens[t[4]]))
        report["apps"][app.name] = {
            "scores": {k: {"h1": v["h1"], "h5": v["h5"]} for k, v in r.items()},
            "speed": {k: round(v["predictions_per_s"], 1) for k, v in r.items()},
            "bank_missing_pct": round(100 * sum(e not in bank for e in appeared) / max(1, len(appeared)), 1),
            "disagreement_auroc": auroc(dis, [e > 0.5 for e in err]),
            "disagreement_spearman": spearman(dis, err) if len(set(dis)) > 1 else None,
            "n_unvisited_h5": sum(u for u, _ in r["copy"]["h5"]),
        }
        print(f"done {app.name}", flush=True)
    Path(args.out).write_text(json.dumps(report))
    print_report(report)


def mean_unv(items):
    v = [s for u, s in items if u]
    return stats.mean(v) if v else None


def print_report(report):
    rows = report["apps"]
    gate = [a for a, r in rows.items() if r["n_unvisited_h5"] >= GATE_MIN_WINDOWS]
    fmt = lambda x: f"{x:.3f}" if x is not None else "  -  "
    print(f"\nthresholds: vanish {report['thresholds']['vanish']}, appear {report['thresholds']['appear']}")
    print(f"{'app':13} {'gate':4} | h=1 unvisited: copy memo ens | h=5 unvisited: copy memo ens  members p10/med/p90 | h=5 all: memo ens | bank miss% | AUROC  rho")
    for a, r in rows.items():
        s = r["scores"]
        mem = sorted(mean_unv(s[f"member{k}"]["h5"]) or 0 for k in range(5))
        print(f"{a:13} {'yes' if a in gate else '':4} | {fmt(mean_unv(s['copy']['h1']))} {fmt(mean_unv(s['memo']['h1']))} {fmt(mean_unv(s['ensemble']['h1']))} | "
              f"{fmt(mean_unv(s['copy']['h5']))} {fmt(mean_unv(s['memo']['h5']))} {fmt(mean_unv(s['ensemble']['h5']))}  {mem[0]:.3f}/{mem[2]:.3f}/{mem[4]:.3f} | "
              f"{stats.mean(x for _, x in s['memo']['h5']):.3f} {stats.mean(x for _, x in s['ensemble']['h5']):.3f} | {r['bank_missing_pct']:9} | "
              f"{fmt(r['disagreement_auroc'])} {fmt(r['disagreement_spearman'])}")
    wins_memo = sum(mean_unv(rows[a]["scores"]["ensemble"]["h5"]) > mean_unv(rows[a]["scores"]["memo"]["h5"]) for a in gate)
    wins_both = sum(mean_unv(rows[a]["scores"]["ensemble"]["h5"]) > max(mean_unv(rows[a]["scores"]["memo"]["h5"]), mean_unv(rows[a]["scores"]["copy"]["h5"])) for a in gate)
    # equal-weight mean difference over gate apps, bootstrap over windows within each app
    rng = random.Random(0)
    diffs = {a: [e - m for (u, e), (_, m) in zip(rows[a]["scores"]["ensemble"]["h5"], rows[a]["scores"]["memo"]["h5"]) if u] for a in gate}
    point = stats.mean(stats.mean(d) for d in diffs.values())
    boots = sorted(stats.mean(stats.mean(rng.choices(d, k=len(d))) for d in diffs.values()) for _ in range(2000))
    lo, hi = boots[50], boots[1949]
    speed = min(rows[a]["speed"]["ensemble"] for a in rows)
    print(f"\ngate apps: {gate}")
    print(f"1. ensemble beats Copy and Memo at h=5 unvisited in {wins_both} of {len(gate)} gate apps (beats Memo in {wins_memo})")
    print(f"2. equal-weight mean difference vs Memo: {point:+.3f}, 95% interval [{lo:+.3f}, {hi:+.3f}]")
    print(f"3. slowest app: {speed:.0f} ensemble predictions/s = {speed * REAL_STEP_MS / 1000:.0f}x a real step (need 100x)")
    passed = wins_both > len(gate) / 2 and lo > 0 and speed * REAL_STEP_MS / 1000 >= 100
    print(f"GATE: {'PASS' if passed else 'FAIL'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["tune", "test", "show"])
    ap.add_argument("--data", default="data/wm")
    ap.add_argument("--members", nargs="+")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--thresholds", default="runs/wm/thresholds.json")
    ap.add_argument("--out", default=None)
    ap.add_argument("--split", default="test", help="only for a dry run of the report code on val")
    ap.add_argument("--apps", nargs="*", help="only for a dry run")
    args = ap.parse_args()
    if args.cmd == "tune":
        args.out = args.out or "runs/wm/thresholds.json"
        tune(args)
    elif args.cmd == "test":
        args.out = args.out or "runs/wm/test_report.json"
        if Path(args.out).exists():
            raise SystemExit(f"{args.out} exists: the test runs once. Use 'show' to print it again.")
        test(args)
    else:
        print_report(json.loads(Path(args.out or "runs/wm/test_report.json").read_text()))


if __name__ == "__main__":
    main()
